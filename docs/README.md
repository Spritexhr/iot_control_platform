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
| [MQTT 服务设计](backend/backend_design/mqtt_service_design.md) | mqtt_service、send_service、handler 架构与自启动 |
| [自动化规则设计](backend/backend_design/AutomationRules_design.md) | engine、head_files、脚本执行流程 |
| [日志系统设计](backend/backend_design/logsystem_design.md) | 按模块分离、轮转、Logger 配置 |

---

## 后端使用指南

| 文档 | 说明 |
|------|------|
| [Django 模型使用](backend/backend_user_guide/django_models_guide.md) | Shell 中 CRUD、关联查询、方法调用 |
| [MQTT 服务使用](backend/backend_user_guide/mqtt_service_guide.md) | 命令发送、手动初始化、主题速览 |
| [自动化规则脚本](backend/backend_user_guide/AutomationRules_guide.md) | 编写符合规范的自动化脚本 |
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
│   └── frontend_design.md
├── design/                      # 设计
│   └── logging.md
└── archive/                     # 归档
    └── coding_progress_files/
```
