"""
MQTT服务模块
负责MQTT连接管理、主题订阅、消息接收和发送
连接参数从 platform_config 读取，支持 reload 后重连以应用新配置
"""
import json
import logging
import re
from typing import Callable, Dict, Optional
import paho.mqtt.client as mqtt

from config.platform_config import get_config
from .sensors_service.sensor_upload_data_handlers import handle_mqtt_data_message
from .sensors_service.sensor_upload_status_handlers import handle_mqtt_status_message
from .devices_service.device_upload_status_handlers import handle_mqtt_device_status_message

logger = logging.getLogger(__name__)


class MQTTService:
    """
    MQTT服务类
    管理MQTT客户端连接、消息路由和发送
    """

    def __init__(self):
        """初始化MQTT服务"""
        self.client: Optional[mqtt.Client] = None
        self.is_connected = False
        self.handlers: Dict[str, Callable] = {}  # 主题模式 -> 处理器函数
        self.pending_subscriptions = []  # 待订阅的主题列表

    def connect(self, timeout: int = 5) -> bool:
        """
        连接到MQTT服务器

        Args:
            timeout: 连接超时时间（秒）

        Returns:
            bool: 连接成功返回True
        """
        try:
            # 从 platform_settings 数据库读取连接参数（支持 reload 后重连生效）
            broker = get_config("mqtt_broker", "127.0.0.1", str)
            port = get_config("mqtt_port", 1883, int)
            keepalive = get_config("mqtt_keepalive", 60, int)
            username = get_config("mqtt_username", "", str)
            password = get_config("mqtt_password", "", str)

            # 创建MQTT客户端
            self.client = mqtt.Client(client_id="django_iot_platform")
            if username and password:
                self.client.username_pw_set(username, password)

            # 设置回调函数
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            logger.info(f"正在连接MQTT服务器: {broker}:{port}")
            self.client.connect(broker, port, keepalive)

            # 启动网络循环（后台线程）
            self.client.loop_start()

            # 等待连接建立
            import time
            start_time = time.time()
            while not self.is_connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)  # 每100ms检查一次

            if self.is_connected:
                logger.info("MQTT连接成功，已建立通信")
                return True
            else:
                logger.error(f"MQTT连接超时（{timeout}秒）")
                self.client.loop_stop()
                return False

        except Exception as e:
            logger.error(f"连接MQTT服务器失败: {e}", exc_info=True)
            if self.client:
                self.client.loop_stop()
            return False

    def start(self):
        """启动MQTT服务（阻塞式循环）"""
        if self.client:
            logger.info("MQTT服务启动，开始监听消息...")
            try:
                import time
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
        else:
            logger.error("MQTT客户端未初始化，请先调用connect()")

    def stop(self):
        """停止MQTT服务"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.client = None
            self.is_connected = False
            logger.info("MQTT服务已停止")

    def reconnect(self, timeout: int = 5) -> bool:
        """
        断开并重新连接，使用最新 platform_config 配置
        用于配置修改后无需重启服务即可生效
        """
        self.stop()
        return self.connect(timeout=timeout)

    def subscribe(self, topic: str, qos: int = 1):
        """
        订阅MQTT主题

        Args:
            topic: MQTT主题（支持通配符 + 和 #）
            qos: 服务质量等级（0, 1, 2）
        """
        subscription = (topic, qos)
        if subscription not in self.pending_subscriptions:
            self.pending_subscriptions.append(subscription)

        if not self.is_connected:
            logger.debug(f"MQTT未连接，主题 {topic} 将在连接后自动订阅")
            return

        try:
            result, mid = self.client.subscribe(topic, qos=qos)
            if result == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"✓ 已订阅主题: {topic} (QoS={qos})")
            else:
                logger.error(f"✗ 订阅主题失败: {topic}, 错误码: {result}")
        except Exception as e:
            logger.error(f"订阅主题异常: {topic}, {e}", exc_info=True)

    def publish(self, topic: str, payload: dict, qos: int = 1) -> bool:
        """
        发布消息到MQTT主题

        Args:
            topic: MQTT主题
            payload: 消息内容（字典，会自动转JSON）
            qos: 服务质量等级

        Returns:
            bool: 发布成功返回True
        """
        if not self.is_connected:
            logger.error(f"MQTT未连接，无法发布消息到: {topic}")
            return False

        try:
            message = json.dumps(payload, ensure_ascii=False)
            result = self.client.publish(topic, message, qos=qos)

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"✓ 消息发布成功 - 主题: {topic}")
                logger.debug(f"  消息内容: {message}")
                return True
            else:
                logger.error(f"✗ 消息发布失败 - 主题: {topic}, 错误码: {result.rc}")
                return False

        except Exception as e:
            logger.error(f"发布消息异常: {topic}, {e}", exc_info=True)
            return False

    def register_handler(self, topic_pattern: str, handler: Callable):
        """
        注册消息处理器

        Args:
            topic_pattern: 主题模式（支持通配符 + 和 #）
            handler: 处理函数，签名为 handler(topic, payload)
        """
        self.handlers[topic_pattern] = handler
        logger.info(f"✓ 已注册处理器: {topic_pattern} -> {handler.__name__}")

    def setup_sensor_data_handler(self):
        """
        快速设置传感器数据处理器
        自动注册处理器并订阅数据主题
        """
        self.register_handler('iot/sensors/+/data', handle_mqtt_data_message)
        self.subscribe('iot/sensors/+/data', qos=1)
        logger.info("✓ 传感器数据处理器设置完成")

    def setup_sensor_status_handler(self):
        """
        快速设置传感器状态处理器
        自动注册处理器并订阅状态主题
        """
        self.register_handler('iot/sensors/+/status', handle_mqtt_status_message)
        self.subscribe('iot/sensors/+/status', qos=1)
        logger.info("✓ 传感器状态处理器设置完成")

    def setup_device_status_handler(self):
        """
        快速设置设备状态处理器
        自动注册处理器并订阅设备状态主题
        """
        self.register_handler('iot/devices/+/status', handle_mqtt_device_status_message)
        self.subscribe('iot/devices/+/status', qos=1)
        logger.info("✓ 设备状态处理器设置完成")

    def _on_connect(self, client, userdata, flags, rc):
        """MQTT连接成功回调"""
        if rc == 0:
            self.is_connected = True
            logger.info("✓ MQTT连接成功")

            if self.pending_subscriptions:
                logger.info(f"开始订阅 {len(self.pending_subscriptions)} 个主题...")
                for topic, qos in self.pending_subscriptions:
                    try:
                        result, mid = self.client.subscribe(topic, qos=qos)
                        if result == mqtt.MQTT_ERR_SUCCESS:
                            logger.info(f"✓ 已订阅主题: {topic} (QoS={qos})")
                        else:
                            logger.error(f"✗ 订阅主题失败: {topic}, 错误码: {result}")
                    except Exception as e:
                        logger.error(f"订阅主题异常: {topic}, {e}", exc_info=True)
        else:
            self.is_connected = False
            error_messages = {
                1: "协议版本错误",
                2: "客户端ID无效",
                3: "服务器不可用",
                4: "用户名或密码错误",
                5: "未授权"
            }
            error_msg = error_messages.get(rc, f"未知错误(rc={rc})")
            logger.error(f"✗ MQTT连接失败: {error_msg}")

    def _on_disconnect(self, client, userdata, rc):
        """MQTT断开连接回调"""
        self.is_connected = False
        if rc != 0:
            logger.warning(f"⚠ MQTT意外断开，错误码: {rc}")
        else:
            logger.info("MQTT正常断开")

    def _extract_id_from_topic(self, topic: str, pattern: str) -> Optional[str]:
        """
        从主题中提取设备ID或传感器ID。
        如 iot/sensors/DHT11-WEMOS-001/data -> DHT11-WEMOS-001
        iot/devices/SG_80_01/status -> SG_80_01
        """
        parts = topic.split('/')
        if len(parts) >= 3:
            return parts[2]  # iot / sensors|devices / ID / ...
        return None

    def _on_message(self, client, userdata, msg):
        """MQTT消息接收回调，将消息路由到对应的处理器"""
        topic = msg.topic

        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            # 提取并显示具体 ID（传感器或设备）
            extracted_id = None
            if '/sensors/' in topic:
                extracted_id = self._extract_id_from_topic(topic, 'iot/sensors/+/')
                payload_id = payload.get('sensor_id', '') if isinstance(payload, dict) else ''
                id_display = payload_id or extracted_id or '未知'
                logger.info(f"📨 收到消息 - 主题: {topic} [传感器ID: {id_display}]")
            elif '/devices/' in topic:
                extracted_id = self._extract_id_from_topic(topic, 'iot/devices/+/')
                payload_id = payload.get('device_id', '') if isinstance(payload, dict) else ''
                id_display = payload_id or extracted_id or '未知'
                logger.info(f"📨 收到消息 - 主题: {topic} [设备ID: {id_display}]")
            else:
                logger.info(f"📨 收到消息 - 主题: {topic}")
            logger.debug(f"  消息内容: {payload}")

            handler = self._find_handler(topic)

            if handler:
                try:
                    handler(topic, payload)
                except Exception as e:
                    id_hint = self._extract_id_from_topic(topic, '') or ''
                    extra = f" [ID: {id_hint}]" if id_hint else ""
                    logger.error(f"处理器执行异常: {topic}{extra}, {e}", exc_info=True)
            else:
                id_hint = self._extract_id_from_topic(topic, '') or ''
                extra = f" [ID: {id_hint}]" if id_hint else ""
                logger.warning(f"⚠ 未找到匹配的处理器: {topic}{extra}")

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {topic}, {e}")
            logger.debug(f"  原始消息: {msg.payload}")
        except Exception as e:
            logger.error(f"消息处理异常: {topic}, {e}", exc_info=True)

    def _find_handler(self, topic: str) -> Optional[Callable]:
        """查找匹配的消息处理器"""
        for pattern, handler in self.handlers.items():
            if self._topic_matches(topic, pattern):
                return handler
        return None

    @staticmethod
    def _topic_matches(topic: str, pattern: str) -> bool:
        """检查主题是否匹配模式（支持MQTT通配符）"""
        pattern_regex = pattern.replace('+', r'[^/]+')
        pattern_regex = pattern_regex.replace('#', r'.*')
        pattern_regex = f'^{pattern_regex}$'
        return re.match(pattern_regex, topic) is not None


# 全局单例
mqtt_service = MQTTService()
