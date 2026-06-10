# 物联网控制平台 - 文档中心

本目录为项目文档库，按设计文档、使用指南、部署、硬件等分类组织。

---

## 入口文档

| 文档 | 说明 |
|------|------|
| [项目概述](./PROJECT_DOCUMENTATION.md) | 项目简介、快速开始、系统架构、通信协议、数据库设计、文档索引 |

---

## 部署

| 文档 | 说明 |
|------|------|
| [部署前准备](deployment/before_deploy.md) | EMQX 安装、Python/Node 环境、MySQL 可选、检查清单 |
| [Docker 部署](deployment/docker.md) | 使用 Docker Compose 容器化部署 |
| [非 Docker 部署](deployment/not_docker.md) | 传统方式部署（开发/生产） |

---

## 后端设计

| 文档 | 说明 |
|------|------|
| [Django 模型设计](backend/backend_design/djange_models_design.md) | DeviceType、Device、DeviceData、SensorType、Sensor、AutomationRule |
| [MQTT 服务设计](backend/backend_design/mqtt_service_design.md) | mqtt_service、BaseCommandSendService 基类、send_service、handler 架构与自动重连 |
| [自动化规则设计](backend/backend_design/AutomationRules_design.md) | engine、head_files、脚本执行流程、安全沙箱 |
| [平台配置设计](backend/backend_design/platform_settings_design.md) | PlatformConfig、get_config、seed、安全配置、分批清理 |
| [插件系统设计](backend/backend_design/plugins_design.md) | plugins/ 目录约定、Plugin 登记表、发现/启用/挂载生命周期、data_viz 内置插件 |
| [日志系统设计](backend/backend_design/logsystem_design.md) | 按模块分离、轮转、Logger 配置 |

---

## 后端使用指南

| 文档 | 说明 |
|------|------|
| [Django 模型使用](backend/backend_user_guide/django_models_guide.md) | Shell 中 CRUD、关联查询、方法调用 |
| [MQTT 服务使用](backend/backend_user_guide/mqtt_service_guide.md) | 命令发送、手动初始化、自动重连、主题速览 |
| [自动化规则脚本](backend/backend_user_guide/AutomationRules_guide.md) | 编写符合规范的自动化脚本 |
| [平台配置使用](backend/backend_user_guide/platform_settings_guide.md) | 配置 CRUD、健康检查、数据清理、节流 |
| [插件开发指南](backend/backend_user_guide/plugins_guide.md) | 5 分钟添加 hello 插件、目录骨架、与前端联调、常见坑位 |
| [日志系统使用](backend/backend_user_guide/logsystem_guide.md) | 查看日志、级别、常见问题 |

---

## 硬件与嵌入式

| 文档 | 说明 |
|------|------|
| [硬件程序设计](hardware/hardware_code_design.md) | MQTT 连接流程、mqtt_command_form、mqtt_data_form、mqtt_status_form |
| [嵌入式编写指南](hardware/hardware_guide.md) | 符合后端规范的固件编写步骤与 checklist |

---

## 前端设计

| 文档 | 说明 |
|------|------|
| [前端设计说明](frontend/frontend_design.md) | 技术栈、布局、页面设计、组件、API、实现差异 |
| [前端优化记录](frontend/frontend_optimization.md) | 响应式适配、移动端交互、空状态、登录页面优化 |

---

## 仿真（虚拟传感器/设备）

| 文档 | 说明 |
|------|------|
| [仿真模块使用说明](simulation/simulation_guide.md) | 目录结构、环境、config.yaml + manifests 配置、run.py 启动、节点目录、波形、与后端对接、添加新节点 |
| [仿真端到端验证教程](simulation/testing_guide.md) | L1 日志 / L2 MQTT 抓包 / L3 Django 入库 + check_code / L4 批量启动 |

> 仿真代码位于仓库根目录 `simulation/`（与 Django 后端解耦）；`simulation/README.md` 仅留快速上手，详细说明以本目录为准。

---

## 自动化规则

| 文档 | 说明 |
|------|------|
| [示例脚本](automation/examples/sample_file.txt) | 类风格与函数风格完整示例、API 速查 |
| [湿度告警示例](automation/examples/humidity_alert.py) | 湿度超阈值 → 设备命令（含 send_command 用法） |
| [湿度打印示例](automation/examples/humidity_overflow_print.py) | 湿度超阈值 → 终端输出（无设备依赖，适合新手） |
| [旋转传感器控制示例](automation/examples/rotation_sensor_control_sg90.py) | 传感器值直接映射到设备命令参数 |

