# 物联网控制平台 (IoT Control Platform)

基于 Django 的物联网设备管理和自动化控制平台

## 项目概述

这是一个完整的物联网控制系统，用于管理和控制基于 Wemos D1（ESP8266）的物联网设备。系统支持输入器（传感器）数据采集和输出器（执行器）控制。

### 核心功能

1. **输入器管理**：接收温湿度传感器、光电开关、旋转编码器等设备上报的数据，存储到数据库
2. **输出器管理**：控制 LED 灯、舵机、继电器等设备，并接收设备状态反馈
3. **自动化脚本**：根据传感器数据自动触发设备控制（如温度过高时开启警报）
4. **实时通信**：通过 MQTT 协议与设备进行双向通信
5. **设备监控**：实时监控设备在线状态，自动检测离线设备
6. **RESTful API**：提供设备、传感器、自动化规则的完整 API，支持 JWT 认证

## 技术栈

- **后端框架**：Django 6.0
- **API 框架**：Django REST framework + JWT 认证 (Simple JWT)
- **数据库**：SQLite（开发）/ MySQL（生产）
- **消息队列**：MQTT（EMQX 或 Mosquitto）
- **MQTT 客户端**：paho-mqtt
- **跨域支持**：django-cors-headers
- **部署**：Gunicorn + Docker
- **前端**：Vue.js（位于 `../frontend` 目录）
- **硬件**：Wemos D1（ESP8266）

## 项目结构

```
iot_control_platform/
├── config/                 # Django 项目配置
│   ├── settings.py        # 主配置文件
│   ├── urls.py            # 路由配置
│   ├── api_views.py       # 仪表盘、MQTT 状态等 API
│   ├── auth_views.py      # 用户注册、修改密码等
│   └── wsgi.py            # WSGI 配置
├── devices/               # 设备管理应用（输出器）
│   ├── models.py          # DeviceType、Device、DeviceData
│   ├── views.py           # 设备控制接口
│   ├── serializers.py     # 序列化器
│   └── admin.py           # 管理后台
├── sensors/               # 传感器应用（输入器）
│   ├── models.py          # SensorType、Sensor、SensorData 等
│   ├── views.py           # 数据查询接口
│   └── admin.py           # 管理后台
├── automation/            # 自动化脚本应用
│   ├── models.py          # AutomationRule 规则模型
│   ├── views.py           # 脚本管理接口
│   ├── serializers.py     # 序列化器
│   ├── engine.py          # 自动化引擎
│   ├── script/            # 示例脚本（humidity_alert、rotation_sensor_control_sg90 等）
│   └── head_files/        # 脚本依赖的头文件（devices、sensors 等）
├── utils/                 # 工具类
│   └── mqtt_client.py     # MQTT 客户端封装
├── logs/                  # 日志目录
├── manage.py              # Django 管理脚本
├── requirements.txt       # Python 依赖
├── Dockerfile             # 容器镜像构建
├── .dockerignore
└── README.md              # 项目说明（本文件）
```

## 安装与配置

### 1. 环境要求

- Python 3.12+
- pip
- MySQL 8.0+（可选，开发时可使用 SQLite）
- EMQX 或 Mosquitto MQTT 服务器

### 2. 安装依赖

```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境（Windows）
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

**依赖包**：Django、paho-mqtt、django-cors-headers、django-extensions、djangorestframework、djangorestframework-simplejwt、mysqlclient、gunicorn

### 3. 数据库配置

#### 使用 SQLite（默认，开发环境）

已在 `config/settings.py` 中配置，无需额外操作。

#### 切换到 MySQL（生产环境）

1. 创建数据库：

```sql
CREATE DATABASE iot_platform CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. 修改 `config/settings.py`，根据环境变量或手动配置 MySQL 连接。

### 4. MQTT 服务器配置

在 `config/settings.py` 中配置 MQTT 连接信息：

```python
MQTT_BROKER = "localhost"  # EMQX 服务器地址
MQTT_PORT = 1883
MQTT_USERNAME = ""  # 如果需要认证
MQTT_PASSWORD = ""  # 如果需要认证
```

### 5. 初始化数据库

```bash
# 激活虚拟环境
.venv\Scripts\activate

# 创建数据库迁移
python manage.py makemigrations

# 执行迁移
python manage.py migrate

# 创建超级管理员
python manage.py createsuperuser
```

### 6. 运行开发服务器

```bash
python manage.py runserver
```

服务器将在 http://localhost:8000 启动

## Docker 部署

项目支持使用 Docker Compose 进行容器化一键部署。

### 环境要求

- Docker & Docker Compose
- MQTT Broker（EMQX 或 Mosquitto，需单独部署或使用 Docker 启动）

### 部署步骤

1. 在项目根目录 `graduation_thesis/` 下，复制环境变量并修改：

```bash
cp .env.example .env
```

2. 启动容器：

```bash
docker compose up -d --build
```

