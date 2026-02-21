# 嵌入式硬件程序设计文档

本文档描述 Wemos D1（ESP8266）嵌入式程序的 MQTT 连接流程，以及传感器、设备端 `mqtt_command_form`、`mqtt_data_form`、`mqtt_status_form` 在程序中的核心作用与实现约定。

---

## 一、程序结构概览

| 类型 | 路径 | 示例 |
|-----|------|------|
| 传感器 | `embedded_code/sensors/{sensor_type}/` | rotation_sensor, temp_humi_sensor |
| 设备 | `embedded_code/devices/{device_type}/` | SG_90, pin_control |

传感器负责**采集并上报数据**，设备负责**接收控制命令并执行**。两者均通过 MQTT 与后端通信。

---

## 二、MQTT 连接流程

### 2.1 启动顺序

```
setup() 顺序:
  1. setupSerial()     — 串口输出
  2. setupSensor/SetupServo/SetupPin  — 硬件初始化
  3. setupWiFi()       — 连接 WiFi
  4. setupMQTT()       — 配置 MQTT 主题与回调
  5. setupNTP()        — 时间同步
```

### 2.2 WiFi 连接

```cpp
WiFi.mode(WIFI_STA);
WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
// 轮询等待 WL_CONNECTED，超时约 15 秒
```

### 2.3 MQTT 配置与连接

```cpp
// 主题构建（传感器）
MQTT_TOPIC_DATA    = "iot/sensors/" + String(SENSOR_ID) + "/data";
MQTT_TOPIC_CONTROL = "iot/sensors/" + String(SENSOR_ID) + "/control";
MQTT_TOPIC_STATUS  = "iot/sensors/" + String(SENSOR_ID) + "/status";

// 主题构建（设备）
MQTT_TOPIC_CONTROL = "iot/devices/" + String(DEVICE_ID) + "/control";
MQTT_TOPIC_STATUS  = "iot/devices/" + String(DEVICE_ID) + "/status";

mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
mqttClient.setCallback(mqttCallback);
mqttClient.setBufferSize(512);
```

### 2.4 重连与订阅

在 `mqttReconnect()` 中：

1. 使用 `WemosD1-{SENSOR_ID}` 或 `WemosD1-{DEVICE_ID}` 作为 `clientId`
2. 可选 `MQTT_USERNAME`、`MQTT_PASSWORD` 认证
3. 连接成功后订阅 `MQTT_TOPIC_CONTROL`
4. 发送 `online` 状态上报，证明上线

```cpp
if (mqttClient.connect(clientId.c_str(), MQTT_USERNAME, MQTT_PASSWORD)) {
  mqttClient.subscribe(MQTT_TOPIC_CONTROL.c_str());
  sendStatusUpdate("online");
}
```

### 2.5 主循环中维护连接

```cpp
void loop() {
  if (WiFi.status() != WL_CONNECTED) { setupWiFi(); return; }
  if (!mqttClient.connected()) { mqttReconnect(); }
  mqttClient.loop();  // 必须周期性调用，处理收发

  // 心跳、数据采集等...
  delay(100);
}
```

---

## 三、mqtt_command_form.txt 的核心作用

### 3.1 定义与用途

`mqtt_command_form.txt` 描述**后端下发给设备/传感器的控制命令格式**。嵌入式程序作为**订阅方**，在 `mqttCallback` 中解析并执行。

### 3.2 传感器：rotation_sensor

**内容示例：**

```json
{
  "turn_on": {"mqtt_message": {"command": "enable"}, "description": "启动传感器", "params": []},
  "turn_off": {"mqtt_message": {"command": "disable"}, "description": "关闭传感器", "params": []},
  "set_data_interval": {"mqtt_message": {"command": "set_data_interval", "interval": "{val}"}, "params": ["val"]},
  "set_status_interval": {"mqtt_message": {"command": "set_status_interval", "interval": "{val}"}, "params": ["val"]}
}
```

**在程序中的对应实现：**