---

## 插件

| 文档 | 说明 |
|------|------|
| [P&ID 画板添加图标指南](plugins/plant_diagram/HOW_TO_ADD_ICONS.md) | 扩展工艺符号库（静态符号/独立组件两条路径）、三文件修改流程、常见坑位 |

---

## 功能方案文档

| 文档 | 说明 |
|------|------|
| [EB 装置 IoT 监测方案](development_plans/EB装置IoT辅助监测预警系统方案.md) | EB 乙苯装置大屏的业务背景与功能设计 |
| [P&ID 画板编辑器方案](development_plans/工厂PID画板编辑器方案.md) | plant_diagram 插件的设计方案与技术选型 |
| [苯乙烯装置实验方案](development_plans/苯乙烯装置监测系统实验方案.md) | 实验室环境下的监测部署方案 |

---

## 更新日志

| 版本 | 说明 |
|------|------|
| [0.9 更新日志](update_notes/0.9_update_notes.md) | 自动化规则系统升级（引擎、SensorWrapper 扩展、CodeMirror 编辑器、设备选择器）；示例文件迁入 docs |
| [0.8 更新日志](update_notes/0.8_update_notes.md) | 全平台实时化（Django Channels + Redis + WebSocket）；MQTT 客户端拆分独立进程；useWebSocket composable |
| [0.7 更新日志](update_notes/0.7_update_notes.md) | 配置系统统一（configure 命令）；首次部署引导；系统设置页重写；Token 主动续期 |
| [0.6 更新日志](update_notes/0.6_update_notes.md) | 在线状态显示修复；Admin 一致性整治；卡片拖拽排序 |
| [0.5 更新日志](update_notes/0.5_update_notes.md) | 插件系统（plugins 目录 + Plugin 登记 + sync 命令）；内置 data_viz 数据可视化插件 |
| [0.4 更新日志](update_notes/0.4_update_notes.md) | BaseCommandSendService 基类重构；MQTT 自动重连；生产安全配置；健康检查端点 |
| [0.3 更新日志](update_notes/0.3_update_notes.md) | 后台调度器；自动化规则轮询执行 |
| [0.2 更新日志](update_notes/0.2_update_notes.md) | MQTT 服务架构；自动重连 |

---

## 目录结构

```
docs/
├── README.md                        # 本文件：文档索引
├── PROJECT_DOCUMENTATION.md         # 项目主文档
├── EB装置大屏使用手册.md              # EB 大屏操作手册
├── deployment/                      # 部署
│   ├── before_deploy.md
│   ├── docker.md
│   └── not_docker.md
├── backend/                         # 后端
│   ├── backend_design/              # 设计文档
│   └── backend_user_guide/          # 使用指南
├── hardware/                        # 硬件与嵌入式
│   ├── hardware_code_design.md
│   └── hardware_guide.md
├── frontend/                        # 前端设计
│   ├── frontend_design.md
│   └── frontend_optimization.md
├── simulation/                      # 仿真（虚拟传感器/设备）
│   ├── simulation_guide.md
│   └── testing_guide.md
├── automation/                      # 自动化规则
│   └── examples/                    # 示例脚本
│       ├── sample_file.txt
│       ├── humidity_alert.py
│       ├── humidity_overflow_print.py
│       └── rotation_sensor_control_sg90.py
├── plugins/                         # 插件文档
│   └── plant_diagram/
│       └── HOW_TO_ADD_ICONS.md
├── development_plans/               # 功能方案文档
│   ├── EB装置IoT辅助监测预警系统方案.md
│   ├── 工厂PID画板编辑器方案.md
│   └── 苯乙烯装置监测系统实验方案.md
└── update_notes/                    # 版本更新日志
    ├── 0.9_update_notes.md
    ├── 0.8_update_notes.md
    ├── 0.7_update_notes.md
    ├── 0.6_update_notes.md
    ├── 0.5_update_notes.md
    ├── 0.4_update_notes.md
    ├── 0.3_update_notes.md
    └── 0.2_update_notes.md
```
