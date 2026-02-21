"""
设备管理数据模型
用于管理物联网输出器（执行器）设备
参考 sensors 应用结构实现
"""
from django.db import models
from django.utils import timezone
from datetime import timedelta


class DeviceType(models.Model):
    """
    设备类型模型
    定义不同类型的输出器（LED、舵机、继电器等）
    存储设备类型级别的固定参数和配置
    参考 SensorType 结构
    """
    DeviceType_id = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name="设备类型唯一ID",
        help_text="例如：LED-01、FAN-01"
    )

    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="设备类型名称",
        help_text="例如：LED灯、智能风扇、继电器"
    )

    description = models.TextField(
        blank=True,
        verbose_name="类型描述",
        help_text="设备类型的详细说明"
    )

    # 状态字段列表（设备上报状态内容中需要提取的字段）
    state_fields = models.JSONField(
        default=list,
        verbose_name="状态字段列表",
        help_text='设备上报的状态字段名称列表。示例：["power_state", "brightness"]'
    )

    # 设备参数列表（设备上报状态时需提取的配置字段）
    config_parameters = models.JSONField(
        default=list,
        verbose_name="配置参数列表",
        help_text='可配置的参数名称列表。示例：["heartbeat_interval"]'
    )

    # 命令列表（可发送给设备的控制命令）
    commands = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="可用命令列表",
        help_text=
        """
        该类型设备支持的命令列表。示例：
        {
            "turn_on": {
                "mqtt_message": {"command": "power_on"},
                "description": "打开设备",
                "params": []
            },
            "turn_off": {
                "mqtt_message": {"command": "power_off"},
                "description": "关闭设备",
                "params": []
            },
            "set_brightness": {
                "mqtt_message": {"command": "set_brightness", "value": "{val}"},
                "description": "设置亮度",
                "params": ["val"]
            }
        }
        """
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间"
    )

    class Meta:
        verbose_name = "设备类型"
        verbose_name_plural = "设备类型"
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_state_fields(self):
        """获取状态字段列表"""
        return self.state_fields if isinstance(self.state_fields, list) else []

    def get_config_parameters(self):
        """获取配置参数列表"""
        return self.config_parameters if isinstance(self.config_parameters, list) else []

    def get_heartbeat_interval(self):
        """获取心跳间隔（秒）"""
        return 60  # 默认值


class Device(models.Model):
    """
    设备模型（输出器/执行器）
    参考 Sensor 结构，专注于控制执行
    设备实例使用设备类型中定义的固定变量和参数
    """

    # ========== 基本信息 ==========
    device_id = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name="设备唯一ID"
    )

    name = models.CharField(
        max_length=100,
        verbose_name="设备名称"
    )

    description = models.TextField(
        blank=True,
        verbose_name="设备描述"
    )

    location = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="设备位置"
    )

    # ========== MQTT 通信 ==========
    mqtt_topic_data = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="状态主题"
    )

    mqtt_topic_control = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="控制主题"
    )

    # ========== 状态管理 ==========
    is_online = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="是否在线"
    )

    last_seen = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="最后上报时间"
    )

    # ========== 时间戳 ==========
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新时间"
    )

    # ========== 关联关系 ==========
    device_type = models.ForeignKey(
        DeviceType,
        on_delete=models.PROTECT,
        related_name='devices',
        verbose_name="设备类型"
    )

    class Meta:
        verbose_name = "设备"
        verbose_name_plural = "设备列表"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.device_id})"

    def save(self, *args, **kwargs):
        """保存时自动设置 MQTT 主题，与 Arduino 固件保持一致"""
        if not self.mqtt_topic_data:
            self.mqtt_topic_data = f"iot/devices/{self.device_id}/status"
        if not self.mqtt_topic_control:
            self.mqtt_topic_control = f"iot/devices/{self.device_id}/control"

        super().save(*args, **kwargs)

    def get_heartbeat_interval(self):
        """获取心跳间隔（从类型获取）"""
        if self.device_type:
            return self.device_type.get_heartbeat_interval()
        return 60

    def check_online_status(self):
        """
        检查设备是否在线
        如果超过心跳间隔的3倍时间未收到心跳，标记为离线
        """
        if self.last_seen:
            heartbeat_interval = self.get_heartbeat_interval()
            timeout = heartbeat_interval * 3
            time_diff = (timezone.now() - self.last_seen).total_seconds()

            if time_diff > timeout:
                if self.is_online:
                    self.is_online = False
                    self.save(update_fields=['is_online', 'updated_at'])
                return False
            return True
        return False

    def update_heartbeat(self):
        """更新心跳时间"""
        self.last_seen = timezone.now()
        self.is_online = True
        self.save(update_fields=['last_seen', 'is_online', 'updated_at'])

    def get_data_count(self, hours=24):
        """
        获取指定时间内的数据记录数

        Args:
            hours: 小时数，默认24小时

        Returns:
            int: 数据记录数
        """
        start_time = timezone.now() - timedelta(hours=hours)
        return self.data_records.filter(timestamp__gte=start_time).count()


class DeviceData(models.Model):
    """
    设备数据记录模型
    存储设备上报的状态、命令执行记录和操作日志
    """
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name='data_records',
        verbose_name="设备"
    )

    # 数据内容（灵活存储各种设备数据）
    data = models.JSONField(
        verbose_name="数据内容",
        help_text="设备上报的数据，如：{'power_state': true, 'brightness': 80}"
    )

    # 时间戳
    timestamp = models.DateTimeField(
        db_index=True,
        verbose_name="数据时间",
        help_text="数据记录的时间戳"
    )

    received_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="接收时间",
        help_text="服务器接收到数据的时间"
    )

    class Meta:
        verbose_name = "设备数据"
        verbose_name_plural = "设备数据记录"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['device', '-timestamp']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        return f"{self.device.device_id} - {self.timestamp}"

    def save(self, *args, **kwargs):
        """保存时自动设置时间戳"""
        if not self.timestamp:
            self.timestamp = timezone.now()

        super().save(*args, **kwargs)

        # 更新设备的最新心跳
        self.device.update_heartbeat()
