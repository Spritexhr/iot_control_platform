"""
湿度超 80% 打印 - runscript 入口
运行：python manage.py runscript humidity_overflow_print（持续监听，Ctrl+C 停止）
"""
from automation.script.humidity_overflow_print import run_standalone as run
