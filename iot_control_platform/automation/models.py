"""
自动化规则模型 - 简化版
使用 script（脚本）实现自动化逻辑，devices 字典提供设备和传感器数据
与 devices.Device、sensors.Sensor 模型对接
"""
from django.db import models


PROCESS_STATUS_CHOICES = [
    ('idle', '未启动'),
    ('running', '正在运行'),
    ('stopped_by_user', '由用户停止'),
    ('error_stopped', '由错误停止'),
]


class AutomationRule(models.Model):
    """
    自动化规则 - 运行脚本实现自动化逻辑

    脚本可访问关联的设备和传感器，数据来源于：
    - Sensor：sensor.data_records (SensorData)，最新一条的 data 字段
    - Device：device.data_records (DeviceData)，最新一条的 data 字段
    设备控制通过 DeviceType.commands 定义的命令发送
    """

    # ========== 基本信息 ==========
    name = models.CharField(max_length=100, verbose_name="规则名称")
    description = models.TextField(blank=True, verbose_name="规则描述")
    script_id = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="脚本唯一ID",
        help_text="唯一标识，通过 execute_by_script_id('xxx') 调用执行，如 humidity_overflow_print、humidity_alert",
    )

    # ========== 脚本 ==========
    script = models.TextField(
        blank=True,
        verbose_name="脚本",
        help_text="""
        Python 脚本，Arduino 风格：from engine import sensors, devices，定义带 loop() 的控制器类。

        engine 由引擎注入，含 sensors、devices。控制器类 __init__ 相当于 setup()，loop() 返回 True/False。

        参见 automation/script/sample_file.txt 完整示例。
        """
    )

    # ========== 关联设备列表 ==========
    device_list = models.JSONField(
        default=list,
        verbose_name="设备与传感器列表",
        help_text="""
        脚本中可访问的设备和传感器，device_id 需与 devices.Device 或 sensors.Sensor 表中的 device_id 对应。
        格式示例：
        [
            {"device_id": "DHT11-WEMOS-001", "device_type": "Sensor", "name": "温湿度传感器"},
            {"device_id": "SG_80_01", "device_type": "Device", "name": "LED灯"}
        ]
        """
    )

    # ========== 轮询状态 ==========
    is_launched = models.BooleanField(
        default=False,
        verbose_name="是否启动轮询",
        help_text="标记该规则是否应持续轮询执行"
    )
    poll_interval = models.PositiveIntegerField(
        default=30,
        verbose_name="轮询间隔（秒）",
        help_text="轮询执行的时间间隔，单位为秒，最小 1 秒"
    )
    process_status = models.CharField(
        max_length=20,
        choices=PROCESS_STATUS_CHOICES,
        default='idle',
        verbose_name="进程状态"
    )
    error_message = models.TextField(
        blank=True,
        verbose_name="错误信息",
        help_text="当 process_status 为 error_stopped 时的错误详情"
    )

    # ========== 时间戳 ==========
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "自动化规则"
        verbose_name_plural = "自动化规则"
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_device_count(self):
        """获取关联设备数量"""
        if not isinstance(self.device_list, list):
            return 0
        return len(self.device_list)

    def get_device_summary(self):
        """获取设备列表简要摘要，要求每项为 {"device_id": "xxx", "device_type": "Sensor/Device"}"""
        if not isinstance(self.device_list, list) or not self.device_list:
            return "-"
        parts = []
        for item in self.device_list[:5]:
            if not isinstance(item, dict):
                return "输入不规范"
            did = item.get('device_id', '-')
            dtype = item.get('device_type', '-')
            parts.append(f"{did}({dtype})")
        if len(self.device_list) > 5:
            parts.append("...")
        return ", ".join(parts)

    def execute(self):
        """执行脚本，返回 True/False"""
        try:
            from automation.engine import execute_rule
            return execute_rule(self)
        except Exception:
            return False

    @classmethod
    def execute_by_script_id(cls, script_id: str):
        """
        按脚本唯一ID执行规则。
        Returns:
            bool: 执行成功返回 True，否则 False（未找到规则或执行失败）
        """
        try:
            rule = cls.objects.get(script_id=script_id)
            return rule.execute()
        except cls.DoesNotExist:
            return False

    @classmethod
    def execute_by_script_id_with_timed_polling(cls, script_id: str, interval_seconds: float = 30):
        """
        按脚本唯一ID定时轮询执行规则，Ctrl+C 停止。
        Args:
            script_id: 脚本唯一ID
            interval_seconds: 轮询间隔（秒），默认 30
        """
        import time
        try:
            rule = cls.objects.get(script_id=script_id)
        except cls.DoesNotExist:
            return
        print(f"定时轮询已启动：script_id={script_id}，间隔 {interval_seconds} 秒，Ctrl+C 停止\n")
        try:
            while True:
                rule.execute()
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("\n定时轮询已停止")
