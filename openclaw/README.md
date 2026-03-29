# OpenClaw 接入方案说明

OpenClaw 作为本物联网平台的“智能技能层”，负责将自然语言意图（Intents）或代理工具调用（Tool Calls）转化为本系统的具体操作（如开关灯、查询传感器数值等）。

## 1. 架构设计

- **技能定义 (Skills)**: 位于 `openclaw/skills/` 目录下，每个文件代表一个或一组相关的智能功能。
- **桥接层 (Bridge)**: 技能通过调用 `iot_control_platform` 内的 `services/mqtt_service.py` 或直接操作 Django ORM 模型来执行。
- **双向通信**:
    - **Control**: AI Agent -> OpenClaw Skill -> MQTT/ORM -> Device
    - **Query**: AI Agent -> OpenClaw Skill -> ORM/Database -> Information

## 2. 技能目录结构

```text
openclaw/
├── README.md           # 本说明文档
├── skills/             # 存放所有技能定义
│   ├── __init__.py
│   ├── device_control.py # 设备控制类技能（如：打开/关闭设备）
│   └── sensor_query.py   # 传感器查询类技能（如：当前温度是多少？）
└── core.py             # (可选) OpenClaw 的核心逻辑，用于加载和分发技能
```

## 3. 开发规范

1. **原子性**: 每个技能函数应只执行一个明确的任务。
2. **返回描述**: 技能应返回易于被 AI 模型理解的字符串结果（如："客厅灯已成功打开"）。
3. **错误处理**: 捕捉硬件超时或 MQTT 连接失败等异常，并返回友好的提示。

## 4. 示例代码 (device_control.py)

```python
# 示例：通过 OpenClaw 控制设备
from iot_control_platform.services.mqtt_service import MQTTService
from iot_control_platform.devices.models import Device

def turn_on_device(device_id):
    """
    OpenClaw 意图：开启特定设备
    """
    try:
        device = Device.objects.get(id=device_id)
        # 调用系统现有的 MQTT 服务发送指令
        # 具体逻辑需根据设备协议实现
        return f"设备 {device.name} 开启指令已发送"
    except Device.DoesNotExist:
        return "未找到指定的设备"
```