```cpp
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  deserializeJson(doc, payload, length);
  const char* command = doc["command"];
  const char* checkCode = doc["check_code"];

  if (strcmp(command, "set_data_interval") == 0) {
    float newInterval = doc["interval"];
    samplingInterval = newInterval;
    sendStatusUpdate("interval_updated", checkCode);
  }
  else if (strcmp(command, "set_status_interval") == 0) {
    int newInterval = doc["interval"];
    statusReportInterval = newInterval;
    sendStatusUpdate("status_interval_updated", checkCode);
  }
  else if (strcmp(command, "enable") == 0) {
    isEnabled = true;
    sendStatusUpdate("sensor_enabled", checkCode);
  }
  else if (strcmp(command, "disable") == 0) {
    isEnabled = false;
    sendStatusUpdate("sensor_disabled", checkCode);
  }
}
```

**核心作用：**

- 明确可识别的 `command` 及 `interval`、`angle` 等参数
- 后端 `SensorType.commands` 按此格式构造 mqtt_message 下发
- `check_code` 在响应时原样回传，供后端 `send_custom_command_with_make_sure` 确认

### 3.3 设备：SG_90

**内容示例：**

```json
{
  "set_angle": {"mqtt_message": {"command": "set_angle", "angle": "{val}"}, "description": "设置舵机角度 0-180°", "params": ["val"]},
  "current_status": {"mqtt_message": {"command": "current_status"}, "params": []},
  "set_status_interval": {"mqtt_message": {"command": "set_status_interval", "interval": "{val}"}, "params": ["val"]}
}
```

**在程序中的对应实现：**

```cpp
if (strcmp(command, "set_angle") == 0) {
  int angle = doc["angle"];
  currentAngle = angle;
  myServo.write(currentAngle);
  sendStatusUpdate("angle_updated", checkCode);
}
else if (strcmp(command, "current_status") == 0) {
  sendStatusUpdate("check_current_angle", checkCode);
}
else if (strcmp(command, "set_status_interval") == 0) {
  statusReportInterval = doc["interval"];
  sendStatusUpdate("status_interval_updated", checkCode);
}
```

---

## 四、mqtt_data_form.txt 的核心作用（仅传感器）

### 4.1 定义与用途

`mqtt_data_form.txt` 描述**传感器采集数据的上报格式**。嵌入式程序作为**发布方**，将采集结果按此格式 JSON 序列化后发布到 `iot/sensors/{sensor_id}/data`。

### 4.2 rotation_sensor 数据格式

**内容示例：**

```json
{
  "sensor_id": "Rotation-001",
  "data": {"raw": 512, "position": 50, "angle": 90},
  "timestamp": 1770733931
}
```

**在程序中的对应实现：**

```cpp
void sendSensorData() {
  readSensorData();  // 读取 raw, positionPercent, angle

  StaticJsonDocument<256> doc;
  doc["sensor_id"] = SENSOR_ID;

  JsonObject data = doc.createNestedObject("data");
  data["raw"] = sensorValue;           // 0-1023
  data["position"] = positionPercent;   // 0-100
  data["angle"] = angle;                // 0-180

  doc["timestamp"] = timeClient.getEpochTime();

  mqttClient.publish(MQTT_TOPIC_DATA.c_str(), jsonString.c_str());
}
```

**核心作用：**

- 约定 `sensor_id`、`data`、`timestamp` 等字段
- 后端 `sensor_upload_data_handlers` 按此格式解析并写入 `SensorData`
- `SensorType.data_fields` 可引用 `data` 内字段（如 `raw`、`position`、`angle`）

---

## 五、mqtt_status_form.txt 的核心作用

### 5.1 定义与用途

`mqtt_status_form.txt` 描述**传感器/设备状态上报格式**。嵌入式程序在以下场景发布到 `iot/sensors/{sensor_id}/status` 或 `iot/devices/{device_id}/status`：

- 上线（`online`）
- 心跳（`heartbeat`）
- 命令执行后回传（如 `angle_updated`、`interval_updated`），并带回 `check_code`

### 5.2 传感器：rotation_sensor

**通用结构：**

```json
{
  "sensor_id": "Rotation-001",
  "event": "interval_updated" | "heartbeat" | "status_interval_updated" | ...,
  "status": {
    "is_enabled": true,
    "samplingInterval": 1,
    "statusReportInterval": 120,
    "raw": 512,
    "position": 50,
    "angle": 90
  },
  "timestamp": 1770731525,
  "check_code": "123456"   // 命令响应时必填
}
```

