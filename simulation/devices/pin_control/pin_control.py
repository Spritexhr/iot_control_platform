"""
虚拟 D5/D6/D7 电平控制器 —— 复刻
hardware/wemos-d1/devices/pin_control/pin_control_d5.ino

支持命令：
  high / low       —— 设置单个引脚（D5/D6/D7，默认 D5）
  high_all         —— 三个引脚依次置高，间隔 1 秒
  low_all          —— 三个引脚依次置低，间隔 1 秒
  current_status   —— 上报当前状态
  set_status_interval —— 调整心跳间隔
"""
import argparse
import logging
import os
import sys
import threading
import time
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common.mqtt_node import MqttNode

log = logging.getLogger(__name__)

VALID_PINS = ("D5", "D6", "D7")
LEVEL_HIGH = "high"
LEVEL_LOW = "low"
ALL_PIN_STEP_MS = 1000


class PinControl(MqttNode):
    NODE_TYPE = "device"
    ID_FIELD = "device_id"

    DEFAULT_STATUS_REPORT_INTERVAL = 120

    def __init__(
        self,
        node_id: str,
        broker: str,
        port: int = 1883,
        username: str = "",
        password: str = "",
        status_report_interval: int = DEFAULT_STATUS_REPORT_INTERVAL,
        initial_levels: Optional[dict] = None,
    ):
        super().__init__(
            node_id=node_id,
            broker=broker,
            port=port,
            username=username,
            password=password,
            status_report_interval=status_report_interval,
        )
        # 三个引脚的当前电平
        self.levels = {p: LEVEL_LOW for p in VALID_PINS}
        if initial_levels:
            for p, lvl in initial_levels.items():
                if p in VALID_PINS and lvl in (LEVEL_HIGH, LEVEL_LOW):
                    self.levels[p] = lvl

    def build_status_payload(self) -> dict:
        return {
            "level_d5": self.levels["D5"],
            "level_d6": self.levels["D6"],
            "level_d7": self.levels["D7"],
            "statusReportInterval": self.status_report_interval,
        }

    def _set_pin(self, pin: str, level: str) -> bool:
        if pin not in VALID_PINS:
            log.warning(f"[{self.node_id}] ✗ 无效 pin: {pin}")
            return False
        if level not in (LEVEL_HIGH, LEVEL_LOW):
            log.warning(f"[{self.node_id}] ✗ 无效 level: {level}")
            return False
        self.levels[pin] = level
        log.info(f"[{self.node_id}] ✓ {pin} → {level}")
        return True

    def _do_all(self, level: str, check_code: Optional[str]) -> None:
        """依次切换三个引脚，每步间隔 1 秒，最后发一次 all_level_updated"""
        def runner():
            for p in VALID_PINS:
                self._set_pin(p, level)
                time.sleep(ALL_PIN_STEP_MS / 1000.0)
            self.publish_status("all_level_updated", check_code)
        threading.Thread(target=runner, name=f"{self.node_id}-all-{level}", daemon=True).start()

    def handle_command(self, command: str, payload: dict, check_code: Optional[str]) -> None:
        if command in (LEVEL_HIGH, LEVEL_LOW):
            pin = (payload.get("pin") or "D5").upper()
            if self._set_pin(pin, command):
                self.publish_status("level_updated", check_code)

        elif command == "high_all":
            self._do_all(LEVEL_HIGH, check_code)

        elif command == "low_all":
            self._do_all(LEVEL_LOW, check_code)

        elif command == "current_status":
            # 可选 pin 字段：当前实现统一返回全部，与 .ino 行为一致（status 总是含三个 level）
            self.publish_status("check_current_level", check_code)

        elif command == "set_status_interval":
            interval = int(payload.get("interval", 0))
            if 30 <= interval <= 600:
                self.status_report_interval = interval
                log.info(f"[{self.node_id}] ✓ statusReportInterval → {interval}s")
                self.publish_status("status_interval_updated", check_code)
            else:
                log.warning(f"[{self.node_id}] ✗ interval 越界（30-600）: {interval}")

        else:
            log.warning(f"[{self.node_id}] ⚠ 未知命令: {command}")


def main():
    parser = argparse.ArgumentParser(description="虚拟 D5/D6/D7 电平控制器")
    parser.add_argument("--id", default="potential_controler_001")
    parser.add_argument("--broker", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--username", default="")
    parser.add_argument("--password", default="")
    parser.add_argument("--status-report-interval", type=int,
                        default=PinControl.DEFAULT_STATUS_REPORT_INTERVAL)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    node = PinControl(
        node_id=args.id,
        broker=args.broker,
        port=args.port,
        username=args.username,
        password=args.password,
        status_report_interval=args.status_report_interval,
    )
    try:
        node.run()
    except KeyboardInterrupt:
        node.stop()


if __name__ == "__main__":
    main()
