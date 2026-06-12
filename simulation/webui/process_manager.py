"""
run.py 子进程生命周期管理

启动：DB 配置渲染成 runtime/manifest_run_<id>.yaml + config_run_<id>.yaml，
      spawn `python run.py --config ... -m ...`（start_new_session 建进程组）。
      渲染产物落盘且快照入库 —— 每次启动可审计，也可脱离 webui 手工复跑：
          python run.py --config runtime/config_run_42.yaml -m runtime/manifest_run_42.yaml
停止：先 SIGTERM 进程组（run.py 已有优雅停机），5 秒超时后 SIGKILL。
日志：stdout/stderr 合并写 runtime/logs/run_<id>.log，后台线程 tail 推给 on_event。
恢复：webui 重启时对 DB 中 status=running 的 run 探活（os.kill(pid,0)），
      存活则接管继续 tail，死亡则标记 exited。
"""
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from typing import Callable, Dict, List, Optional

from . import db, manifest_io

log = logging.getLogger(__name__)

RUN_PY = os.path.join(manifest_io.SIMULATION_DIR, "run.py")
STOP_GRACE_S = 5.0

# 事件回调：on_event(event: dict)，由 server.py 注入（转发到 WebSocket）
# event 形如 {"type": "log_line", "run_id", "line"} / {"type": "run_state", "run": {...}}
_on_event: Optional[Callable[[dict], None]] = None

# run_id -> Popen（仅本进程启动/接管的）
_procs: Dict[int, subprocess.Popen] = {}
_lock = threading.Lock()


def set_event_handler(handler: Callable[[dict], None]):
    global _on_event
    _on_event = handler


def _emit(event: dict):
    if _on_event:
        try:
            _on_event(event)
        except Exception:
            log.exception("事件回调失败")


def _pid_alive(pid: Optional[int]) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def _tail_log(run_id: int, log_path: str, proc: Optional[subprocess.Popen], pid: Optional[int]):
    """跟踪日志文件并推送新行；进程退出后更新 runs 表"""
    try:
        # 日志文件可能已被清理（如上次 shutdown 后 _cleanup_runtime 删除），
        # 此时仍需监控进程退出以正确更新 DB 状态
        if not os.path.isfile(log_path):
            log.warning(f"run {run_id} 日志文件不存在，仅监控进程退出")
            while True:
                if proc is not None:
                    code = proc.poll()
                    if code is not None:
                        _finish(run_id, code)
                        return
                elif not _pid_alive(pid):
                    _finish(run_id, None)
                    return
                time.sleep(0.5)

        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            f.seek(0, os.SEEK_END)
            while True:
                line = f.readline()
                if line:
                    _emit({"type": "log_line", "run_id": run_id, "line": line.rstrip("\n")})
                    continue
                # 没有新内容：检查进程是否退出
                if proc is not None:
                    code = proc.poll()
                    if code is not None:
                        _finish(run_id, code)
                        return
                elif not _pid_alive(pid):
                    _finish(run_id, None)
                    return
                time.sleep(0.3)
    except Exception:
        log.exception(f"日志跟踪线程异常 run={run_id}")


def _cleanup_runtime(run_id: int):
    """删除 run 结束后不再需要的渲染产物（manifest / config / log），保持 runtime/ 干净。"""
    for pattern in (
        os.path.join(db.RUNTIME_DIR, f"manifest_run_{run_id}.yaml"),
        os.path.join(db.RUNTIME_DIR, f"config_run_{run_id}.yaml"),
        os.path.join(db.LOG_DIR, f"run_{run_id}.log"),
    ):
        try:
            if os.path.isfile(pattern):
                os.remove(pattern)
        except OSError:
            pass


def _finish(run_id: int, exit_code: Optional[int]):
    run = db.get_run(run_id)
    if run and run["status"] == "running":
        # SIGTERM 正常停止的 exit_code 是 -15 / 0，都归为 stopped；其余为 exited
        status = "stopped" if exit_code in (0, -signal.SIGTERM, None) else "exited"
        db.finish_run(run_id, status, exit_code)
    with _lock:
        _procs.pop(run_id, None)
    _cleanup_runtime(run_id)
    _emit({"type": "run_state", "run": db.get_run(run_id)})
    log.info(f"run {run_id} 结束 exit_code={exit_code}")


