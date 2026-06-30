"""
主层 WebSocket Consumer。

M1 仅含：
- _BaseAuthedConsumer：未登录直接 4001 close 的基类（后续 consumer 都继承）
- PingConsumer：连通性联调用的 echo consumer（/ws/_ping/）

M2 起会在此追加 SensorListConsumer / SensorStreamConsumer 等。
"""
from __future__ import annotations

import logging
from typing import List

from channels.generic.websocket import AsyncJsonWebsocketConsumer

log = logging.getLogger(__name__)


class _BaseAuthedConsumer(AsyncJsonWebsocketConsumer):
    """所有 consumer 公共：未登录直接 4001 close；统一 group_add / discard。"""

    groups_to_join: List[str] = []

    async def connect(self):
        user = self.scope.get("user")
        if user is None or not getattr(user, "is_authenticated", False):
            await self.close(code=4001)
            return
        for group in self._compute_groups():
            await self.channel_layer.group_add(group, self.channel_name)
        await self.accept()
        await self._send_initial()

    async def disconnect(self, code):
        for group in self._compute_groups():
            try:
                await self.channel_layer.group_discard(group, self.channel_name)
            except Exception:
                pass

    def _compute_groups(self) -> List[str]:
        """子类可覆盖。默认返回 groups_to_join。"""
        return list(self.groups_to_join)

    async def _send_initial(self):
        """子类可覆盖：连接建立后立刻发的首条消息（如快照）。"""
        return None

    async def receive_json(self, content, **kwargs):
        """MVP 阶段客户端不主动 send 业务消息，仅支持 ping/pong 保活。"""
        if isinstance(content, dict) and content.get("action") == "ping":
            await self.send_json({"action": "pong"})


class PingConsumer(_BaseAuthedConsumer):
    """连通性联调：accept 后立刻发一条 hello，客户端 send 任何 JSON 都原样回显。"""

    async def _send_initial(self):
        user = self.scope.get("user")
        await self.send_json({
            "event": "hello",
            "data": {
                "msg": "websocket ok",
                "user": getattr(user, "username", None),
            },
        })

    async def receive_json(self, content, **kwargs):
        if isinstance(content, dict) and content.get("action") == "ping":
            await self.send_json({"action": "pong"})
            return
        await self.send_json({"event": "echo", "data": content})


# ==================== 传感器 ====================
class SensorStreamConsumer(_BaseAuthedConsumer):
    """单传感器订阅：合并推送 data + status。

    URL: /ws/sensors/<sensor_id>/
    """

    def _compute_groups(self):
        sid = self.scope["url_route"]["kwargs"]["sensor_id"]
        return [f"sensors.{sid}"]

    async def broadcast_sensor_data(self, event):
        await self.send_json({"event": "sensor.data", "data": event["payload"]})

    async def broadcast_sensor_status(self, event):
        await self.send_json({"event": "sensor.status", "data": event["payload"]})


class SensorListConsumer(_BaseAuthedConsumer):
    """全量传感器订阅：列表页 / Dashboard 用。

    URL: /ws/sensors/
    """

    groups_to_join = ["sensors.all"]

    async def broadcast_sensor_data(self, event):
        await self.send_json({"event": "sensor.data", "data": event["payload"]})

    async def broadcast_sensor_status(self, event):
        await self.send_json({"event": "sensor.status", "data": event["payload"]})


# ==================== 设备 ====================
class DeviceStreamConsumer(_BaseAuthedConsumer):
    """单设备订阅。

    URL: /ws/devices/<device_id>/
    """

    def _compute_groups(self):
        did = self.scope["url_route"]["kwargs"]["device_id"]
        return [f"devices.{did}"]

    async def broadcast_device_status(self, event):
        await self.send_json({"event": "device.status", "data": event["payload"]})


class DeviceListConsumer(_BaseAuthedConsumer):
    """全量设备订阅：列表页 / Dashboard 用。

    URL: /ws/devices/
    """

    groups_to_join = ["devices.all"]

    async def broadcast_device_status(self, event):
        await self.send_json({"event": "device.status", "data": event["payload"]})


# ==================== MQTT broker 系统状态 ====================
class MqttSystemConsumer(_BaseAuthedConsumer):
    """MQTT broker 连接状态推送。

    URL: /ws/system/mqtt/

    建连时立刻发一次当前状态（从 mqtt_service.is_connected 读），后续状态变化由
    mqtt_service._on_connect/_on_disconnect 通过 dispatch.publish_mqtt_system 推过来。
    """

    groups_to_join = ["system.mqtt"]

    async def _send_initial(self):
        from channels.db import database_sync_to_async

        async def _read():
            return await database_sync_to_async(self._snapshot)()

        await self.send_json({"event": "system.mqtt", "data": await _read()})

    @staticmethod
    def _snapshot():
        try:
            from config.platform_config import get_config
            from services.mqtt_service import mqtt_service
            return {
                "is_connected": bool(getattr(mqtt_service, "is_connected", False)),
                "broker": get_config("mqtt_broker", "127.0.0.1", str),
                "port": get_config("mqtt_port", 1883, int),
            }
        except Exception:
            return {"is_connected": False}

    async def broadcast_system_mqtt(self, event):
        await self.send_json({"event": "system.mqtt", "data": event["payload"]})


# ==================== 自动化规则 ====================
class AutomationConsumer(_BaseAuthedConsumer):
    """自动化脚本与结构化控制方案全量订阅。

    URL: /ws/automation/
    任何规则的 is_launched / process_status / error_message / last_run_time 变化
    都会推送到所有订阅者；前端按 payload.id 找到本地对象 patch 字段。
    """

    groups_to_join = ["automation.rules"]

    async def broadcast_automation_rule(self, event):
        await self.send_json({"event": "automation.rule", "data": event["payload"]})

    async def broadcast_automation_control(self, event):
        await self.send_json({"event": "automation.control", "data": event["payload"]})
