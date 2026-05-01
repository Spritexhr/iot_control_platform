# 插件系统

`plugins/` 目录用于承载实验性的新功能（数据可视化、ML 推理、报表等），每个插件就是一个独立的 Django app。

## 插件目录结构

```
plugins/
└── <plugin_name>/
    ├── plugin.json          # 必需：插件清单
    ├── apps.py              # 必需：Django AppConfig，name 必须为 "plugins.<plugin_name>"
    ├── urls.py              # 可选：API 路由，会被自动 include 到 /api/plugins/<plugin_name>/
    ├── views.py
    ├── models.py            # 可选：插件可定义自己的模型，用 makemigrations 生成迁移
    ├── serializers.py       # 可选
    ├── admin.py             # 可选
    └── migrations/
```

## plugin.json 字段

| 字段          | 类型    | 说明                                              |
|---------------|---------|---------------------------------------------------|
| `name`        | string  | 插件唯一标识，建议与目录名一致                    |
| `version`     | string  | 语义化版本，如 `"0.1.0"`                          |
| `description` | string  | 简短描述，会写入 `Plugin.description`             |
| `enabled`     | boolean | 默认启用状态，首次 `sync_plugins` 时写入 DB       |

## 生命周期

1. **发现**：`plugins.discover_plugins()` 文件系统扫描，仅看 `plugin.json`
2. **登记**：`python manage.py sync_plugins` 把清单同步到 `platform_settings.Plugin` 表
3. **启用**：`Plugin.enabled` 控制 `/api/plugins/<name>/` 是否注册
4. **生效**：启用/禁用需要重启 Django 进程（URL conf 在启动时绑定）

## 已知限制

- 不支持热插拔：toggle `enabled` 后必须重启进程
- 所有发现到的插件都会被加入 `INSTALLED_APPS`（保证 migration 可用），仅 URL 层面按 `enabled` 过滤
- 插件 app label 形如 `plugins.<name>`，`models.Meta.app_label` 与之一致
