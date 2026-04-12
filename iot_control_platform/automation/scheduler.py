import logging
import threading
import time
import traceback
from django.utils import timezone
from automation.models import AutomationRule
from automation.engine import execute_rule

logger = logging.getLogger('automation.scheduler')

_scheduler_thread = None
_stop_event = threading.Event()


def _run_scheduler():
    """后台调度器主循环，每秒检查一次是否有需要执行的自动化规则"""
    logger.info("自动化规则后台调度器已启动")
    while not _stop_event.is_set():
        try:
            # 获取所有处于运行状态的规则
            rules = AutomationRule.objects.filter(is_launched=True, process_status='running')
            now = timezone.now()

            for rule in rules:
                interval = rule.poll_interval
                if not interval or interval < 1:
                    interval = 1

                # 判断是否达到执行时间
                should_run = False
                if not rule.last_run_time:
                    should_run = True
                else:
                    elapsed = (now - rule.last_run_time).total_seconds()
                    if elapsed >= interval:
                        should_run = True

                if should_run:
                    # 记录执行时间
                    rule.last_run_time = now
                    rule.save(update_fields=['last_run_time'])
                    
                    try:
                        # 执行规则
                        logger.debug(f"调度器执行规则: {rule.name}")
                        execute_rule(rule)
                    except Exception as e:
                        error_msg = f"后台执行异常: {str(e)}\n{traceback.format_exc()}"
                        logger.error(f"规则 [{rule.name}] {error_msg}")
                        # 执行异常，停止该规则的轮询
                        rule.is_launched = False
                        rule.process_status = 'error_stopped'
                        rule.error_message = f"后台调度器执行异常: {str(e)}"
                        rule.save(update_fields=['is_launched', 'process_status', 'error_message'])

        except Exception as e:
            logger.error(f"自动化调度器发生未捕获异常: {e}")

        # 睡眠 1 秒后再次检查
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