def start_run(group_ids: List[int]) -> dict:
    """校验 → 渲染 → spawn。校验失败抛 ValueError（含全部错误信息）"""
    groups, nodes_by_group, errors = [], {}, []
    for gid in group_ids:
        g = db.get_group(gid)
        if not g:
            raise ValueError(f"分组 {gid} 不存在")
        groups.append(g)
        nodes_by_group[g["id"]] = db.list_nodes(g["id"])

    # 与 run.py 同款 (module, id) 跨组重复预检
    seen = {}
    for g in groups:
        for n in nodes_by_group[g["id"]]:
            if not n.get("enabled", True):
                continue
            key = (n["module"], n["node_id"])
            if key in seen:
                errors.append(
                    f"分组 '{g['name']}' 与 '{seen[key]}' 包含重复节点"
                    f" module={key[0]} id={key[1]}"
                )
            seen[key] = g["name"]
            errs, _warns = manifest_io.validate_node(
                n["module"], manifest_io.node_to_entry(n))
            errors.extend(f"分组 '{g['name']}' 节点 {n['node_id']}: {e}" for e in errs)

    if not seen:
        errors.append("所选分组没有任何启用的节点")
    if errors:
        raise ValueError("；\n".join(errors))

    # broker：取第一个组绑定的 profile，未绑定用默认
    broker = None
    for g in groups:
        if g.get("broker_profile_id"):
            broker = db.get_broker(g["broker_profile_id"])
            break
    broker = broker or db.get_default_broker()
    if not broker:
        raise ValueError("尚未配置任何 broker，请先到设置页创建 broker profile")

    manifest = manifest_io.groups_to_manifest(groups, nodes_by_group)
    manifest_text = manifest_io.dump_manifest_yaml(manifest)
    config_text = manifest_io.dump_config_yaml(broker)

    # 先占位拿 run_id 再补落盘路径，保证文件名含 run_id 可追溯
    run = db.create_run(group_ids, pid=0, manifest_snapshot=manifest_text, log_path="")
    run_id = run["id"]
    manifest_path = os.path.join(db.RUNTIME_DIR, f"manifest_run_{run_id}.yaml")
    config_path = os.path.join(db.RUNTIME_DIR, f"config_run_{run_id}.yaml")
    log_path = os.path.join(db.LOG_DIR, f"run_{run_id}.log")
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(manifest_text)
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(config_text)

    log_file = open(log_path, "w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, RUN_PY, "--config", config_path, "-m", manifest_path],
        stdout=log_file, stderr=subprocess.STDOUT,
        cwd=manifest_io.SIMULATION_DIR,
        start_new_session=True,
    )
    log_file.close()  # 子进程已持有 fd

    with db._lock, db.connect() as conn:
        conn.execute("UPDATE runs SET pid=?, log_path=? WHERE id=?",
                     (proc.pid, log_path, run_id))
    with _lock:
        _procs[run_id] = proc

    threading.Thread(target=_tail_log, args=(run_id, log_path, proc, proc.pid),
                     name=f"tail-run-{run_id}", daemon=True).start()

    run = db.get_run(run_id)
    _emit({"type": "run_state", "run": run})
    log.info(f"run {run_id} 已启动 pid={proc.pid} 节点数={len(seen)}")
    return run


def stop_run(run_id: int) -> dict:
    run = db.get_run(run_id)
    if not run:
        raise ValueError(f"run {run_id} 不存在")
    if run["status"] != "running":
        return run

    pid = run["pid"]
    try:
        # 杀进程组（start_new_session 后 pgid == pid）
        os.killpg(pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        _finish(run_id, None)
        return db.get_run(run_id)

    def _force_kill():
        deadline = time.time() + STOP_GRACE_S
        while time.time() < deadline:
            if not _pid_alive(pid):
                return
            time.sleep(0.2)
        try:
            os.killpg(pid, signal.SIGKILL)
            log.warning(f"run {run_id} SIGTERM 超时，已 SIGKILL")
        except (ProcessLookupError, PermissionError):
            pass

    threading.Thread(target=_force_kill, name=f"kill-run-{run_id}", daemon=True).start()
    return run


def recover():
    """webui 启动时调用：接管或清理 DB 中 status=running 的 run"""
    active_ids = set()
    for run in db.running_runs():
        if _pid_alive(run["pid"]):
            log.info(f"接管仍在运行的 run {run['id']} (pid={run['pid']})")
            active_ids.add(run["id"])
            threading.Thread(
                target=_tail_log,
                args=(run["id"], run["log_path"], None, run["pid"]),
                name=f"tail-run-{run['id']}", daemon=True,
            ).start()
        else:
            log.info(f"run {run['id']} 进程已不存在，从 DB 删除并清理文件")
            db.finish_run(run["id"], "exited", None)
            _cleanup_runtime(run["id"])

    # 同时清理没有被接管的其他历史临时文件
    import glob
    for p in glob.glob(os.path.join(db.RUNTIME_DIR, "manifest_run_*.yaml")):
        try:
            fname = os.path.basename(p)
            rid = int(fname.split("_")[-1].split(".")[0])
            if rid not in active_ids:
                os.remove(p)
        except Exception:
            pass
    for p in glob.glob(os.path.join(db.RUNTIME_DIR, "config_run_*.yaml")):
        try:
            fname = os.path.basename(p)
            rid = int(fname.split("_")[-1].split(".")[0])
            if rid not in active_ids:
                os.remove(p)
        except Exception:
            pass
    for p in glob.glob(os.path.join(db.LOG_DIR, "run_*.log")):
        try:
            fname = os.path.basename(p)
            rid = int(fname.split("_")[-1].split(".")[0])
            if rid not in active_ids:
                os.remove(p)
        except Exception:
            pass


def read_log(run_id: int, offset: int = 0, limit: int = 500) -> dict:
    """分页读取日志行（WS 之外的兜底/历史查看）"""
    run = db.get_run(run_id)
    if not run or not run.get("log_path") or not os.path.isfile(run["log_path"]):
        return {"lines": [], "next_offset": offset, "eof": True}
    lines = []
    with open(run["log_path"], "r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f):
            if i < offset:
                continue
            if len(lines) >= limit:
                break
            lines.append(line.rstrip("\n"))
    next_offset = offset + len(lines)
    return {
        "lines": lines,
        "next_offset": next_offset,
        "eof": run["status"] != "running" and len(lines) < limit,
    }
