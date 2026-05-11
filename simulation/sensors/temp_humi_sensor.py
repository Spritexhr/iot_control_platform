"""
虚拟 DHT11 温湿度传感器 —— 复刻 hardware/wemos-d1/sensors/temp_humi_sensor/temp_humi_sensor_v3.ino

MQTT 主题：
  数据:   iot/sensors/{sensor_id}/data
  状态:   iot/sensors/{sensor_id}/status
  控制:   iot/sensors/{sensor_id}/control

支持命令：enable / disable / set_interval / set_data_interval / set_status_interval
"""
import argparse
import logging
import math
import os
import random
import sys
import time
from typing import Optional

# 支持作为脚本独立运行：把 simulation/ 加入 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.mqtt_node import MqttNode

log = logging.getLogger(__name__)


class TempHumiSensor(MqttNode):
    NODE_TYPE = "sensor"
    ID_FIELD = "sensor_id"

    # 与 .ino 默认值一致
    DEFAULT_SAMPLING_INTERVAL = 60
    DEFAULT_STATUS_REPORT_INTERVAL = 120

    def __init__(
        self,
        node_id: str,
        broker: str,
        port: int = 1883,
        username: str = "",
        password: str = "",
        sampling_interval: int = DEFAULT_SAMPLING_INTERVAL,
        status_report_interval: int = DEFAULT_STATUS_REPORT_INTERVAL,
    ):
        super().__init__(
            node_id=node_id,
            broker=broker,
            port=port,
            username=username,
            password=password,
            status_report_interval=status_report_interval,
        )
        self.topic_data = f"iot/sensors/{node_id}/data"
        self.sampling_interval = sampling_interval
        self.is_enabled = True
        self._last_sample_time = 0.0
        self._t0 = time.time()  # 波形相位起点

    # ============ status payload ============
    def build_status_payload(self) -> dict:
        return {
            "is_enabled": self.is_enabled,
            "samplingInterval": self.sampling_interval,
            "statusReportInterval": self.status_report_interval,
        }

    # ============ 数据生成（仿真核心）============
    # 想换波形就改下面两个方法
    def read_temperature(self) -> float:
        """正弦波昼夜温度：周期 1 小时，22±5°C，附加 ±0.3°C 抖动"""
        period_s = 3600
        elapsed = time.time() - self._t0
        base = 22.0 + 5.0 * math.sin(2 * math.pi * elapsed / period_s)
        return round(base + random.uniform(-0.3, 0.3), 1)

    def read_humidity(self) -> float:
        """45~65% 区间均匀分布"""
        return round(random.uniform(45.0, 65.0), 1)

    # ============ 控制命令 ============
    def handle_command(self, command: str, payload: dict, check_code: Optional[str]) -> None:
        if command in ("set_interval", "set_data_interval"):
            interval = int(payload.get("interval", 0))
            if 10 <= interval <= 3600:
                self.sampling_interval = interval
                log.info(f"[{self.node_id}] ✓ samplingInterval → {interval}s")
                self.publish_status("interval_updated", check_code)
            else:
                log.warning(f"[{self.node_id}] ✗ interval 越界（10-3600）: {interval}")

        elif command == "set_status_interval":
            interval = int(payload.get("interval", 0))
            if 30 <= interval <= 600:
                self.status_report_interval = interval
                log.info(f"[{self.node_id}] ✓ statusReportInterval → {interval}s")
                self.publish_status("status_interval_updated", check_code)
            else:
                log.warning(f"[{self.node_id}] ✗ interval 越界（30-600）: {interval}")

        elif command == "enable":
            self.is_enabled = True
            log.info(f"[{self.node_id}] ✓ 已启用")
            self.publish_status("sensor_enabled", check_code)

        elif command == "disable":
            self.is_enabled = False
            log.info(f"[{self.node_id}] ✓ 已禁用")
            self.publish_status("sensor_disabled", check_code)

        else:
            log.warning(f"[{self.node_id}] ⚠ 未知命令: {command}")

    # ============ 主循环 hook：周期发数据 ============
    def on_tick(self) -> None:
        if not self.is_enabled:
            return
        now = time.time()
        if now - self._last_sample_time < self.sampling_interval:
            return

        temperature = self.read_temperature()
        humidity = self.read_humidity()
        data_msg = {
            "sensor_id": self.node_id,
            "data": {
                "temperature": temperature,
                "humidity": humidity,
            },
            "timestamp": self.now_ts(),
        }
        if self.publish_json(self.topic_data, data_msg):
            log.info(
                f"[{self.node_id}] → data temperature={temperature}°C humidity={humidity}%"
            )
        self._last_sample_time = now


def main():
    parser = argparse.ArgumentParser(description="虚拟 DHT11 温湿度传感器")
    parser.add_argument("--id", default="DHT11-WEMOS-001", help="sensor_id")
    parser.add_argument("--broker", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--username", default="")
    parser.add_argument("--password", default="")
    parser.add_argument("--sampling-interval", type=int, default=TempHumiSensor.DEFAULT_SAMPLING_INTERVAL)
    parser.add_argument("--status-report-interval", type=int, default=TempHumiSensor.DEFAULT_STATUS_REPORT_INTERVAL)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    node = TempHumiSensor(
        node_id=args.id,
        broker=args.broker,
        port=args.port,
        username=args.username,
        password=args.password,
        sampling_interval=args.sampling_interval,
        status_report_interval=args.status_report_interval,
    )
    try:
        node.run()
    except KeyboardInterrupt:
        log.info("⚠ Ctrl-C，停止中…")
        node.stop()


if __name__ == "__main__":
    main()
