# 嵌入式程序编写指南——符合后端设计规范

本文档说明如何编写符合后端设计规范的嵌入式程序，使传感器/设备能正确与 Django 平台对接。设计说明见 [hardware_code_design.md](hardware_code_design.md)。

---

## 一、编写前准备

### 1.1 后端先建模型

嵌入式程序的 `sensor_id` / `device_id` 必须与后端数据库中的记录一致，否则 Handler 无法找到对应模型，消息会被丢弃。

**传感器：**

- 在 Django Admin 或 Shell 中创建 `SensorType`、`Sensor`
- 记下 `sensor_id`（如 `Rotation-001`）

**设备：**

- 创建 `DeviceType`、`Device`
- 记下 `device_id`（如 `sg90_001`）

### 1.2 确定类型与目录

| 类型 | 目录 | 示例 |
|-----|------|------|
| 传感器 | `embedded_code/sensors/{sensor_type}/` | `rotation_sensor` |
| 设备 | `embedded_code/devices/{device_type}/` | `SG_90` |

---

## 二、主题命名规范（必须遵守）

后端 Handler 按固定主题订阅，嵌入式程序必须使用相同规则。

### 2.1 传感器

```
iot/sensors/{sensor_id}/data     — 数据上报（发布）
iot/sensors/{sensor_id}/control  — 控制命令（订阅）
iot/sensors/{sensor_id}/status   — 状态上报（发布）
```

### 2.2 设备

```
iot/devices/{device_id}/control  — 控制命令（订阅）
iot/devices/{device_id}/status   — 状态上报（发布）
```

**注意：** `{sensor_id}`、`{device_id}` 需与数据库中的值完全一致。

---

## 三、先写 form 文件，再写程序

建议先创建三份 form 文件作为契约，再按契约实现 .ino 程序。form 文件与后端 `SensorType` / `DeviceType` 的 `commands`、`data_fields` 等对应。

### 3.1  sensors 目录下需要的文件

| 文件 | 说明 |
|-----|------|
| `mqtt_command_form.txt` | 后端下发的命令格式（与 SensorType.commands 对应） |
| `mqtt_data_form.txt` | 数据上报格式（与 SensorData.data 对应） |
| `mqtt_status_form.txt` | 状态上报格式（与 SensorStatusCollection.data 对应） |

### 3.2 devices 目录下需要的文件

| 文件 | 说明 |
|-----|------|
| `mqtt_command_form.txt` | 后端下发的命令格式（与 DeviceType.commands 对应） |
| `mqtt_status_form.txt` | 状态上报格式（与 DeviceData.data 对应） |

---

## 四、数据上报格式（传感器）

后端 `sensor_upload_data_handlers` 要求：

### 4.1 必须字段

| 字段 | 类型 | 说明 |
|-----|------|------|
| `sensor_id` | string | 与 Sensor.sensor_id 一致 |
| `data` | object | 采集数据，键名与 SensorType.data_fields 可对应 |
| `timestamp` | number | Unix 秒级时间戳，支持毫秒（≥1e12 时自动除以 1000） |

### 4.2 示例（mqtt_data_form.txt）

```json
{
  "sensor_id": "Rotation-001",
  "data": {"raw": 512, "position": 50, "angle": 90},
  "timestamp": 1770733931
}
```

### 4.3 程序实现要点

```cpp
doc["sensor_id"] = SENSOR_ID;  // 必须

JsonObject data = doc.createNestedObject("data");  // data 必须是对象
data["raw"] = sensorValue;
data["position"] = positionPercent;
data["angle"] = angle;

doc["timestamp"] = timeClient.getEpochTime();  // NTP 秒级时间戳
```

---

## 五、状态上报格式（传感器与设备）

后端 `sensor_upload_status_handlers` / `device_upload_status_handlers` 要求：

### 5.1 传感器必须字段

| 字段 | 类型 | 说明 |
|-----|------|------|
| `sensor_id` | string | 与 Sensor.sensor_id 一致 |
| `event` | string | 如 online、heartbeat、interval_updated |
| `status` | object | 状态内容 |
| `timestamp` | number | Unix 秒级时间戳 |
| `check_code` | string（可选） | 命令响应时回传，用于确认 |

### 5.2 设备必须字段

| 字段 | 类型 | 说明 |
|-----|------|------|
| `device_id` | string | 与 Device.device_id 一致 |
| `event` | string | 如 online、heartbeat、angle_updated |
| `status` | object | 状态内容 |
| `timestamp` | number | Unix 秒级时间戳 |
| `check_code` | string（可选） | 命令响应时回传 |

### 5.3 程序实现要点

