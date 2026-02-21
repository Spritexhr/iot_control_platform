# 物联网控制平台 - 非 Docker 部署指南

本文档说明在**不使用 Docker** 的情况下如何部署物联网控制平台，适用于本地开发、测试或无法使用容器的部署环境。Docker 部署见 [docker.md](docker.md)。

---

## 一、部署架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户浏览器                                 │
│              http://localhost:5173 或 http://IP:80               │
└────────────────────────────────┬────────────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │ 开发模式              │ 生产模式                │
         ▼                       ▼                        │
┌─────────────────┐    ┌─────────────────────────────────┴──────┐
│ Vite 开发服务器  │    │ Nginx / 静态服务器                       │
│ (端口 5173)     │    │ - 提供前端静态文件                       │
│ 内置 /api 代理   │    │ - /api 反向代理到 Django                 │
└────────┬────────┘    └────────────────┬────────────────────────┘
         │                              │
         └──────────────┬───────────────┘
                        ▼
         ┌──────────────────────────────┐
         │  Django 后端                   │
         │  runserver / Gunicorn :8000   │
         └──────────────┬───────────────┘
                        │
         ┌──────────────┼──────────────┐
         ▼              ▼              ▼
   SQLite/MySQL    MQTT Broker     logs/
   (数据库)        (EMQX 等)       (日志)
```

---

## 二、环境准备

### 2.1 所需软件

| 软件 | 版本建议 | 用途 |
|-----|---------|------|
| Python | 3.10+ | Django 后端 |
| Node.js | 18+ | 前端构建（可选，仅构建时需要） |
| MQTT Broker | - | EMQX / Mosquitto，传感器与设备通信 |
| MySQL | 8.0（可选） | 生产环境可替代 SQLite |

### 2.2 安装 Python 与 Node.js

**Windows：**
- Python: [python.org](https://www.python.org/downloads/) 下载安装，勾选 "Add Python to PATH"
- Node.js: [nodejs.org](https://nodejs.org/) 下载 LTS 版本

**Linux（Ubuntu/Debian）：**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv nodejs npm
```

**验证：**
```bash
python --version   # 或 python3
pip --version
node --version
npm --version
```

---

## 三、后端部署（Django）

### 3.1 进入后端目录并创建虚拟环境

```bash
cd d:\learning\graduation_thesis
python -m venv .venv

# 激活虚拟环境
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Windows CMD:
.\.venv\Scripts\activate.bat
# Linux/Mac:
source .venv/bin/activate
```

### 3.2 安装依赖

```bash
cd iot_control_platform
pip install -r requirements.txt
```

### 3.3 配置环境变量（可选）

在项目根目录或 `iot_control_platform` 下创建 `.env`，或在运行前设置环境变量：

```bash
# Windows PowerShell 示例
$env:SECRET_KEY="your-secret-key"
$env:DEBUG="True"
$env:ALLOWED_HOSTS="localhost,127.0.0.1"
$env:MQTT_BROKER="your-mqtt-broker-ip"
$env:MQTT_PORT="1883"

# Linux/Mac 示例
export SECRET_KEY="your-secret-key"
export DEBUG=True
export ALLOWED_HOSTS="localhost,127.0.0.1"
export MQTT_BROKER="your-mqtt-broker-ip"
```

不设置时使用 `config/settings.py` 中的默认值（SQLite、默认 MQTT 配置）。

### 3.4 数据库迁移与创建管理员

```bash
cd iot_control_platform
python manage.py migrate
python manage.py createsuperuser
```

按提示输入用户名、邮箱和密码。

### 3.5 启动后端

**开发模式：**
```bash
python manage.py runserver 0.0.0.0:8000
```

**生产模式（Gunicorn）：**
```bash
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2
```

后端启动后，MQTT 服务会由 `sensors.apps` 自动初始化并连接 Broker。

---

## 四、前端部署

### 4.1 开发模式（推荐本地调试）

前端与后端分别启动，Vite 将 `/api` 代理到 Django：

```bash
# 终端 1：启动后端
cd iot_control_platform
python manage.py runserver 0.0.0.0:8000

# 终端 2：启动前端
cd frontend
npm install
npm run dev
```

访问：http://localhost:5173

### 4.2 生产模式（构建静态文件）

```bash
cd frontend
npm install
npm run build
```

构建产物在 `frontend/dist/` 目录。

#### 方式 A：使用 Vite 预览（简单测试）

```bash
npm run preview
```

默认 http://localhost:4173，需配置代理或修改前端 API 地址指向后端。

#### 方式 B：使用 Nginx 提供静态文件并代理 API

1. 安装 Nginx（如 `sudo apt install nginx`）
2. 将 `frontend/dist/` 内容放到 Nginx 根目录
3. 参考 `frontend/nginx.conf`，将 `proxy_pass http://backend:8000` 改为 `proxy_pass http://127.0.0.1:8000`
4. 重启 Nginx

#### 方式 C：使用 Python 静态文件服务器（临时）

```bash
cd frontend/dist
python -m http.server 8080
```

