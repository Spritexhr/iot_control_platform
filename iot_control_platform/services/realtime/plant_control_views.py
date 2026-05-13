"""
EB 装置扰动控制 API。

POST /api/realtime/plant/EB/disturbance
    body: {"scenario": "deb_snowball"}
    通过 MQTT 把控制消息发给模拟器(topic: plant/EB/disturbance/control)
"""
from __future__ import annotations

import logging

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from services.mqtt_service import mqtt_service

log = logging.getLogger(__name__)

VALID_SCENARIOS = {
    "none", "ethylene_overfeed", "cooling_failure", "deb_snowball",
}

CONTROL_TOPIC = "plant/EB/disturbance/control"


@api_view(["POST"])
@permission_classes([AllowAny])
def inject_disturbance(request):
    scenario = (request.data.get("scenario") or "").strip()
    if scenario not in VALID_SCENARIOS:
        return Response(
            {"detail": f"未知 scenario,有效值: {sorted(VALID_SCENARIOS)}"},
            status=400,
        )
    ok = mqtt_service.publish(CONTROL_TOPIC, {"scenario": scenario}, qos=1)
    if not ok:
        return Response({"detail": "MQTT 未连接,无法下发"}, status=503)
    log.info("已下发扰动场景: %s", scenario)
    return Response({"scenario": scenario, "delivered": True})