```cpp
// 传感器
doc["sensor_id"] = SENSOR_ID;
doc["event"] = event;
doc["timestamp"] = timeClient.getEpochTime();

JsonObject status = doc.createNestedObject("status");
status["is_enabled"] = isEnabled;
status["samplingInterval"] = samplingInterval;
// ...

if (checkCode != nullptr && checkCode[0] != '\0') {
  doc["check_code"] = checkCode;  // 命令响应时必填
}

// 设备
doc["device_id"] = DEVICE_ID;
// 其余同上
```

---

## 六、控制命令格式（mqtt_command_form）

后端按 `SensorType.commands` / `DeviceType.commands` 中的 `mqtt_message` 下发。嵌入式程序在 `mqttCallback` 中解析。

### 6.1 通用结构

每条命令的 `mqtt_message` 至少包含 `command`，参数名需与 form 中一致，例如：

```json
{"command": "set_angle", "angle": 90, "check_code": "123456"}
```

### 6.2 程序解析示例

```cpp
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  StaticJsonDocument<256> doc;
  deserializeJson(doc, payload, length);

  const char* command = doc["command"];
  const char* checkCode = doc["check_code"].as<const char*>();
  if (checkCode == nullptr) checkCode = "";

  if (strcmp(command, "set_angle") == 0) {
    int angle = doc["angle"];
    // 执行并回传 check_code
    sendStatusUpdate("angle_updated", checkCode);
  }
  // ...
}
```

### 6.3 check_code 回传

- 收到带 `check_code` 的命令时，在状态上报中**原样回传**
- 后端依赖此流程实现 `send_custom_command_with_make_sure` 的确认
- 心跳等非命令响应可不带 `check_code`

---

## 七、心跳与在线判定

### 7.1 心跳要求

- 定期发送 `event: "heartbeat"` 的状态报文
- 建议间隔：10–600 秒（可由 `set_status_interval` 配置）
- 心跳用于更新 `Sensor.last_seen` / `Device.last_seen`，后端据此判断在线

### 7.2 实现示例

```cpp
if (millis() - lastStatusReportTime >= statusReportInterval * 1000UL) {
  sendStatusUpdate("heartbeat");  // 不带 check_code
  lastStatusReportTime = millis();
}
```

---

## 八、时间戳规范

### 8.1 使用 NTP

- 使用 `NTPClient` 获取 `getEpochTime()`
- 时间戳为**秒级** Unix 时间（整数或浮点均可）

### 8.2 后端兼容

- 若传入毫秒（≥1e12），后端会自动除以 1000 转为秒

---

## 九、新建传感器 checklist

1. 创建目录：`sensors/{sensor_type}/`
2. 编写 `mqtt_data_form.txt`：`sensor_id`、`data`、`timestamp`
3. 编写 `mqtt_status_form.txt`：`sensor_id`、`event`、`status`、`timestamp`、`check_code`（可选）
4. 编写 `mqtt_command_form.txt`：与 SensorType.commands 中的 mqtt_message 一致
5. 在 Django 中创建 SensorType、Sensor，配置 `data_fields`、`commands`
6. 程序中 `SENSOR_ID` 与 `sensor_id` 保持一致
7. 主题：`iot/sensors/{sensor_id}/data|control|status`
8. 实现 `sendSensorData()`、`sendStatusUpdate()`、`mqttCallback()`
9. 实现 NTP 同步与心跳

---

## 十、新建设备 checklist

1. 创建目录：`devices/{device_type}/`
2. 编写 `mqtt_status_form.txt`：`device_id`、`event`、`status`、`timestamp`、`check_code`（可选）
3. 编写 `mqtt_command_form.txt`：与 DeviceType.commands 一致
4. 在 Django 中创建 DeviceType、Device，配置 `commands`
5. 程序中 `DEVICE_ID` 与 `device_id` 保持一致
6. 主题：`iot/devices/{device_id}/control|status`
7. 实现 `sendStatusUpdate()`、`mqttCallback()`
8. 实现 NTP 同步与心跳

---

## 十一、常见错误与排查

| 现象 | 可能原因 |
|-----|---------|
| 数据/状态不落库 | sensor_id / device_id 与数据库不一致 |
| 命令无法确认 | 命令响应时未回传 check_code |
| 时间异常 | 未使用 NTP，时间戳错误 |
| 主题不匹配 | 未按 `iot/sensors/` 或 `iot/devices/` 规范 |
| JSON 解析失败 | 字段类型错误（如 data 非 object、timestamp 非数字） |
| 传感器不存在 / 设备不存在 | 后端未创建对应 Sensor / Device 记录 |

---

## 十二、参考示例

| 类型 | 路径 | 说明 |
|-----|------|------|
| 传感器 | `sensors/rotation_sensor/rotation_sensor_v1.ino` | 数据+状态+命令完整流程 |
| 传感器 | `sensors/temp_humi_sensor/temp_humi_sensor_v3.ino` | 温湿度传感器 |
| 设备 | `devices/SG_90/sg90_control.ino` | 舵机控制 |
| 设备 | `devices/pin_control/pin_control_d5.ino` | 高低电平控制 |
