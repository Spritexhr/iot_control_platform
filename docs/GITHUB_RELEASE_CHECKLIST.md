# GitHub 发布前检查清单

发布到 GitHub 前的准备工作与注意事项。

---

## 一、已完成的修改 ✓

本次发布准备已自动完成以下修改：

### 1. 敏感信息移除

| 位置 | 修改内容 |
|-----|---------|
| `iot_control_platform/config/settings.py` | MQTT 默认值改为 `127.0.0.1` 和空字符串，移除真实 IP 与密码 |
| `iot_control_platform/config/settings.py` | 移除 CORS 中的局域网 IP（192.168.12.33） |
| `.env.example` | 移除真实 MQTT IP 与密码示例 |
| 硬件 `.ino` 文件 | WiFi、MQTT 配置改为 `YOUR_WIFI_SSID`、`YOUR_MQTT_BROKER_IP` 等占位符 |
| 部署文档 | `not_docker.md`、`docker.md` 等中的示例 IP 改为占位符 |

### 2. .gitignore 已配置

- `.venv/`、`node_modules/`
- `.env`、`.env.local`、`.env.*.local`
- `iot_control_platform/logs/`
- `*.log`、`*.tmp`、`*.temp`
- `.vscode/`、`.idea/`、`.DS_Store` 等

---

## 二、发布前请手动确认

### 1. 确认无敏感文件被跟踪

若项目此前已有 Git 提交，请检查是否存在已被提交的敏感文件：

```bash
# 查看是否跟踪了 .env、logs 等
git ls-files | grep -E "\.env$|logs/|\.venv"

# 若有输出，需要从 Git 中移除（保留本地文件）：
# git rm --cached .env
# git rm -r --cached iot_control_platform/logs/
# git rm -r --cached iot_control_platform/.venv/
```

### 2. 确认 .env 未被提交

```bash
git status
# 确保 .env 显示为 untracked 或 ignored
```

### 3. 首次推送前建议

- 在 GitHub 创建**空仓库**（不勾选 README、.gitignore、LICENSE）
- 本地执行：
  ```bash
  git init
  git add .
  git commit -m "Initial commit: IoT Control Platform"
  git remote add origin https://github.com/你的用户名/仓库名.git
  git branch -M main
  git push -u origin main
  ```

---

## 三、可选优化

### 1. 添加 LICENSE

在项目根目录添加 `LICENSE` 文件，例如 MIT、Apache 2.0 等。

### 2. 完善 README

- 已包含项目结构、技术栈、快速开始说明
- 可根据需要补充：截图、演示链接、贡献指南等

### 3. 生产环境配置

发布后，部署时务必在 `.env` 中设置：

- `SECRET_KEY`：随机强密钥
- `DB_PASSWORD`：数据库密码
- `MQTT_BROKER`：EMQX 地址
- `MQTT_PASSWORD`：若 EMQX 开启认证

---

## 四、使用方说明

克隆或下载后，使用者需：

1. 复制 `.env.example` 为 `.env`，并填写实际配置
2. 硬件固件烧录前，在各 `.ino` 中修改 `YOUR_WIFI_SSID`、`YOUR_WIFI_PASSWORD`、`YOUR_MQTT_BROKER_IP`

---

*文档生成日期：2026-02-21*
