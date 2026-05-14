"""
虚拟节点统一启动器

读取 config.yaml 拿 broker 配置，按 --manifest 加载一个或多个清单（manifests/*.yaml），
为每个节点起一个线程，每个节点有独立 MQTT client（client_id 唯一）。
节点 .py 也可单独 `python simulation/sensors/xxx.py --id ...` 运行。

用法：
  python run.py                                # 加载 manifests/default.yaml
  python run.py -m default -m eb_plant         # 同时加载多份清单
  python run.py -m ./path/to/custom.yaml       # 直接指定清单文件路径
"""
import argparse
import logging
import os
import signal
import sys
import threading
from typing import List

import yaml

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MANIFEST_DIR = os.path.join(BASE_DIR, "manifests")

sys.path.insert(0, BASE_DIR)

from common.mqtt_node import MqttNode
from sensors.temp_humi_sensor.temp_humi_sensor import TempHumiSensor
from sensors.bmp280_temp_pressure_sensor.bmp280_temp_pressure_sensor import BMP280TempPressureSensor
from sensors.temp_pressure_sensor.temp_pressure_sensor import TempPressureSensor
from sensors.rotation_sensor.rotation_sensor import RotationSensor
from sensors.touch_sensor_switch.touch_sensor_switch import TouchSensorSwitch
from sensors.radial_counting_module.radial_counting_module import RadialCountingModule
from sensors.flow_sensor.flow_sensor import FlowSensor
from devices.sg90_servo.sg90_servo import SG90Servo
from devices.pin_control.pin_control import PinControl
from devices.pump.pump import Pump

log = logging.getLogger(__name__)

# 节点模块注册表：清单里 module 字段 -> 类
REGISTRY = {
    # 硬件复刻
    "temp_humi_sensor": TempHumiSensor,
    "bmp280_temp_pressure_sensor": BMP280TempPressureSensor,
    "rotation_sensor": RotationSensor,
    "touch_sensor_switch": TouchSensorSwitch,
    "radial_counting_module": RadialCountingModule,
    "sg90_servo": SG90Servo,
    "pin_control": PinControl,
    # 新增（无对应固件）
    "temp_pressure_sensor": TempPressureSensor,
    "flow_sensor": FlowSensor,
    "pump": Pump,
}


def build_node(entry: dict, broker: dict) -> MqttNode:
    module = entry.get("module")
    cls = REGISTRY.get(module)
    if cls is None:
        raise ValueError(f"未知节点模块 '{module}'，可选: {list(REGISTRY.keys())}")

    node_id = entry.get("id")
    if not node_id:
        raise ValueError(f"节点配置缺少 id 字段: {entry}")

    # 鉴权：节点级覆盖 > broker 级默认（复刻每台 .ino 独立 credentials 的能力）
    username = entry.get("username", broker.get("username", ""))
    password = entry.get("password", broker.get("password", ""))

    # 其余字段作为构造参数透传（剔除已显式处理的字段，避免重复传参）
    reserved = {"module", "id", "username", "password"}
    extra_kwargs = {k: v for k, v in entry.items() if k not in reserved}

    return cls(
        node_id=node_id,
        broker=broker["host"],
        port=broker.get("port", 1883),
        username=username,
        password=password,
        **extra_kwargs,
    )


def _resolve_manifest_path(name: str) -> str:
    """`default` -> manifests/default.yaml；带 / 或 .yaml 后缀的当成文件路径。"""
    if os.sep in name or name.endswith((".yaml", ".yml")):
        return name if os.path.isabs(name) else os.path.join(BASE_DIR, name)
    return os.path.join(MANIFEST_DIR, f"{name}.yaml")


def _load_manifest(path: str) -> dict:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"清单文件不存在: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if "nodes" not in data or not isinstance(data["nodes"], list):
        raise ValueError(f"清单 {path} 缺少 nodes 列表")
    return data


def collect_nodes(manifest_names: List[str]) -> List[dict]:
    """加载并合并所有清单的 nodes。同名 (module, id) 组合检测重复并报错。"""
    all_nodes: List[dict] = []
    seen = {}  # (module, id) -> manifest_name
    for name in manifest_names:
        path = _resolve_manifest_path(name)
        manifest = _load_manifest(path)
        display = manifest.get("name") or os.path.basename(path)
        desc = manifest.get("description", "")
        node_count = len(manifest["nodes"])
        log.info(f"加载清单: {display} ({node_count} 节点) {('- ' + desc) if desc else ''}")
        for entry in manifest["nodes"]:
            key = (entry.get("module"), entry.get("id"))
            if key in seen:
                raise ValueError(
                    f"清单 '{display}' 与 '{seen[key]}' 包含重复节点 module={key[0]} id={key[1]}"
                )
            seen[key] = display
            all_nodes.append(entry)
    return all_nodes


def main():
    parser = argparse.ArgumentParser(description="批量启动虚拟 IoT 节点")
    parser.add_argument(
        "--config",
        default=os.path.join(BASE_DIR, "config.yaml"),
        help="broker 配置文件（包含 broker 段）。默认: simulation/config.yaml",
    )
    parser.add_argument(
        "--manifest", "-m",
        action="append",
        default=None,
        help="清单名（manifests/<name>.yaml）或文件路径，可重复指定。默认: default",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    broker = cfg.get("broker") or {}
    if not broker.get("host"):
        log.error(f"{args.config} 缺少 broker.host")
        sys.exit(1)

    # 向后兼容：旧 config.yaml 里若仍残留 nodes 段，给出迁移提示但不再使用
    if cfg.get("nodes"):
        log.warning(
            f"{args.config} 仍包含 nodes 段，但现在节点列表由 manifests/*.yaml 管理；"
            f"该段已被忽略。请将节点搬到 manifests/ 下并删除 config.yaml 的 nodes。"
        )

    manifest_names = args.manifest if args.manifest else ["default"]
    try:
        entries = collect_nodes(manifest_names)
    except (FileNotFoundError, ValueError) as e:
        log.error(f"加载清单失败: {e}")
        sys.exit(1)

    if not entries:
        log.error("清单中没有任何节点，退出")
        sys.exit(1)

    nodes: List[MqttNode] = []
    threads: List[threading.Thread] = []

    for entry in entries:
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
