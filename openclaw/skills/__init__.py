from .device_control import SKILL_INTENTS as device_control_intents
from .sensor_control import SKILL_INTENTS as sensor_control_intents
from .sensor_query import SKILL_INTENTS as sensor_query_intents
from .device_query import SKILL_INTENTS as device_query_intents

# 聚合所有可用技能
ALL_SKILLS = {
    **device_control_intents,
    **sensor_control_intents,
    **sensor_query_intents,
    **device_query_intents
}
