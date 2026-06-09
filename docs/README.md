# 物联网控制平台 - 文档中心

本目录为项目文档库，按设计文档、使用指南、部署、硬件等分类组织。

---

## 入口文档

| 文档 | 说明 |
|------|------|
| [项目概述 (PROJECT_DOCUMENTATION.md)](./PROJECT_DOCUMENTATION.md) | 项目简介、快速开始、系统架构、通信协议、数据库设计、文档索引 |

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
| [硬件程序设计](hardware_code/hardware_code_design.md) | MQTT 连接流程、mqtt_command_form、mqtt_data_form、mqtt_status_form |
| [嵌入式编写指南](hardware_code/hardware_guide.md) | 符合后端规范的固件编写步骤与 checklist |

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

## 更新日志

| 版本 | 说明 |
|------|------|
| [0.5 更新日志](update_notes/0.5_update_notes.md) | 插件系统（plugins 目录 + Plugin 登记 + sync 命令）、内置 data_viz 数据可视化插件 |
| [0.4 更新日志](update_notes/0.4_update_notes.md) | BaseCommandSendService 基类重构、MQTT 自动重连、生产安全配置、健康检查端点 |
| [0.3 更新日志](update_notes/0.3_update_notes.md) | 后台调度器、自动化规则轮询执行 |
| [0.2 更新日志](update_notes/0.2_update_notes.md) | MQTT 服务架构、自动重连等 |

---

## 设计文档（其他）

| 文档 | 说明 |
|------|------|
| [日志管理方案](design/logging.md) | 日志架构、分级、实施步骤 |

---

## 归档

| 目录 | 说明 |
|------|------|
| [archive/coding_progress_files](archive/coding_progress_files/) | 开发过程记录、AI 编码日志、历史设计文档 |

---

## 目录结构

```
docs/
├── README.md                    # 本文件：文档索引
├── PROJECT_DOCUMENTATION.md     # 项目主文档
├── deployment/                  # 部署
│   ├── before_deploy.md
│   ├── docker.md
│   └── not_docker.md
├── backend/                     # 后端
│   ├── backend_design/
│   └── backend_user_guide/
├── hardware_code/               # 嵌入式
│   ├── hardware_code_design.md
│   └── hardware_guide.md
├── frontend/                    # 前端设计
│   ├── frontend_design.md
│   └── frontend_optimization.md
├── simulation/                  # 仿真（虚拟传感器/设备）
│   ├── simulation_guide.md
│   └── testing_guide.md
├── design/                      # 设计
│   └── logging.md
└── archive/                     # 归档
    └── coding_progress_files/
```
