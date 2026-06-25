import logging
import os
import sys
import threading
import time
import traceback
from django.utils import timezone
from automation.models import AutomationRule, ControlScheme
from automation.engine import execute_rule
from automation.controllers import run_control_scheme

logger = logging.getLogger('automation.scheduler')

_scheduler_thread = None
_stop_event = threading.Event()


def scheduler_enabled() -> bool:
    """
    调度器（自动化规则 + 控制方案）必须只在「单一完整模式常驻进程」运行，
    否则多 worker 会重复执行规则 / 重复向设备下发命令。

    判定（与 sensors/apps.py 的 MQTT 模式同源）：
    - 迁移 / 测试：不运行
    - publisher-only backend（IOT_MQTT_RUNNER=false，可能多 ASGI worker）：不运行
    - mqtt_runner 独立容器（生产，单实例完整模式）：运行 ← 控制环的实际执行进程
    - 本地 runserver（仅 RUN_MAIN 主进程）：运行
    - 其它完整模式服务器进程（gunicorn/daphne 且未声明 publisher-only）：运行
    """
    if 'test' in sys.argv or 'migrate' in sys.argv or 'makemigrations' in sys.argv:
        return False
    if 'mqtt_runner' in sys.argv:
        return True
    if os.environ.get('IOT_MQTT_RUNNER', '').lower() in ('false', '0', 'no'):
        return False
    if 'runserver' in sys.argv:
        return os.environ.get('RUN_MAIN') == 'true'
    if any(x in sys.argv[0].lower() for x in ('gunicorn', 'uwsgi', 'daphne', 'uvicorn')):
        return True
    return False


def _process_automation_rules(now):
    """处理自由脚本规则（原有逻辑）"""
    rules = AutomationRule.objects.filter(is_launched=True, process_status='running')
    for rule in rules:
        interval = rule.poll_interval
        if not interval or interval < 1:
            interval = 1

        should_run = (not rule.last_run_time
                      or (now - rule.last_run_time).total_seconds() >= interval)
        if not should_run:
            continue

        # 记录执行时间
        rule.last_run_time = now
        rule.save(update_fields=['last_run_time'])
        try:
            logger.debug(f"调度器执行规则: {rule.name}")
            execute_rule(rule)
        except Exception as e:
            error_msg = f"后台执行异常: {str(e)}\n{traceback.format_exc()}"
            logger.error(f"规则 [{rule.name}] {error_msg}")
            rule.is_launched = False
            rule.process_status = 'error_stopped'
            rule.error_message = f"后台调度器执行异常: {str(e)}"
            rule.save(update_fields=['is_launched', 'process_status', 'error_message'])


def _process_control_schemes(now):
    """处理结构化控制方案（双位 / PI / PID）。

    注意：dt 由 run_control_scheme 内部用上一次 last_run_time 推算，
    这里不预先改写 last_run_time，只判断是否到点。
    """
    schemes = ControlScheme.objects.filter(is_enabled=True, status='running').select_related(
        'sensor_member__sensor', 'device_member__device'
    )
    for scheme in schemes:
        interval = scheme.sample_interval or 1
        should_run = (not scheme.last_run_time
                      or (now - scheme.last_run_time).total_seconds() >= interval)
        if not should_run:
            continue
        try:
            logger.debug(f"调度器执行控制方案: {scheme.name}")
            run_control_scheme(scheme, send=True)
        except Exception as e:
            # run_control_scheme 内部已兜底，这里再保险一层
            logger.error(f"控制方案 [{scheme.name}] 后台执行异常: {e}\n{traceback.format_exc()}")
            ControlScheme.objects.filter(pk=scheme.pk).update(
                is_enabled=False, status='error', error_message=f"后台调度器执行异常: {e}")


def _run_scheduler():
    """后台调度器主循环，每秒检查一次自动化规则与控制方案。"""
    logger.info("自动化调度器已启动（自动化规则 + 控制方案）")
    while not _stop_event.is_set():
        try:
            now = timezone.now()
            _process_automation_rules(now)
            _process_control_schemes(now)
        except Exception as e:
            logger.error(f"自动化调度器发生未捕获异常: {e}")
        time.sleep(1)


def start_scheduler():
    """启动后台调度器线程"""
    global _scheduler_thread
    if _scheduler_thread is None or not _scheduler_thread.is_alive():
        _stop_event.clear()
        _scheduler_thread = threading.Thread(target=_run_scheduler, name="AutomationScheduler", daemon=True)
        _scheduler_thread.start()


def stop_scheduler():
    """停止后台调度器线程"""
    if _scheduler_thread and _scheduler_thread.is_alive():
        _stop_event.set()
        _scheduler_thread.join(timeout=2)
