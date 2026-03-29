import sys
import os
import time
import json
import logging

# 将项目根目录添加到 python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.api_client import api_client
from openclaw.skills.device_control import control_device
from openclaw.skills.sensor_query import query_sensor
from openclaw.skills.device_query import query_device_data

# 配置日志输出
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def discover_all_resources():
    """发现系统中所有的传感器、设备及其可用的控制命令"""
    print("\n" + "=" * 80)
    print("🔍 [系统资源与指令发现] 正在获取 IoT 实体及其控制能力...")
    print("=" * 80)

    # 1. 发现传感器及其命令
    res_sensors = api_client.get("/sensors/")
    sensors = res_sensors.get("results", []) if isinstance(res_sensors, dict) else res_sensors
    print(f"\n📡 传感器列表 ({len(sensors)} 个):")
    for s in sensors:
        name = s.get('name')
        sid = s.get('sensor_id')
        # 从嵌套的 sensor_type_info 中提取命令
        type_info = s.get('sensor_type_info', {})
        commands = type_info.get('commands', {})
        
        print(f"   - 【{name}】 (ID: {sid})")
        if commands:
            for cmd_name, cmd_info in commands.items():
                desc = cmd_info.get('description', '无描述')
                params = cmd_info.get('params', [])
                param_str = f" 参数: {params}" if params else ""
                print(f"     └─ 指令: {cmd_name:<15} | 描述: {desc}{param_str}")
        else:
            print("     └─ (该类型暂未定义控制指令)")

    # 2. 发现执行器设备及其命令
    res_devices = api_client.get("/devices/")
    devices = res_devices.get("results", []) if isinstance(res_devices, dict) else res_devices
    print(f"\n🔌 执行器设备列表 ({len(devices)} 个):")
    for d in devices:
        name = d.get('name')
        did = d.get('device_id')
        # 从嵌套的 device_type_info 中提取命令
        type_info = d.get('device_type_info', {})
        commands = type_info.get('commands', {})

        print(f"   - 【{name}】 (ID: {did})")
        if commands:
            for cmd_name, cmd_info in commands.items():
                desc = cmd_info.get('description', '无描述')
                params = cmd_info.get('params', [])
                param_str = f" 参数: {params}" if params else ""
                print(f"     └─ 指令: {cmd_name:<15} | 描述: {desc}{param_str}")
        else:
            print("     └─ (该类型暂未定义控制指令)")

    # 3. 发现自动化规则
    res_rules = api_client.get("/automation-rules/")
    rules = res_rules.get("results", []) if isinstance(res_rules, dict) else res_rules
    print(f"\n🤖 自动化规则列表 ({len(rules)} 个):")
    for r in rules:
        print(f"   - 名称: {r.get('name'):<20} | 脚本ID: {r.get('script_id'):<20} | 状态: {r.get('process_status')}")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    # 登录并执行全量发现
    if api_client.login():
        discover_all_resources()
    else:
        print("❌ 认证失败，请检查账号密码。")
