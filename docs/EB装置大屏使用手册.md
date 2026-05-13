# 乙苯(EB)装置辅助监测大屏 — 使用手册

> 适用版本:`beta_version` 分支(2026-05-13 起)
> 对应方案文档:[development_plans/EB装置IoT辅助监测预警系统方案.md](./development_plans/EB装置IoT辅助监测预警系统方案.md)
> 路由入口:`/plant/eb`

---

## 一、大屏能做什么

这是一个独立于 DCS 主控的**化工辅助监测演示大屏**,基于自研 IoT 平台,用于化工设计竞赛的差异化亮点。
当前(W3 第一周 MVP)能力:

- **5 个核心点位实时显示**:R1 反应温度/压力、R1 蒸汽包液位、R2 反应温度、DEB 循环流量
- **工程蓝白图风格**:仿 ISA 仪表符号,与 P&ID 工程图纸视觉一致
- **阈值越限自动着色**:正常(灰)/ 警告(黄)/ 报警(红 + 闪烁)
- **SSE 长连接**:1Hz 数据推送,无需轮询,延迟 <1s
- **三种扰动场景一键注入**:演示乙烯过量、冷却失效、DEB 雪球效应
- **MQTT 全链路**:模拟器 → 公网 broker → Django → SSE → 浏览器

后续 W3 第二周开始叠加 P&ID 动态图(罐体/塔器/管线动画),W4 加规则引擎和移动推送。

---

## 二、组件总览

```
┌──────────────────────────────┐
│ EBPlantSimulator(Python)    │  simulation/devices/eb_plant/
│  - 1Hz 发布 5 个点位         │
│  - 订阅扰动控制 topic        │
└─────────────┬────────────────┘
              │ MQTT publish: iot/sensors/EB-*/data
              │ MQTT subscribe: plant/EB/disturbance/control
              ▼
┌──────────────────────────────┐
│ MQTT Broker(公网)           │  116.62.68.29:1883
└─────────────┬────────────────┘
              │
              ▼
┌──────────────────────────────┐
│ Django + mqtt_service        │  iot_control_platform/services/
│  → sensor_upload_data_handler│
│  → ingest_sensor_data()      │
│    - 写 SensorData(DB)       │
│    - 更新 latest_values 缓存 │
│    - 广播到 SSE 订阅队列     │
└─────────────┬────────────────┘
              │
              ▼
┌──────────────────────────────┐
│ SSE endpoint                 │  /api/realtime/plant/EB/stream
│  /api/realtime/plant/EB/snapshot│
│  /api/realtime/plant/EB/disturbance(POST)│
└─────────────┬────────────────┘
              │ EventSource (text/event-stream)
              ▼
┌──────────────────────────────┐
│ Vue3 前端                    │  frontend/src/views/plant/EBPlantView.vue
│  - useSSE composable         │
│  - usePlantStore (Pinia)     │
│  - InstrumentCard ×5         │
└──────────────────────────────┘
```

---

## 三、前置条件

| 依赖 | 用途 | 默认值 |
|------|------|--------|
| Python 3.12 + paho-mqtt | 运行模拟器 | 通过 `iot_platform_env` conda 环境 |
| MQTT Broker | 消息中转 | **公网 116.62.68.29:1883**(已部署) |
| Django 后端 | API + SSE | 默认 8000 端口 |
| Vue3 前端 | 大屏页面 | 默认 5173 端口 |
| 平台配置 `mqtt_broker` | 后端连 broker | 系统设置 → 通信 → MQTT |

> ⚠️ **必须确认**:Django 端 `mqtt_broker` 配置为 `116.62.68.29`,否则后端订阅不到模拟器发的数据,大屏会持续空白。
> 在前端【系统设置 → MQTT】查看/修改,或用 `python manage.py configure --set mqtt_broker=116.62.68.29`。

---

## 四、首次启动步骤

### 1. 种子 EB 装置传感器到数据库

