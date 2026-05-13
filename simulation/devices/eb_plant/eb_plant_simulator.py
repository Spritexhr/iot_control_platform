"""
乙苯(EB)装置模拟器——单进程模拟 5 个核心点位的耦合工况。

与其他传感器节点不同,本模拟器一个进程持有整个装置的状态(因为点位之间物理耦合),
按 1Hz 向 MQTT 发布数据,topic 与平台约定一致: iot/sensors/<sensor_id>/data。

支持的扰动场景(通过 MQTT control topic 注入):
  - none              恢复正常工况
  - ethylene_overfeed 乙烯进料过量,反应器温度上升,蒸汽包液位下降
  - cooling_failure   R1 冷却失效,温度/压力持续上升
  - deb_snowball      DEB 循环流量缓慢爬升(论文 Figure 10 雪球效应)

控制 topic: plant/EB/disturbance/control,payload: {"scenario": "deb_snowball"}

用法:
    python eb_plant_simulator.py --broker 127.0.0.1 --port 1883
    python eb_plant_simulator.py --broker 127.0.0.1 --scenario deb_snowball
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import os
import random
import signal
import sys
import time
from dataclasses import dataclass
from typing import Dict, Optional

import paho.mqtt.client as mqtt

log = logging.getLogger(__name__)


# ============ 点位定义(与 seed_eb_plant.py 保持一致) ============
@dataclass
class PointDef:
    sensor_id: str
    tag: str
    data_key: str
    normal_value: float
    noise: float  # 高斯噪声标准差(物理单位)


POINTS: Dict[str, PointDef] = {
    "EB-TT-101": PointDef("EB-TT-101", "TT-101", "temperature", 434.0, 0.5),
    "EB-PT-101": PointDef("EB-PT-101", "PT-101", "pressure", 20.0, 0.1),
    "EB-LT-102": PointDef("EB-LT-102", "LT-102", "level", 50.0, 0.5),
    "EB-FT-401": PointDef("EB-FT-401", "FT-401", "flow_rate", 282.0, 2.0),
    "EB-TT-201": PointDef("EB-TT-201", "TT-201", "temperature", 432.0, 0.5),
}


SCENARIOS = {
    "none", "ethylene_overfeed", "cooling_failure", "deb_snowball",
}


class EBPlantSimulator:
    """
    内部状态:每个点位维护一个 "bias" 偏移量,由扰动场景动态调整;
    每次 tick 输出 = normal + bias + 高斯噪声。
    """

    PUBLISH_PERIOD = 1.0  # 1Hz
    CONTROL_TOPIC = "plant/EB/disturbance/control"

    def __init__(self, broker: str, port: int, username: str = "", password: str = ""):
        self.broker = broker
        self.port = port

        self.client = mqtt.Client(client_id=f"EBPlantSim-{os.getpid()}")
        if username:
            self.client.username_pw_set(username, password)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.reconnect_delay_set(min_delay=1, max_delay=60)

        # 每个点位的当前偏移量(扰动累加的结果)
        self._bias: Dict[str, float] = {sid: 0.0 for sid in POINTS}
        self._scenario: str = "none"
        self._scenario_t0: float = 0.0  # 扰动启动时间
        self._stop = False

    # ---------- MQTT 回调 ----------
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            log.info("MQTT 已连接 broker=%s:%s", self.broker, self.port)
            client.subscribe(self.CONTROL_TOPIC, qos=1)
        else:
            log.error("MQTT 连接失败 rc=%s", rc)

    def _on_message(self, client, userdata, msg):
        if msg.topic != self.CONTROL_TOPIC:
            return
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except Exception as e:
            log.warning("控制消息解析失败: %s", e)
            return
        scenario = (payload.get("scenario") or "none").strip()
        if scenario not in SCENARIOS:
            log.warning("未知扰动场景: %s,有效值: %s", scenario, sorted(SCENARIOS))
            return
        self.set_scenario(scenario)

    # ---------- 场景控制 ----------
    def set_scenario(self, scenario: str) -> None:
        self._scenario = scenario
        self._scenario_t0 = time.time()
        # 切换场景时清空偏移,避免叠加错乱
        self._bias = {sid: 0.0 for sid in POINTS}
        log.info("→ 扰动场景切换: %s", scenario)

    # ---------- 主循环 ----------
    def run(self) -> None:
        self.client.connect(self.broker, self.port, keepalive=60)
        self.client.loop_start()

        next_tick = time.time()
        try:
            while not self._stop:
                self._step()
                self._publish_all()
                next_tick += self.PUBLISH_PERIOD
                sleep = next_tick - time.time()
                if sleep > 0:
                    time.sleep(sleep)
                else:
                    next_tick = time.time()  # 落后了就直接对齐
        finally:
            self.client.loop_stop()
            self.client.disconnect()

    def stop(self) -> None:
        self._stop = True

    # ---------- 物理推进 ----------
    def _step(self) -> None:
        """根据当前扰动场景,调整各点位的 bias。"""
        scenario = self._scenario
        elapsed = time.time() - self._scenario_t0

        if scenario == "none":
            # 偏移缓慢回零(指数衰减)
            for sid in self._bias:
                self._bias[sid] *= 0.98
            return

        if scenario == "ethylene_overfeed":
            # 乙烯进料过量 → 反应放热增加 → R1/R2 温度上升,蒸汽包液位下降
            # 30s 内温度上升 ~10K,液位下降 ~25%
            ramp = min(elapsed / 30.0, 1.0)
            self._bias["EB-TT-101"] = 10.0 * ramp
            self._bias["EB-TT-201"] = 8.0 * ramp
            self._bias["EB-PT-101"] = 1.5 * ramp
            self._bias["EB-LT-102"] = -25.0 * ramp

        elif scenario == "cooling_failure":
            # R1 冷却失效 → 温度/压力线性上升,直到饱和
            ramp = min(elapsed / 45.0, 1.0)
            self._bias["EB-TT-101"] = 15.0 * ramp
            self._bias["EB-PT-101"] = 3.0 * ramp
            self._bias["EB-LT-102"] = -10.0 * ramp

        elif scenario == "deb_snowball":
            # DEB 雪球效应:FT-401 缓慢爬升,演示中用 60 秒压缩论文 30 小时
            # 起始斜率小,逐渐加速(指数增长 + 上限)
            growth = min(20.0 * (math.exp(elapsed / 30.0) - 1), 350.0)
            self._bias["EB-FT-401"] = growth

    # ---------- 发布 ----------
    def _publish_all(self) -> None:
        now_ts = int(time.time())
        for pdef in POINTS.values():
            value = pdef.normal_value + self._bias[pdef.sensor_id] \
                + random.gauss(0, pdef.noise)
            # 物理夹紧:液位 0~100
            if pdef.data_key == "level":
                value = max(0.0, min(100.0, value))
            payload = {
                "sensor_id": pdef.sensor_id,
                "data": {pdef.data_key: round(value, 3)},
                "timestamp": now_ts,
            }
            topic = f"iot/sensors/{pdef.sensor_id}/data"
            self.client.publish(topic, json.dumps(payload), qos=0)


def main():
    ap = argparse.ArgumentParser(description="EB 装置 5 点模拟器")
    ap.add_argument("--broker", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--username", default="")
    ap.add_argument("--password", default="")
    ap.add_argument("--scenario", default="none", choices=sorted(SCENARIOS))
    ap.add_argument("--log-level", default="INFO")
    args = ap.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )

    sim = EBPlantSimulator(args.broker, args.port, args.username, args.password)
    if args.scenario != "none":
        sim.set_scenario(args.scenario)

    signal.signal(signal.SIGINT, lambda *_: sim.stop())
    signal.signal(signal.SIGTERM, lambda *_: sim.stop())

    log.info("EB 装置模拟器启动,1Hz 发布 5 个点位 → broker=%s:%s", args.broker, args.port)
    sim.run()


if __name__ == "__main__":
    main()
