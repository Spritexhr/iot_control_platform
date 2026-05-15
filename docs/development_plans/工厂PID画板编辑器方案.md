# 工厂 P&ID 画板编辑器 - 实施方案

> **目标场景**：把 EB 装置（及未来其他装置）的"网格仪表卡"升级为可编辑的 P&ID 工艺流程图
> **核心交互**：画布上拖放设备/传感器图标 → 拖动定位 → 端点连线 → 绑定 sensor_id/device_id → 实时显示数值
> **文档版本**：v0.1（2026-05-15）
> **预计工期**：3-4 周（MVP 2 周 + 打磨 1-2 周）
> **关联文档**：[EB装置IoT辅助监测预警系统方案.md](EB装置IoT辅助监测预警系统方案.md)

---

## 一、现状梳理

### 1.1 后端已有能力（不需要重写）

- `services/realtime/latest_values.py` —— 进程内点位缓存 + Broadcaster，**仍在使用，不是废弃功能**。MQTT 上报 → `ingest_sensor_data()` → 缓存 + 广播。
- `Sensor.plant_code` + `Sensor.plant_metadata` —— 装置归属和工艺元数据（位号、阈值、单位、`data_key` 等）。
- `plugins/eb_plant/views.py` —— 已经提供 SSE 流（`/stream`）、快照（`/snapshot`）、扰动下发（`/disturbance`）。
- 前端 [usePlantStore](../../frontend/src/stores/plant.js) + [useSSE](../../frontend/src/composables/useSSE.js) —— SSE 数据消费逻辑已闭环。

> **结论**：实时数据通道完整，本方案只需在它上面叠一层"空间布局 + 图编辑器"，**不动数据流**。

### 1.2 当前 UI 的缺口