3. 初始化数据库（首次部署）：

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
```

4. 访问系统：
   - 前端界面：`http://localhost:8080`（或 `.env` 中 `FRONTEND_PORT` 指定端口）
   - 管理后台：`http://localhost:8080/admin/`

详细说明请参阅 [docs/deployment/docker.md](../docs/deployment/docker.md)。

## API 说明

### 认证

- **登录**：`POST /api/auth/login/` 获取 JWT Token
- **刷新 Token**：`POST /api/auth/refresh/`
- **注册**：`POST /api/auth/register/`
- **个人资料**：`GET/PUT /api/auth/profile/`（需认证）
- **修改密码**：`POST /api/auth/change-password/`（需认证）

### 其他接口

- 传感器、设备、自动化规则：见 `sensors/`、`devices/`、`automation/` 的 `urls.py`
- MQTT 状态：`GET /api/mqtt/status/`
- 仪表盘统计：`GET /api/dashboard/stats/`

## MQTT 主题设计

### 传感器数据上报（输入器）

**主题格式**：`iot/sensors/{device_id}/data`

**消息示例**（与 `docs/PROJECT_DOCUMENTATION.md` 一致）：

```json
{
  "sensor_id": "DHT11-WEMOS-001",
  "data": {
    "temperature": 25.5,
    "humidity": 60.0
  },
  "timestamp": 1770733931
}
```

### 设备控制（输出器）

**主题格式**：`iot/devices/{device_id}/control`

**消息示例**：

```json
{
  "command": "set_brightness",
  "parameters": {
    "val": 100
  }
}
```

### 设备状态反馈

**主题格式**：`iot/devices/{device_id}/status`

**消息示例**：

```json
{
  "device_id": "LED-01",
  "status": {
    "power_state": true,
    "brightness": 80
  },
  "timestamp": 1770733935
}
```

## 系统架构说明

### 输入器（传感器）工作流程

1. Wemos D1 连接传感器（如 DHT11 温湿度传感器）
2. 定期读取传感器数据
3. 通过 MQTT 发布到 `iot/sensors/{device_id}/data` 主题
4. Django 后端订阅该主题，接收数据
5. 数据存入数据库
6. 前端可通过 API 查询历史数据

### 输出器（执行器）工作流程

1. 用户通过前端发送控制命令
2. Django 后端通过 MQTT 发布到 `iot/devices/{device_id}/control` 主题
3. Wemos D1 订阅该主题，接收控制命令
4. 执行命令（如开关 LED、转动舵机）
5. 通过 MQTT 反馈执行结果到 `iot/devices/{device_id}/status` 主题
6. Django 后端接收反馈，更新设备状态

### 自动化脚本

自动化脚本实现输入器和输出器之间的联动。脚本通过 `automation/engine.py` 引擎运行，可访问关联的传感器和设备数据，并通过 MQTT 发送控制指令。

示例脚本位于 `automation/script/` 目录。

## 开发指南

### 创建新的设备类型

1. 在 `devices/models.py` 中定义 DeviceType 及命令
2. 在 `devices/views.py` 中创建控制接口
3. 在 Arduino 代码中订阅对应的 MQTT 主题

### 创建新的传感器类型

1. 在 `sensors/models.py` 中定义 SensorType 及数据字段
2. 在 `sensors/views.py` 中创建数据查询接口
3. 在 Arduino 代码中发布数据到对应 MQTT 主题

### 编写自动化脚本

1. 在 `automation/models.py` 中创建 AutomationRule
2. 编写 Python 脚本（参考 [AutomationRules 指南](../docs/backend/backend_user_guide/AutomationRules_guide.md)）
3. 脚本通过 `from engine import sensors, devices` 访问数据，通过 `devices.get(id).send_command()` 发送指令

## 相关文档

| 文档 | 说明 |
|-----|------|
| [项目概述](../docs/PROJECT_DOCUMENTATION.md) | 系统设计、通信协议、数据库建模 |
| [Django 模型设计](../docs/backend/backend_design/djange_models_design.md) | 数据模型详细说明 |
| [Django 模型使用](../docs/backend/backend_user_guide/django_models_guide.md) | Shell 中 CRUD 与查询 |
| [MQTT 服务设计](../docs/backend/backend_design/mqtt_service_design.md) | mqtt_service、handler、send_service |
| [MQTT 服务使用](../docs/backend/backend_user_guide/mqtt_service_guide.md) | 命令发送、手动初始化 |
| [自动化规则设计](../docs/backend/backend_design/AutomationRules_design.md) | engine、脚本执行 |
| [部署前准备](../docs/deployment/before_deploy.md) | EMQX 安装、环境配置 |
| [Docker 部署](../docs/deployment/docker.md) | 容器化部署 |
| [非 Docker 部署](../docs/deployment/not_docker.md) | 传统部署 |

## 参考资料

- Django 文档：https://docs.djangoproject.com/
- MQTT 协议：https://mqtt.org/
- EMQX 文档：https://www.emqx.io/docs/
- Wemos D1 文档：参见 `../learning_esp8266_WEMOS_D1/`

## 许可证

本项目为毕业设计项目