注意：此方式无法代理 `/api`，前端需直接请求后端地址（如 `http://127.0.0.1:8000/api`），需修改前端 `baseURL` 或通过 Nginx 等代理。

---

## 五、MQTT Broker

### 5.1 本机运行 EMQX

- 下载 [EMQX](https://www.emqx.io/downloads)
- 解压并运行 `bin/emqx start`
- 默认端口 1883，Web 控制台 18083

### 5.2 使用远程 MQTT

在环境变量或 `config/settings.py` 中配置：

```python
MQTT_BROKER = "your-mqtt-broker-ip"  # 实际 IP 或域名
MQTT_PORT = 1883
MQTT_USERNAME = ""   # 若需认证
MQTT_PASSWORD = ""
```

---

## 六、使用 MySQL（可选）

### 6.1 安装 MySQL 并创建数据库

```sql
CREATE DATABASE iot_platform CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'iot_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL ON iot_platform.* TO 'iot_user'@'localhost';
FLUSH PRIVILEGES;
```

### 6.2 配置环境变量

```bash
export DB_USE_MYSQL=true
export DB_NAME=iot_platform
export DB_USER=iot_user
export DB_PASSWORD=your_password
export DB_HOST=localhost
export DB_PORT=3306
```

### 6.3 安装 MySQL 客户端并迁移

```bash
# 若 requirements.txt 中已有 mysqlclient
pip install mysqlclient

python manage.py migrate
```

---

## 七、完整启动流程示例

### 7.1 开发环境（双终端）

**终端 1 - 后端：**
```bash
cd d:\learning\graduation_thesis
.\.venv\Scripts\Activate.ps1
cd iot_control_platform
python manage.py runserver 0.0.0.0:8000
```

**终端 2 - 前端：**
```bash
cd d:\learning\graduation_thesis\frontend
npm run dev
```

访问 http://localhost:5173，使用 `createsuperuser` 创建的账号登录。

### 7.2 生产环境（后台运行）

**后端（使用 nohup 或 tmux）：**
```bash
cd iot_control_platform
nohup gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 > gunicorn.log 2>&1 &
```

**Nginx：** 按上文配置，提供前端静态文件并代理 `/api` 到 `http://127.0.0.1:8000`。

---

## 八、目录与文件说明

| 路径 | 说明 |
|-----|------|
| `iot_control_platform/` | Django 项目根目录 |
| `iot_control_platform/config/settings.py` | 主配置，支持环境变量 |
| `iot_control_platform/db.sqlite3` | SQLite 数据库（默认） |
| `iot_control_platform/logs/` | 日志目录（自动创建） |
| `frontend/` | Vue 前端源码 |
| `frontend/dist/` | 构建产物（`npm run build` 后生成） |
| `.env` | 环境变量（可选，项目根目录或 iot_control_platform 下） |

---

## 九、常见问题

### Q1：前端访问后端 401 / CORS 错误

确认 `config/settings.py` 中 `CORS_ALLOWED_ORIGINS`、`CSRF_TRUSTED_ORIGINS` 包含前端实际访问地址（如 `http://localhost:5173`、`http://your-ip:8080`）。

### Q2：MQTT 连接失败

- 检查 `MQTT_BROKER`、`MQTT_PORT` 是否正确
- 确认防火墙允许 1883 端口
- 若 EMQX 在本机，`MQTT_BROKER` 可设为 `127.0.0.1` 或 `localhost`

### Q3：静态文件 404（生产环境）

确保 Nginx 的 `root` 指向 `frontend/dist`，且 `try_files $uri $uri/ /index.html` 已配置（支持 Vue Router history 模式）。

### Q4：数据库迁移失败

```bash
python manage.py makemigrations
python manage.py migrate
```

### Q5：端口被占用

- 后端：`runserver 0.0.0.0:8001` 或修改 Gunicorn `--bind`
- 前端开发：在 `frontend/vite.config.js` 中修改 `server.port`

---

## 十、与 Docker 部署对比

| 项目 | 非 Docker | Docker |
|-----|-----------|--------|
| 环境准备 | 需手动安装 Python、Node、MQTT 等 | 镜像内已包含 |
| 数据库 | 默认 SQLite 本地文件 | 可用数据卷或 MySQL 容器 |
| 启动方式 | 分别启动后端、前端、MQTT | `docker compose up -d` 一键启动 |
| 适用场景 | 开发、测试、无 Docker 环境 | 生产、多环境一致性 |

---

## 十一、快速命令速查

| 操作 | 命令 |
|-----|------|
| 创建虚拟环境 | `python -m venv .venv` |
| 激活虚拟环境 | `.\.venv\Scripts\Activate.ps1` (Windows) |
| 安装后端依赖 | `pip install -r requirements.txt` |
| 数据库迁移 | `python manage.py migrate` |
| 创建管理员 | `python manage.py createsuperuser` |
| 启动后端（开发） | `python manage.py runserver 0.0.0.0:8000` |
| 启动后端（生产） | `gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2` |
| 安装前端依赖 | `cd frontend && npm install` |
| 启动前端（开发） | `npm run dev` |
| 构建前端 | `npm run build` |