```bash
cd iot_control_platform
python manage.py seed_eb_plant            # 5 个 MVP 点位
# 或:
python manage.py seed_eb_plant --full     # 全部 ~20 个点位(供后续扩展)
```

输出末尾应看到 `当前 EB 装置传感器共 5 个。` 即成功。命令是**幂等的**,重复执行只会更新元数据,不会重复创建。

### 2. 启动后端

```bash
cd iot_control_platform
python manage.py runserver
```

后端启动后会自动连公网 MQTT broker 并订阅 `iot/sensors/+/data`。

### 3. 启动模拟器

```bash
cd simulation
python devices/eb_plant/eb_plant_simulator.py --broker 116.62.68.29 --port 1883
```

正常输出:
```
... INFO EB 装置模拟器启动,1Hz 发布 5 个点位 → broker=116.62.68.29:1883
... INFO MQTT 已连接 broker=116.62.68.29:1883
```

启动后每秒会向 5 个 topic 发数据。

### 4. 启动前端

```bash
cd frontend
npm run dev
```

### 5. 访问大屏

浏览器打开 <http://localhost:5173/plant/eb>(或登录后从左侧菜单【乙苯装置大屏】进入)。

**正常画面**:5 张仪表卡片,数值每秒跳动一次,顶栏【SSE】显示绿色"已连接",【更新】显示"刚刚"。

---

## 五、演示扰动场景

页面顶部"演示场景"控制台有四个按钮,点击即下发到模拟器。

| 按钮 | scenario 值 | 现象 |
|------|------------|------|
| **正常工况** | `none` | 所有点位回归稳态(±5% 噪声) |
| **乙烯进料过量** | `ethylene_overfeed` | 30 秒内 TT-101/TT-201 上升 ~10K,蒸汽包液位 LT-102 下降至 25%,触发蒸汽包【高报】 |
| **R1 冷却失效** | `cooling_failure` | 45 秒内 TT-101 上升 ~15K(→449 K),PT-101 上升 ~3 atm,温度/压力先后【高报】 |
| **DEB 雪球效应** | `deb_snowball` | FT-401 缓慢爬升(指数增长,~60 秒达到 ~600 kmol/h),演示传统阈值报警的滞后性 |

**演示推荐顺序**(给评委看):
1. 先点【正常工况】等 10 秒,所有卡片灰色
2. 点【DEB 雪球效应】,讲解雪球效应原理,等 FT-401 卡片渐变橙→红
3. 点【正常工况】恢复
4. 点【乙烯进料过量】,演示蒸汽包危险这种**严重等级**的报警闪烁
5. 点【正常工况】结束

每次切换场景模拟器会清零所有偏移再叠加新扰动,不会出现叠加错乱。

---

## 六、关键 API

| 方法 | 路径 | 用途 |
|------|------|------|
| GET | `/api/realtime/plant/EB/snapshot` | 当前所有点位的 JSON 快照(前端初始化用) |
| GET | `/api/realtime/plant/EB/stream` | SSE 长连接,持续推送 `snapshot` / `sample` 事件 |
| POST | `/api/realtime/plant/EB/disturbance` | 注入扰动,body: `{"scenario": "deb_snowball"}` |

SSE 事件格式:
```
event: sample
data: {"sensor_id":"EB-TT-101","tag":"TT-101","value":434.2,"unit":"K","status":"normal","ts":1731000000,"metadata":{"hi_threshold":440,...}}
```

> ⚠️ SSE 端点目前为了让浏览器 `EventSource` 直接连得通,**权限为 AllowAny**(无需 JWT)。
> 仅用于内网/演示。生产环境如要鉴权,可改用 fetch + ReadableStream 自解析 SSE,并在 URL 上挂 token 参数。

---

## 七、故障排查