[EBPlantView.vue:47-56](../../frontend/src/views/plugins/eb_plant/EBPlantView.vue#L47-L56) 把所有 `samples` 平铺在 CSS Grid 里：

```html
<main class="eb-plant__grid">
  <InstrumentCard v-for="s in store.samplesList" :key="s.sensor_id" :sample="s" />
</main>
```

问题：
1. 仪表之间没有工艺**拓扑关系**（看不出来 R1 反应器跟 T1 塔有没有联通）。
2. 位置由网格算法决定，**用户不能摆**。
3. 没有连线 / 没有阀门 / 没有管道符号，谈不上 P&ID。

### 1.3 用户期望

| 期望 | 翻译为功能点 |
| --- | --- |
| 画工厂 P&ID 图的效果 | 提供 ISA 风格图元库（仪表圈、阀门、反应器、塔、泵、换热器、管线、流向箭头） |
| 图标可在画板上移动 | 选中节点拖拽改坐标，画布支持平移/缩放 |
| 图标之间能连线 | 鼠标从节点端口拖到另一节点端口生成边，边可标识管线介质 |
| 图标绑定到具体设备/传感器 | 节点上有"绑定"动作，下拉选 sensor_id 或 device_id；运行时显示实时值与状态 |
| 跨装置可复用 | 不写死 EB，按 `plant_code` 加载和保存图，未来新装置直接复用编辑器 |

---

## 二、技术选型

### 2.1 画布引擎对比

| 选项 | 类型 | 优势 | 劣势 | 评分 |
| --- | --- | --- | --- | --- |
| **Vue Flow** (`@vue-flow/core`) | Vue3 原生节点图库 | API 与 React Flow 一致；TypeScript；自定义节点用 Vue 组件直接写；内置 minimap/controls/zoom | 偏"流程图"取向，工业 P&ID 的细节（管线打角、双折线、流向箭头）需要自实现 | ★★★★★ |
| **AntV X6** | 通用图编辑引擎 | 工业图能力最完整（ER/BPMN/UML 模板）；自带 Stencil 工具箱、对齐线、路由 | 学习曲线陡；和 Vue3 集成要 `@antv/x6-vue-shape`，渲染要额外封装；体积大 | ★★★★ |
| **JointJS** | 老牌 SVG 图库 | 图元元素丰富，社区电力 / 工业插件多 | 商业插件 (Rappid) 才有完整 P&ID；与 Vue3 生态融合差 | ★★ |
| **自研 SVG + useDraggable** | 完全自研 | 零依赖、完全可控 | 实现 zoom/pan/边路由/snap 要至少 1 个月，重复造轮子 | ★ |

**推荐 Vue Flow 作为 MVP 引擎**，理由：
- Vue3 原生组件，节点内容写 SFC，能直接复用 [InstrumentCard.vue](../../frontend/src/views/plugins/eb_plant/InstrumentCard.vue)。
- 文档清晰，license MIT，社区活跃。
- 工业图细节（连接点、流向箭头、管线样式）通过自定义 `<EdgeLabel>` 和 SVG marker 实现成本低。
- 如果 MVP 验证后觉得图编辑能力不够，再迁移到 X6（数据结构都是 nodes/edges，迁移成本可控）。

### 2.2 后端 / 存储

- 不引新依赖。在 `plugins/eb_plant/` 同级新增一个**通用** `plugins/plant_diagram/` 应用，提供 P&ID 图持久化 API。
- 存储用现有 SQLite/PostgreSQL，一个 `PlantDiagram` 表 + JSONField 装画布数据，**不为节点拆字段**——画布是 UI 状态，JSON 整存整取效率最高。

---

## 三、数据模型

### 3.1 后端模型（新增）

```python
# plugins/plant_diagram/models.py
class PlantDiagram(models.Model):
    """一张 P&ID 画板。一个装置可以有多张（主流程/公用工程/局部放大）。"""
    plant_code = models.CharField(max_length=50, db_index=True)     # 与 Sensor.plant_code 对应
    name = models.CharField(max_length=100)                          # 例如 "EB 主反应区"
    description = models.TextField(blank=True)
    canvas = models.JSONField(default=dict)                          # 见 §3.2
    is_default = models.BooleanField(default=False)                  # 同 plant_code 内仅一张 default
    sort_order = models.IntegerField(default=0)
    created_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

> 不在 Sensor/Device 上加 `position_x/position_y` 字段。位置是画板属性，同一传感器在不同画板上可能出现多次/不出现，把坐标耦合到设备模型上会污染。

### 3.2 `canvas` JSON 结构

```jsonc
{
  "version": 1,
  "viewport": { "x": 0, "y": 0, "zoom": 1 },
  "nodes": [
    {
      "id": "n_TT101",
      "type": "instrument",                  // 渲染器类型：instrument / valve / pump / vessel / column / heat_exchanger / label
      "position": { "x": 320, "y": 180 },
      "size": { "w": 120, "h": 80 },
      "binding": {
        "kind": "sensor",                    // sensor | device | none(纯图元)
        "id": "TT101"                        // 对应 Sensor.sensor_id 或 Device.device_id
      },
      "data": {                              // 渲染时的静态参数（图元自身配置，与绑定数据无关）
        "label": "R1 进料温度",
        "symbol": "TT",                      // ISA 仪表符号代号
        "show_value": true,
        "show_threshold": true
      }
    },
    {
      "id": "n_R1",
      "type": "vessel",
      "position": { "x": 480, "y": 240 },
      "size": { "w": 160, "h": 220 },
      "binding": { "kind": "none" },
      "data": { "label": "R1 反应器", "shape": "cstr" }
    }
  ],
  "edges": [
    {
      "id": "e_1",
      "source": "n_R1", "sourcePort": "right",
      "target": "n_T1", "targetPort": "left",
      "type": "process_line",                // process_line | utility_line | signal_line
      "data": { "medium": "EB+DEB", "arrow": true, "label": "塔底物料" }
    }
  ]
}
```

设计要点：
- **绑定是松耦合的**：`binding.id` 是字符串 ID，sensor/device 删除时不级联删节点，运行时找不到就显示"未绑定/已失效"。
- **图元类型用枚举驱动渲染器**，前端按 `type` 路由到对应的自定义节点组件；新增图元 = 新增一个渲染器 + 注册到工具箱。
- **viewport 也存**，下次打开还原镜头位置。
- **不存运行时数据**（实时值不入 canvas，运行时按 binding 从 store 取）。

### 3.3 后端 API（新增）

| Method | Path | 说明 |
| --- | --- | --- |
| GET | `/api/plugins/plant_diagram/?plant_code=EB` | 列出某装置的所有画板 |
| GET | `/api/plugins/plant_diagram/<id>/` | 取一张画板（含 canvas） |
| POST | `/api/plugins/plant_diagram/` | 新建画板 |
| PUT/PATCH | `/api/plugins/plant_diagram/<id>/` | 保存画板（前端整体覆盖 canvas） |
| DELETE | `/api/plugins/plant_diagram/<id>/` | 删除 |
| GET | `/api/plugins/plant_diagram/bindable_targets/?plant_code=EB` | 给节点绑定下拉用：返回该装置下可绑定的 sensor / device 简要列表（id、name、tag、unit、阈值） |

可绑定列表接口让编辑器无需另外加载所有传感器；返回结构示例：

```json
{
  "sensors": [
    { "id": "TT101", "name": "R1 进料温度", "tag": "TT-101", "unit": "K", "hi_threshold": 440 }
  ],
  "devices": [
    { "id": "FCV101", "name": "乙烯进料阀", "type": "valve" }
  ]
}
```

### 3.4 与 `services/realtime` 的关系

不动 realtime 层。画板运行时仍订阅 EB 插件的 SSE 流，前端按 `sensor_id` 把 sample 派发给画布上对应的节点。**Realtime 层只关心"点位最新值"，画板只关心"点位摆在哪里"，正交不冲突。**

---

## 四、前端架构

### 4.1 模块拆分

```
frontend/src/views/plugins/plant_diagram/
├── PlantDiagramView.vue          # 路由入口，区分编辑/运行两态
├── editor/
│   ├── DiagramEditor.vue         # 编辑器壳：工具箱 + 画布 + 右侧属性面板
│   ├── ToolboxPanel.vue          # 左侧图元工具箱（拖拽到画布即新建节点）
│   ├── PropertiesPanel.vue       # 右侧属性面板：选中节点 → 编辑 binding/data
│   └── nodes/
│       ├── InstrumentNode.vue    # 仪表圈（复用 InstrumentCard 的视觉）
│       ├── ValveNode.vue         # 阀门
│       ├── PumpNode.vue          # 泵
│       ├── VesselNode.vue        # 反应器/储罐
│       ├── ColumnNode.vue        # 塔
│       └── LabelNode.vue         # 文本注释
├── runtime/
│   └── DiagramRuntime.vue        # 只读运行态：SSE 数据流入节点，无编辑控件
└── composables/
    ├── useDiagramApi.js          # CRUD 封装
    └── useDiagramBindings.js     # 把 plantStore.samples 派发到节点
```

### 4.2 编辑器 UX

```
┌────────────────────────────────────────────────────────────────────┐
│ 顶部栏  [画板：EB 主反应区 ▾] [保存] [另存为] [运行预览] [返回]      │
├──────┬───────────────────────────────────────────────────┬─────────┤
│ 工 具 │                                                   │ 属 性    │
│ 箱   │           画 布（Vue Flow）                         │ 面 板    │
│      │                                                   │         │
│ 仪表 │   ⊙─────────[R1反应器]──────────⊙                 │ 节点ID  │
│ 阀门 │   TT-101                       FT-102             │ 类型    │
│ 泵   │                                                   │ 标签    │
│ 反应器│                                                   │ 绑定    │
│ 塔   │                                                   │  ○ 传感器│
│ 换热器│                                                   │  ○ 设备 │
│ 文本 │                                                   │  下拉 ▾│
│      │                                                   │ 显示设置│
└──────┴───────────────────────────────────────────────────┴─────────┘
```

交互细节：
- **拖入新节点**：从工具箱拖到画布触发 `onDrop`，按图元类型创建 node。
- **连线**：节点四边内置端口（top/right/bottom/left），鼠标从端口拖到另一节点的端口生成 edge。
- **多选 / 删除**：框选 + Delete 键。
- **快捷键**：Ctrl+S 保存、Ctrl+Z 撤销（用 [`@vueuse/core` useRefHistory](https://vueuse.org/core/useRefHistory)）、Space+拖拽 平移。
- **对齐线 / 网格吸附**：MVP 阶段用 `snapToGrid: 10`，进阶版考虑动态吸附线。
- **保存策略**：手动保存为主（避免乱改丢失），同时每 30s 自动存草稿到 localStorage，崩溃可恢复。

### 4.3 运行态

复用编辑器节点组件，但：
- 关闭拖拽 / 连线 / 工具箱 / 属性面板。
- 订阅 SSE，把 sample 按 `sensor_id` 派发到对应 `InstrumentNode`，触发数值刷新和状态色变化。
- 报警动画（脉冲）、链接到详情页（点节点跳 [SensorDetailView](../../frontend/src/views/sensors/SensorDetailView.vue)）。

### 4.4 与现有 EB 插件的关系

- EBPlantView 顶部保留扰动控制台和状态栏，**中间的网格区**改为：
  - 如果该 plant_code 已经有 default 画板 → 渲染画板运行态。
  - 否则 → 渲染当前的网格 + "创建画板"按钮，向下兼容。
- 老的 [InstrumentCard.vue](../../frontend/src/views/plugins/eb_plant/InstrumentCard.vue) 不删除，编辑器的 `InstrumentNode` 内部直接复用它的视觉模板（避免重复实现仪表圈 SVG）。

---

## 五、实施阶段

### 阶段 1：MVP 编辑器（W1–W2）

**目标**：能新建 / 保存一张画板，画布上可放仪表节点和反应器节点，可连线，可绑定传感器并显示实时值。

里程碑：
- [ ] 后端 `plant_diagram` 应用：`PlantDiagram` 模型 + 5 个 CRUD API + `bindable_targets`。迁移并接入主路由。
- [ ] 前端集成 Vue Flow，搭出 `DiagramEditor.vue` 框架，工具箱含 2 类节点（仪表、反应器）。
- [ ] `InstrumentNode` 复用 InstrumentCard 视觉，绑定传感器后从 plantStore 拿值显示。
- [ ] 保存 / 加载 / 删除 / 列表跑通。
- [ ] 在 EBPlantView 路由侧增加"画板"标签页入口。

验收：在 EB 装置下手动画出 5-6 个测点 + R1 + T1，连线，保存，刷新页面后位置和连线保持，并且实时值实时变。

### 阶段 2：图元扩展 + 运行态打磨（W3）

- [ ] 补齐图元：阀门（FCV/HV）、泵、塔、换热器、文本标签。每个图元独立 SVG，遵守 ISA 5.1 基本符号。
- [ ] 边类型区分：工艺管线（粗实线 + 箭头）/ 公用工程（虚线）/ 信号线（细虚线）。
- [ ] 端口路由优化：边自动避让节点（Vue Flow 提供 `step` / `smoothstep` 边）。
- [ ] 运行态独立路由：`/plugins/eb_plant/diagram/:id`（默认大屏入口）和 `/plugins/plant_diagram/:id/edit`（编辑器入口）。
- [ ] 报警态：节点根据 SSE 推送的 `status` 切换样式（warn / alarm），与现有 InstrumentCard 行为一致。

### 阶段 3：易用性 + 多装置复用（W4）

- [ ] 多画板切换：同一装置可建多张（主流程、公用工程、局部放大）。
- [ ] 撤销重做 + 自动草稿。
- [ ] 工具箱搜索 / 图元预览缩略图。
- [ ] 把编辑器升级为通用插件——其他装置（未来新建）只需把 `plant_code` 设过去就能用。
- [ ] 权限：只有 `is_staff` 能进入编辑器，普通用户只看运行态。

---

## 六、风险与决策点

| 风险 | 影响 | 缓解 |
| --- | --- | --- |
| Vue Flow 工业图能力不足（边路由复杂时丑） | 视觉不够"专业 P&ID" | MVP 完成后评估，必要时迁移到 X6（数据模型同构） |
| 一张画板节点 > 200 时性能下降 | 卡顿 | Vue Flow 支持 `onlyRenderVisibleElements`，按需开 |
| 多人同时编辑同一画板的冲突 | 后保存覆盖前保存 | MVP 不做协同；用 `updated_at` 做乐观锁，PUT 时带 `If-Unmodified-Since`，冲突时提示重载 |
| 绑定的 sensor_id 被删除 | 节点失效 | 运行时检测 binding 找不到 → 显示灰色"未绑定/已失效"标签，编辑器里红色标记提示 |
| 画板 JSON Schema 演进 | 老画板加载失败 | canvas 里存 `version`，前端按版本号做向前迁移 |

### 待用户决策

1. **画布引擎**：默认 Vue Flow。如果偏好工业图能力更强的 AntV X6（学习曲线 + 体积代价），需要在动工前确认。
2. **多画板还是单画板**：MVP 是否就支持"一个装置多张图"？我建议 MVP 先做"一个装置一张默认图"，阶段 3 再放开多图。
3. **是否引入 ECharts 内嵌**：节点上是否要带迷你曲线（sparkline）？这是一个亮点但会增加渲染压力，可放到阶段 3。
4. **图元来源**：MVP 阶段图元 SVG 自绘还是引用现有 SVG 库（如 [process-diagram-symbols](https://github.com/equinor/process-diagram-symbols) 等开源资源）？开源资源能省时间但要核查 license。

---

## 七、不在范围内

- 图元的物理仿真（流量平衡、压降计算）—— 由后端模拟器负责，画板只显示。
- DCS 风格的趋势曲线总览 —— 由独立 trend 视图覆盖，不挤进画板。
- 移动端编辑 —— 编辑只在桌面端做，移动端只有运行态查看。
- 实时协同（OT/CRDT）—— 太重，MVP 不做。

---

## 附录 A：如何添加一个新图元（5 步）

新图元有两种实现路径，按复杂度选：

**A. 简单单色 SVG 图元** —— 复用 [SimpleSymbolNode.vue](../../frontend/src/views/plugins/plant_diagram/editor/nodes/SimpleSymbolNode.vue)，所有 5 步都很轻：

1. **想好 `kind` 标识符**（小写蛇形，例如 `compressor`）。这是 canvas JSON 里 `node.type` 的取值。

2. **在 `SimpleSymbolNode.vue` 的模板里加一段 SVG**：
   ```vue
   <svg v-else-if="kind === 'compressor'" viewBox="0 0 70 60" class="sym-node__svg">
     <!-- 你的 SVG 元素 -->
   </svg>
   ```
   并在 `<style>` 里给 `.sym-node--compressor .sym-node__svg` 设宽高。

3. **在 `ToolboxPanel.vue` 里加预览 + 注册到 palette**：
   ```js
   const CompressorPreview = () => h('svg', { viewBox: '0 0 40 40', class: 'svg' }, [/* … */])
   // 然后在 palette 数组末尾加：
   { type: 'compressor', label: '压缩机', preview: CompressorPreview, defaultData: { label: 'K-1' } },
   ```

4. **在 `DiagramEditor.vue` 和 `DiagramRuntime.vue` 里各加一段 slot**：
   ```vue
   <template #node-compressor="nodeProps">
     <SimpleSymbolNode v-bind="nodeProps" kind="compressor" />
   </template>
   ```

5. **（可选）在 `PropertiesPanel.vue` 的 `nodeTypeLabel()` map 里加个中文别名**，让属性面板标题更友好。

**B. 复杂图元（要展示实时数据、多属性、自定义交互）** —— 仿 [InstrumentNode.vue](../../frontend/src/views/plugins/plant_diagram/editor/nodes/InstrumentNode.vue) 新建一个独立 .vue：

1. 同 A.1：定 `kind`。
2. **在 `editor/nodes/` 下新建 `XxxNode.vue`**：模板里放 4 个 `<Handle>`、读 `props.data.binding` 决定显示啥实时数据、按状态切样式（参考 InstrumentNode 的 `statusClass`）。
3. 同 A.3：注册 palette 项。
4. **在 `DiagramEditor.vue` 顶部 `import XxxNode from './nodes/XxxNode.vue'`**，加 slot 模板用 `XxxNode` 而不是 `SimpleSymbolNode`。运行态同理。
5. **如果有独有的编辑字段**（例如换热器的"冷热侧介质"），在 `PropertiesPanel.vue` 加一段 `v-if="node.type === 'xxx'"` 的 form-item。

**永远不要做的事**：
- 不要把图元位置 / 大小回写到 `Sensor.plant_metadata` —— canvas 整存整取，所有几何信息归画板。
- 不要在节点组件里直接调 API 拉数据 —— 走 `plantStore` / SSE 已经把数据流闭环了，节点只读取 store。
- 不要忘了 runtime slot —— 只注册 editor slot 会导致预览模式下节点变空白。

当前已注册的 9 种 `type`：`instrument` / `vessel` / `column` / `valve` / `pump` / `heat_exchanger` / `mixer` / `filter` / `label`。
