# 部署前准备

本文档说明在部署物联网控制平台之前需要完成的准备工作，包括 MQTT Broker 安装、运行环境配置及部署前检查清单。

---

## 一、部署前准备概览

| 步骤 | 说明 | 是否必做 |
|-----|------|---------|
| 安装 EMQX | MQTT Broker，传感器与设备通信必需 | ✓ |
| 安装 Python | Django 后端运行环境 | ✓ |
| 安装 Node.js | 前端构建与开发 | ✓（前端开发/构建时） |
| 安装 MySQL | 可选，生产环境替代 SQLite | 可选 |
| 安装 Docker | 若采用 Docker 部署 | 可选 |
| 配置防火墙 | 开放必要端口 | 生产环境建议 |
| 准备环境变量 | .env 或系统环境变量 | ✓ |

---

## 二、安装 EMQX（MQTT Broker）

物联网平台依赖 MQTT Broker 实现传感器、设备与后端的双向通信，**部署前必须先安装并启动 EMQX**。

### 2.1 下载

- **官网**：[https://www.emqx.com/en/downloads](https://www.emqx.com/en/downloads)
- 选择 **EMQX Open Source**，按系统下载（Windows ZIP、Linux DEB/RPM 等）

### 2.2 Windows 安装

1. 下载 `emqx-x.x.x-windows-amd64.zip`
2. 解压到目录，如 `C:\emqx`
3. 命令行启动：
   ```powershell
   cd C:\emqx
   .\bin\emqx.cmd start
   ```
4. 停止：`.\bin\emqx.cmd stop`

### 2.3 Linux 安装

**方式 A：DEB 包（Ubuntu/Debian）**
```bash
wget https://www.emqx.com/en/downloads/broker/latest/emqx-ubuntu22.04-amd64.deb
sudo apt install ./emqx-ubuntu22.04-amd64.deb
sudo systemctl start emqx
```

**方式 B：ZIP 包**
```bash
wget https://www.emqx.com/en/downloads/broker/latest/emqx-ubuntu22.04-amd64.zip
unzip emqx-*.zip
cd emqx
./bin/emqx start
```

### 2.4 验证 EMQX 运行

- **MQTT 端口**：1883（默认）
- **Web 控制台**：http://localhost:18083
  - 默认账号：admin
  - 默认密码：public

登录控制台可查看客户端连接、主题订阅、消息收发等。

### 2.5 配置认证（可选）

生产环境建议启用 MQTT 认证：

1. 打开 EMQX 控制台 → **访问控制** → **认证**
2. 添加认证方式（如用户名/密码）
3. 在 Django 的 `MQTT_USERNAME`、`MQTT_PASSWORD` 中填写相同凭据

嵌入式固件中的 `MQTT_USERNAME`、`MQTT_PASSWORD` 也需保持一致。

---

## 三、安装 Python 与 Node.js

### 3.1 Python（3.10+）

**Windows：**
- 从 [python.org](https://www.python.org/downloads/) 下载安装
- 安装时勾选 **Add Python to PATH**
- 勾选 **Install pip**

**Linux：**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

**验证：**
```bash
python --version   # 或 python3 --version
pip --version
```

### 3.2 Node.js（18+，前端开发/构建时需要）

**Windows：**
- 从 [nodejs.org](https://nodejs.org/) 下载 LTS 版本安装

**Linux：**
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

**验证：**
```bash
node --version
npm --version
```

---

## 四、安装 MySQL（可选）

若需使用 MySQL 替代 SQLite（生产环境推荐）：

### 4.1 安装

**Windows：**
- 下载 [MySQL Installer](https://dev.mysql.com/downloads/installer/)
- 安装时设置 root 密码

**Linux：**
```bash
sudo apt install mysql-server
sudo mysql_secure_installation
```

### 4.2 创建数据库与用户

```sql
CREATE DATABASE iot_platform CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'iot_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON iot_platform.* TO 'iot_user'@'localhost';
FLUSH PRIVILEGES;
```

### 4.3 后端配置

部署时设置环境变量：
```
DB_USE_MYSQL=true
DB_NAME=iot_platform
DB_USER=iot_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=3306
```

---

## 五、安装 Docker（Docker 部署时）

若采用 [docker.md](docker.md) 部署：

- **Windows**：安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- **Linux**：按官方文档安装 Docker Engine 与 Docker Compose

验证：
```bash
docker --version
docker compose version
```

---

## 六、端口与防火墙

### 6.1 常用端口

| 服务 | 端口 | 说明 |
|-----|------|------|
| EMQX MQTT | 1883 | 传感器、设备、Django 连接 |
| EMQX 控制台 | 18083 | Web 管理界面 |
| Django 后端 | 8000 | runserver / Gunicorn |
| 前端开发 | 5173 | Vite dev server |
| 前端生产 | 80 / 8080 | Nginx 或静态服务 |
| MySQL | 3306 | 若使用 MySQL |

### 6.2 防火墙（生产环境）

**Windows 防火墙：**
- 控制面板 → Windows Defender 防火墙 → 高级设置 → 入站规则
- 新建规则，开放 1883、8000、80（或实际使用端口）

**Linux（ufw）：**
```bash
sudo ufw allow 1883/tcp   # MQTT
sudo ufw allow 8000/tcp  # Django
sudo ufw allow 80/tcp    # HTTP
sudo ufw enable
```

---

## 七、准备环境变量

### 7.1 复制示例文件

在项目根目录：
```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

### 7.2 必改项

| 变量 | 说明 | 示例 |
|-----|------|------|
| `DB_PASSWORD` | MySQL 密码（使用 MySQL 时） | 强密码 |
| `SECRET_KEY` | Django 密钥（生产必改） | 随机字符串 |
| `MQTT_BROKER` | MQTT 服务器地址 | `127.0.0.1`（本机）或远程 IP |
| `MQTT_USERNAME` / `MQTT_PASSWORD` | MQTT 认证（若 EMQX 启用） | 与 EMQX 一致 |

### 7.3 非 Docker 部署

环境变量可通过以下方式传递：

- 系统环境变量（`export` / `set`）
- 在 `iot_control_platform` 目录下创建 `.env`（若使用 python-dotenv 等）
- 启动时在命令行前缀：`SECRET_KEY=xxx python manage.py runserver`

---

## 八、部署前检查清单

在执行 [docker.md](docker.md) 或 [not_docker.md](not_docker.md) 部署前，请确认：

- [ ] EMQX 已安装并启动，1883 端口可访问
- [ ] Python 3.10+ 已安装
- [ ] （若需前端）Node.js 18+ 已安装
- [ ] （若用 MySQL）MySQL 已安装，数据库已创建
- [ ] （若用 Docker）Docker 与 Docker Compose 已安装
- [ ] `.env` 已从 `.env.example` 复制并修改关键配置
- [ ] 防火墙已开放必要端口（生产环境）
- [ ] 嵌入式设备与服务器在同一网络或可访问 MQTT Broker

---

## 九、快速验证 EMQX

部署完成后，可用以下方式验证 MQTT 是否正常：

**1. EMQX 控制台：**
- 打开 http://localhost:18083
- 查看 **客户端** 列表，Django 启动后应能看到 `django_iot_platform` 连接

**2. Django 日志：**
- 启动 `runserver` 或 Gunicorn 后，若 MQTT 连接成功，日志中会有 `✓ MQTT连接成功` 等提示

**3. mosquitto 客户端（可选）：**
```bash
# 订阅测试（需安装 mosquitto-clients）
mosquitto_sub -h 127.0.0.1 -t "iot/sensors/+/data" -v
```

---

## 十、相关文档

- [Docker 部署](docker.md)
- [非 Docker 部署](not_docker.md)
- [MQTT 服务设计](../backend_design/mqtt_service_design.md)