| 现象 | 排查 |
|------|------|
| 大屏一直显示"暂无数据" | ①Django 后端是否启动;②`mqtt_broker` 配置是否指向公网 IP;③模拟器是否在跑;④浏览器 DevTools → Network → stream 是否 200 且有 event-stream 数据 |
| SSE 显示"已连接"但数值不更新 | 多半是 broker 没收到模拟器消息。在另一台机器用 MQTT Explorer 订阅 `iot/sensors/EB-+/data` 验证 |
| 报警卡片不闪烁 | CSS 动画问题,检查浏览器是否禁用了 `prefers-reduced-motion` |
| 顶栏【SSE】显示"异常"并反复重连 | 后端被重启或代理缓冲;开发期用 `runserver` 不会出问题。生产部署见后端章节 |
| 点扰动按钮无效 | 看 Django 日志是否有 `已下发扰动场景: ...`;若 MQTT 未连接会返回 503 |
| 模拟器报 `Connection refused` | broker IP/port 不对,或公网防火墙拦了。本机 ping 验证 |
| 后端日志里没有 EB 数据上报 | 传感器没 seed,或 sensor_id 大小写不一致。运行 `seed_eb_plant` 重置 |

### 调试小贴士

- **看后端缓存里现有点位**:`curl http://localhost:8000/api/realtime/plant/EB/snapshot`
- **手动注入扰动**:`curl -X POST http://localhost:8000/api/realtime/plant/EB/disturbance -H "Content-Type: application/json" -d '{"scenario":"deb_snowball"}'`
- **不开前端测 SSE**:`curl -N http://localhost:8000/api/realtime/plant/EB/stream`(终端里能看到 event-stream 流)
- **单独跑模拟器某个场景**:`python eb_plant_simulator.py --broker 116.62.68.29 --scenario deb_snowball`

---

## 八、数据模型速查

EB 装置传感器存在标准 `Sensor` 表中,通过两个字段区分:

- `plant_code = "EB"` — 标识所属装置
- `plant_metadata` — JSON,包含工艺扩展信息

`plant_metadata` 示例(以 EB-TT-101 为例):
```json
{
  "tag": "TT-101",
  "area": "R1",
  "data_key": "temperature",
  "unit": "K",
  "normal_value": 434,
  "hi_threshold": 440,
  "lo_threshold": 425,
  "severity": "high"
}
```

`severity` 取值:`low` / `mid` / `high` / `critical`,决定阈值越限时是【警告】(黄)还是【报警】(红)。

新增点位:在 `sensors/management/commands/seed_eb_plant.py` 的 `FULL_EXTRA_POINTS` 里加一条,再跑 `seed_eb_plant --full`;然后在 `simulation/devices/eb_plant/eb_plant_simulator.py` 的 `POINTS` 字典里加对应的稳态值和噪声参数。

---

## 九、生产部署注意

当前实现假设单进程 Django,因为 `latest_values` 和 `Broadcaster` 是**进程内**状态:
- 多 worker / 多机部署时,各 worker 的缓存彼此独立,SSE 客户端可能连到没数据的 worker
- 解法:换 Redis pub/sub + Redis 共享 hash,改造 `services/realtime/latest_values.py`

SSE 连接每个占一个 WSGI worker 线程:
- `runserver` 不限制,开发无忧
- 生产建议切 ASGI:`uvicorn config.asgi:application --workers 4`
- 或 gunicorn 用线程模式:`gunicorn config.wsgi:application --worker-class gthread --threads 16`

---

## 十、后续 Roadmap(节选)

参见 [development_plans/EB装置IoT辅助监测预警系统方案.md](./development_plans/EB装置IoT辅助监测预警系统方案.md)。

- **W3 第二周**:P&ID 骨架(罐体/塔器/管线组件 + SVG 布局)
- **W4**:动态 P&ID(液位/流速/温度动画 + 报警闪烁定位到工艺位置)
- **W5**:规则引擎(阈值/趋势/关联报警)
- **W6**:可视化规则配置中心(组态化报警)
- **W7**:移动推送(企业微信/Server酱)
- **W8**:演示视频 + 答辩材料
