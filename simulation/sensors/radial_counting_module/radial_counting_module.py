"""
虚拟 H2010 光电开关计数模块 —— 复刻
hardware/wemos-d1/sensors/radial_counting_module(H2010光电开关)/radial_counting_module_v1.ino

协议与 touch_sensor_switch 一致（事件驱动 switch 上报 + 周期心跳），仅默认 sensor_id 不同
"""
import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sensors.touch_sensor_switch.touch_sensor_switch import TouchSensorSwitch

log = logging.getLogger(__name__)


class RadialCountingModule(TouchSensorSwitch):
    """H2010 光电开关：协议与触摸开关一致，单独成类便于注册和未来差异化"""
    DEFAULT_FLIP_PERIOD_S = 8.0  # 旋转遮挡频率比触摸快一些


def main():
    parser = argparse.ArgumentParser(description="虚拟 H2010 光电开关计数模块")
    parser.add_argument("--id", default="H2010-PHOTO-001")
    parser.add_argument("--broker", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--username", default="")
    parser.add_argument("--password", default="")
    parser.add_argument("--status-report-interval", type=int,
                        default=RadialCountingModule.DEFAULT_STATUS_REPORT_INTERVAL)
    parser.add_argument("--flip-period-s", type=float,
                        default=RadialCountingModule.DEFAULT_FLIP_PERIOD_S)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    node = RadialCountingModule(
        node_id=args.id,
        broker=args.broker,
        port=args.port,
        username=args.username,
        password=args.password,
        status_report_interval=args.status_report_interval,
        flip_period_s=args.flip_period_s,
    )
    try:
        node.run()
    except KeyboardInterrupt:
        node.stop()


if __name__ == "__main__":
    main()
