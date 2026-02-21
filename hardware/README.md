# 物联网控制平台 - 硬件与嵌入式固件

本目录包含 Wemos D1（ESP8266）嵌入式程序，用于传感器数据采集与执行器设备控制，通过 MQTT 与后端通信。

---

## 目录结构

```
hardware/
└── wemos-d1/
    ├── sensors/                    # 传感器（输入器）
    │   ├── temp_humi_sensor/       # DHT11 温湿度
    │   ├── rotation_sensor/        # 旋转编码器
    │   ├── touch_sensor_switch/     # 触摸开关
    │   └── radial_counting_module/ # H2010 光电开关
    ├── devices/                     # 设备（执行器）
    │   ├── SG_90/                  # SG90 舵机
    │   └── pin_control/            # 引脚高低电平控制
    └── learning_esp8266_WEMOS_D1/  # 学习示例
```

---

## 各模块说明

### 传感器（sensors）

| 目录 | 说明 | 数据字段 |
|-----|------|---------|
| temp_humi_sensor | DHT11 温湿度 | temperature, humidity |
| rotation_sensor | 模拟旋转传感器 | raw, position, angle |
| touch_sensor_switch | 触摸传感器 | - |
| radial_counting_module | 光电开关计数 | - |

### 设备（devices）

| 目录 | 说明 | 命令示例 |
|-----|------|---------|
| SG_90 | 舵机角度控制 | set_angle, current_status |
| pin_control | D5 高低电平 | high, low, current_status |

---

## form 文件

每个传感器/设备目录下通常包含：

| 文件 | 说明 |
|-----|------|
| mqtt_command_form.txt | 后端下发的命令格式，与 SensorType/DeviceType.commands 对应 |
| mqtt_data_form.txt | 数据上报格式（仅传感器） |
| mqtt_status_form.txt | 状态上报格式 |

---

## 开发与烧录

### 环境要求

- Arduino IDE 或 PlatformIO
- 安装 **ESP8266** 开发板支持
- 依赖库：PubSubClient、ArduinoJson、NTPClient、DHT（温湿度）、Servo（舵机）

### 配置修改

在 `.ino` 文件中修改：

- `WIFI_SSID`、`WIFI_PASSWORD`
- `MQTT_SERVER`、`MQTT_PORT`
- `SENSOR_ID` / `DEVICE_ID`（需与 Django 中创建的记录一致）

### 烧录

1. 选择开发板：Wemos D1 R1 或 NodeMCU 1.0
2. 选择端口
3. 上传

---

## 相关文档

| 文档 | 说明 |
|-----|------|
| [硬件程序设计](../docs/hardware_code/hardware_code_design.md) | MQTT 连接、form 文件核心作用 |
| [嵌入式编写指南](../docs/hardware_code/hardware_guide.md) | 符合后端规范的固件编写步骤 |
| [项目概述](../docs/PROJECT_DOCUMENTATION.md) | 通信协议、主题结构 |
| [部署前准备](../docs/deployment/before_deploy.md) | EMQX 安装 |