**在程序中的对应实现：**

```cpp
void sendStatusUpdate(const char* event, const char* checkCode) {
  doc["sensor_id"] = SENSOR_ID;
  doc["event"] = event;
  doc["timestamp"] = timeClient.getEpochTime();

  JsonObject status = doc.createNestedObject("status");
  status["is_enabled"] = isEnabled;
  status["samplingInterval"] = samplingInterval;
  status["statusReportInterval"] = statusReportInterval;
  status["raw"] = sensorValue;
  status["position"] = positionPercent;
  status["angle"] = angle;

  if (checkCode != nullptr && checkCode[0] != '\0') {
    doc["check_code"] = checkCode;
  }

  mqttClient.publish(MQTT_TOPIC_STATUS.c_str(), jsonString.c_str());
}
```

### 5.3 设备：SG_90

**通用结构：**

```json
{
  "device_id": "sg90_001",
  "event": "angle_updated" | "check_current_angle" | "heartbeat" | "online" | "status_interval_updated",
  "status": {"angle": 90, "statusReportInterval": 120},
  "timestamp": 1770731525,
  "check_code": "123456"
}
```

**在程序中的对应实现：**

```cpp
void sendStatusUpdate(const char* event, const char* checkCode) {
  doc["device_id"] = DEVICE_ID;
  doc["event"] = event;
  doc["timestamp"] = timeClient.getEpochTime();

  JsonObject status = doc.createNestedObject("status");
  status["angle"] = currentAngle;
  status["statusReportInterval"] = statusReportInterval;

  if (checkCode != nullptr && checkCode[0] != '\0') {
    doc["check_code"] = checkCode;
  }

  mqttClient.publish(MQTT_TOPIC_STATUS.c_str(), jsonString.c_str());
}
```

**核心作用：**

- 约定 `sensor_id`/`device_id`、`event`、`status`、`timestamp`、`check_code`
- 后端 `sensor_upload_status_handlers` / `device_upload_status_handlers` 据此解析并写入 `SensorStatusCollection` / `DeviceData`
- `check_code` 用于 `verify_xxx_check_code`，支持 `send_custom_command_with_make_sure` 的确认流程

---

## 六、三份 form 文件与程序的关系总结

| 文件 | 方向 | 程序中对应位置 | 后端处理 |
|-----|------|----------------|----------|
| **mqtt_command_form.txt** | 后端 → 嵌入式 | `mqttCallback` 解析 `command`、`check_code`、参数 | `SensorType.commands` / `DeviceType.commands` 构造 mqtt_message |
| **mqtt_data_form.txt** | 嵌入式 → 后端 | `sendSensorData()` 构建 JSON 并 publish | `sensor_upload_data_handlers` → SensorData |
| **mqtt_status_form.txt** | 嵌入式 → 后端 | `sendStatusUpdate()` 构建 JSON 并 publish | `sensor_upload_status_handlers` / `device_upload_status_handlers` → SensorStatusCollection / DeviceData |

---

## 七、主题与数据流

```
传感器：
  iot/sensors/{sensor_id}/data    ← 发布（mqtt_data_form）
  iot/sensors/{sensor_id}/control ← 订阅（mqtt_command_form 解析）
  iot/sensors/{sensor_id}/status  ← 发布（mqtt_status_form）

设备：
  iot/devices/{device_id}/control ← 订阅（mqtt_command_form 解析）
  iot/devices/{device_id}/status  ← 发布（mqtt_status_form）
```

---

## 八、心跳与 check_code 约定

### 8.1 心跳

- 定期以 `event: "heartbeat"` 上报状态
- 用于后端判断在线（如 `Sensor.last_seen`、`Device.last_seen`）
- 心跳报文通常**不含** `check_code`

### 8.2 check_code

- 后端下发命令时可选注入 6 位 `check_code`
- 嵌入式执行命令后，在状态上报中**原样回传** `check_code`
- 后端据此确认命令已执行，配合 `send_custom_command_with_make_sure` 使用
