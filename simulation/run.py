"""
虚拟节点统一启动器

读取 config.yaml，为每个节点起一个线程，每个节点有独立 MQTT client（client_id 唯一）
节点 .py 也可单独 `python simulation/sensors/xxx.py --id ...` 运行
"""
import argparse
import logging
import os
import signal
import sys
import threading
from typing import List

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common.mqtt_node import MqttNode
from sensors.temp_humi_sensor import TempHumiSensor
from devices.sg90_servo import SG90Servo

log = logging.getLogger(__name__)

# 节点模块注册表：config.yaml 里 module 字段 -> 类
REGISTRY = {
    "temp_humi_sensor": TempHumiSensor,
    "sg90_servo": SG90Servo,
}


def build_node(entry: dict, broker: dict) -> MqttNode:
    module = entry.get("module")
    cls = REGISTRY.get(module)
    if cls is None:
        raise ValueError(f"未知节点模块 '{module}'，可选: {list(REGISTRY.keys())}")

    node_id = entry.get("id")
    if not node_id:
        raise ValueError(f"节点配置缺少 id 字段: {entry}")

    # 从 entry 中收集除 module/id 之外的所有键作为构造参数
    extra_kwargs = {k: v for k, v in entry.items() if k not in ("module", "id")}

    return cls(
        node_id=node_id,
        broker=broker["host"],
        port=broker.get("port", 1883),
        username=broker.get("username", ""),
        password=broker.get("password", ""),
        **extra_kwargs,
    )


def main():
    parser = argparse.ArgumentParser(description="批量启动虚拟 IoT 节点")
    parser.add_argument(
        "--config",
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml"),
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    broker = cfg.get("broker") or {}
    if not broker.get("host"):
        log.error("config.yaml 缺少 broker.host")
        sys.exit(1)

    nodes: List[MqttNode] = []
    threads: List[threading.Thread] = []

    for entry in cfg.get("nodes", []):
        try:
            node = build_node(entry, broker)
        except Exception as e:
            log.error(f"✗ 构建节点失败: {entry} -> {e}")
            continue
        t = threading.Thread(target=node.run, name=f"node-{node.node_id}", daemon=True)
        nodes.append(node)
        threads.append(t)
        t.start()
        log.info(f"已启动: {entry['module']} id={node.node_id}")

    if not nodes:
        log.error("没有任何节点启动，退出")
        sys.exit(1)

    log.info(f"共启动 {len(nodes)} 个虚拟节点。Ctrl-C 退出。")

    stop_event = threading.Event()

    def _shutdown(signum, frame):
        log.info(f"收到信号 {signum}，停止所有节点…")
        stop_event.set()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    stop_event.wait()
    for n in nodes:
        n.stop()
    for t in threads:
        t.join(timeout=5)


if __name__ == "__main__":
    main()
