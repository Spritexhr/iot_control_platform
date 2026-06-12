"""
webui 数据层 —— 标准库 sqlite3，单用户开发工具不上 ORM

DB 是节点配置的 source of truth；manifests/*.yaml 仅作导入/导出的交换格式。
所有写操作走模块级锁串行化（sqlite 单写者即可满足本工具并发量）。
"""
import json
import os
import sqlite3
import threading
from datetime import datetime
from typing import List, Optional

WEBUI_DIR = os.path.dirname(os.path.abspath(__file__))
RUNTIME_DIR = os.path.join(WEBUI_DIR, "runtime")
LOG_DIR = os.path.join(RUNTIME_DIR, "logs")
DB_PATH = os.path.join(RUNTIME_DIR, "sim.db")

_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS broker_profiles (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  host TEXT NOT NULL,
  port INTEGER NOT NULL DEFAULT 1883,
  username TEXT NOT NULL DEFAULT '',
  password TEXT NOT NULL DEFAULT '',
  is_default INTEGER NOT NULL DEFAULT 0,
  created_at TEXT, updated_at TEXT
);

CREATE TABLE IF NOT EXISTS groups (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  description TEXT NOT NULL DEFAULT '',
  broker_profile_id INTEGER REFERENCES broker_profiles(id) ON DELETE SET NULL,
  created_at TEXT, updated_at TEXT
);

CREATE TABLE IF NOT EXISTS nodes (
  id INTEGER PRIMARY KEY,
  group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
  module TEXT NOT NULL,
  node_id TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1,
  params_json TEXT NOT NULL DEFAULT '{}',
  username TEXT,
  password TEXT,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TEXT, updated_at TEXT,
  UNIQUE(group_id, module, node_id)
);

CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY,
  group_ids_json TEXT NOT NULL,
  pid INTEGER,
  status TEXT NOT NULL,            -- running / stopped / exited / failed
  exit_code INTEGER,
  manifest_snapshot TEXT,
  log_path TEXT,
  started_at TEXT, ended_at TEXT
);

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT
);
"""


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init():
    os.makedirs(LOG_DIR, exist_ok=True)
    with _lock, connect() as conn:
        conn.executescript(SCHEMA)
        conn.execute("DELETE FROM runs WHERE status != 'running'")


def _row_to_dict(row: Optional[sqlite3.Row]) -> Optional[dict]:
    return dict(row) if row is not None else None


def _rows_to_list(rows) -> List[dict]:
    return [dict(r) for r in rows]


# ============ broker_profiles ============

def list_brokers() -> List[dict]:
    with connect() as conn:
        return _rows_to_list(conn.execute(
            "SELECT * FROM broker_profiles ORDER BY is_default DESC, id"))


def get_broker(broker_id: int) -> Optional[dict]:
    with connect() as conn:
        return _row_to_dict(conn.execute(
            "SELECT * FROM broker_profiles WHERE id=?", (broker_id,)).fetchone())


def get_default_broker() -> Optional[dict]:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM broker_profiles ORDER BY is_default DESC, id LIMIT 1"
        ).fetchone()
        return _row_to_dict(row)


def create_broker(data: dict) -> dict:
    ts = now_iso()
    with _lock, connect() as conn:
        if data.get("is_default"):
            conn.execute("UPDATE broker_profiles SET is_default=0")
        cur = conn.execute(
            "INSERT INTO broker_profiles (name, host, port, username, password, is_default,"
            " created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
            (data["name"], data["host"], data.get("port", 1883),
             data.get("username", ""), data.get("password", ""),
             1 if data.get("is_default") else 0, ts, ts),
        )
        # 注意：必须用同一连接回读（事务尚未提交，新连接看不到）
        return _row_to_dict(conn.execute(
            "SELECT * FROM broker_profiles WHERE id=?", (cur.lastrowid,)).fetchone())


def update_broker(broker_id: int, data: dict) -> Optional[dict]:
    with _lock, connect() as conn:
        if data.get("is_default"):
            conn.execute("UPDATE broker_profiles SET is_default=0")
        conn.execute(
            "UPDATE broker_profiles SET name=?, host=?, port=?, username=?, password=?,"
            " is_default=?, updated_at=? WHERE id=?",
            (data["name"], data["host"], data.get("port", 1883),
             data.get("username", ""), data.get("password", ""),
             1 if data.get("is_default") else 0, now_iso(), broker_id),
        )
        return _row_to_dict(conn.execute(
            "SELECT * FROM broker_profiles WHERE id=?", (broker_id,)).fetchone())


def delete_broker(broker_id: int):
    with _lock, connect() as conn:
        conn.execute("DELETE FROM broker_profiles WHERE id=?", (broker_id,))


# ============ groups ============

def list_groups() -> List[dict]:
    with connect() as conn:
        groups = _rows_to_list(conn.execute("SELECT * FROM groups ORDER BY id"))
        counts = dict(conn.execute(
            "SELECT group_id, COUNT(*) FROM nodes GROUP BY group_id").fetchall())
    for g in groups:
        g["node_count"] = counts.get(g["id"], 0)
    return groups


def get_group(group_id: int) -> Optional[dict]:
    with connect() as conn:
        return _row_to_dict(conn.execute(
            "SELECT * FROM groups WHERE id=?", (group_id,)).fetchone())


def get_group_by_name(name: str) -> Optional[dict]:
    with connect() as conn:
        return _row_to_dict(conn.execute(
            "SELECT * FROM groups WHERE name=?", (name,)).fetchone())


def create_group(data: dict) -> dict:
    ts = now_iso()
    with _lock, connect() as conn:
        cur = conn.execute(
            "INSERT INTO groups (name, description, broker_profile_id, created_at, updated_at)"
            " VALUES (?,?,?,?,?)",
            (data["name"], data.get("description", ""),
             data.get("broker_profile_id"), ts, ts),
        )
        return _row_to_dict(conn.execute(
            "SELECT * FROM groups WHERE id=?", (cur.lastrowid,)).fetchone())


def update_group(group_id: int, data: dict) -> Optional[dict]:
    with _lock, connect() as conn:
        conn.execute(
            "UPDATE groups SET name=?, description=?, broker_profile_id=?, updated_at=?"
            " WHERE id=?",
            (data["name"], data.get("description", ""),
             data.get("broker_profile_id"), now_iso(), group_id),
        )
        return _row_to_dict(conn.execute(
            "SELECT * FROM groups WHERE id=?", (group_id,)).fetchone())


def delete_group(group_id: int):
    with _lock, connect() as conn:
        conn.execute("DELETE FROM groups WHERE id=?", (group_id,))


# ============ nodes ============

def _node_out(row: dict) -> dict:
    row["params"] = json.loads(row.pop("params_json") or "{}")
    row["enabled"] = bool(row["enabled"])
    return row


def list_nodes(group_id: int) -> List[dict]:
    with connect() as conn:
        rows = _rows_to_list(conn.execute(
            "SELECT * FROM nodes WHERE group_id=? ORDER BY sort_order, id", (group_id,)))
    return [_node_out(r) for r in rows]


def get_node(node_pk: int) -> Optional[dict]:
    with connect() as conn:
        row = _row_to_dict(conn.execute(
            "SELECT * FROM nodes WHERE id=?", (node_pk,)).fetchone())
    return _node_out(row) if row else None


def create_node(group_id: int, data: dict) -> dict:
    ts = now_iso()
    with _lock, connect() as conn:
        cur = conn.execute(
            "INSERT INTO nodes (group_id, module, node_id, enabled, params_json,"
            " username, password, sort_order, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (group_id, data["module"], data["node_id"],
             1 if data.get("enabled", True) else 0,
             json.dumps(data.get("params", {}), ensure_ascii=False),
             data.get("username"), data.get("password"),
             data.get("sort_order", 0), ts, ts),
        )
        row = _row_to_dict(conn.execute(
            "SELECT * FROM nodes WHERE id=?", (cur.lastrowid,)).fetchone())
        return _node_out(row)


def update_node(node_pk: int, data: dict) -> Optional[dict]:
    with _lock, connect() as conn:
        conn.execute(
            "UPDATE nodes SET module=?, node_id=?, enabled=?, params_json=?,"
            " username=?, password=?, sort_order=?, updated_at=? WHERE id=?",
            (data["module"], data["node_id"],
             1 if data.get("enabled", True) else 0,
             json.dumps(data.get("params", {}), ensure_ascii=False),
             data.get("username"), data.get("password"),
             data.get("sort_order", 0), now_iso(), node_pk),
        )
        row = _row_to_dict(conn.execute(
            "SELECT * FROM nodes WHERE id=?", (node_pk,)).fetchone())
        return _node_out(row) if row else None


def delete_node(node_pk: int):
    with _lock, connect() as conn:
        conn.execute("DELETE FROM nodes WHERE id=?", (node_pk,))


# ============ runs ============

def list_runs(limit: int = 50) -> List[dict]:
    with connect() as conn:
        rows = _rows_to_list(conn.execute(
            "SELECT id, group_ids_json, pid, status, exit_code, log_path,"
            " started_at, ended_at FROM runs ORDER BY id DESC LIMIT ?", (limit,)))
    for r in rows:
        r["group_ids"] = json.loads(r.pop("group_ids_json"))
    return rows


def get_run(run_id: int) -> Optional[dict]:
    with connect() as conn:
        row = _row_to_dict(conn.execute(
            "SELECT * FROM runs WHERE id=?", (run_id,)).fetchone())
    if row:
        row["group_ids"] = json.loads(row.pop("group_ids_json"))
    return row


def create_run(group_ids: List[int], pid: int, manifest_snapshot: str, log_path: str) -> dict:
    with _lock, connect() as conn:
        cur = conn.execute(
            "INSERT INTO runs (group_ids_json, pid, status, manifest_snapshot, log_path,"
            " started_at) VALUES (?,?,?,?,?,?)",
            (json.dumps(group_ids), pid, "running", manifest_snapshot, log_path, now_iso()),
        )
        row = _row_to_dict(conn.execute(
            "SELECT * FROM runs WHERE id=?", (cur.lastrowid,)).fetchone())
        row["group_ids"] = json.loads(row.pop("group_ids_json"))
        return row


def finish_run(run_id: int, status: str, exit_code: Optional[int] = None):
    with _lock, connect() as conn:
        conn.execute("DELETE FROM runs WHERE id=?", (run_id,))


def running_runs() -> List[dict]:
    with connect() as conn:
        rows = _rows_to_list(conn.execute("SELECT * FROM runs WHERE status='running'"))
    for r in rows:
        r["group_ids"] = json.loads(r.pop("group_ids_json"))
    return rows
