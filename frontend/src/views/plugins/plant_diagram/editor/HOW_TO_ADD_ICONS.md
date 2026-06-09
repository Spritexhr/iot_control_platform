# 如何给 P&ID 画板添加新图标

本文档说明如何在画板编辑器里扩展工艺符号库（阀门、塔、换热器之类的新变种）。

## 一、图标体系总览

整个图标体系由 **3 个文件**协同：

| 文件 | 职责 |
|---|---|
| `ToolboxPanel.vue` | 左侧工具栏的可拖拽条目列表（`palette` 数组 + 预览 SVG） |
| `nodes/SimpleSymbolNode.vue` | 简单符号节点的实际渲染（画布上的 SVG） |
| `DiagramEditor.vue` | 把 `type` 字符串注册到 VueFlow 的 `<template #node-xxx>` 槽 |

现存 9 种节点分两类：

**A. 独立组件（有特殊交互或字段）**

| `type` | 组件 | 用途 |
|---|---|---|
| `instrument` | `nodes/InstrumentNode.vue` | 仪表（圆圈 + 位号 + 实时值） |
| `vessel` | `nodes/VesselNode.vue` | 反应器（可配 shape: cstr / pfr 等） |

**B. 共用 SimpleSymbolNode（按 `kind` 切换 SVG）**

`column` / `valve` / `pump` / `heat_exchanger` / `mixer` / `filter` / `label`

---

## 二、选哪条路径？

- **加一个纯静态符号**（只有 SVG 形状 + 标签）→ 走 SimpleSymbolNode，**只改 3 个文件**
- **需要额外字段**（开度、流量、特殊绑定）或**特殊布局**（多 handle、状态色变化）→ 新建独立 `.vue` 组件，参考 `InstrumentNode.vue` / `VesselNode.vue`

下面以最常见的"加静态符号"为例。

---

## 三、完整示例：添加一个"储罐(Tank)"符号

### Step 1 — `nodes/SimpleSymbolNode.vue`

在 `<!-- 过滤器 -->` 那段下方加渲染块：

```vue
<!-- 储罐：圆柱形 -->
<svg v-else-if="kind === 'tank'" viewBox="0 0 60 80" class="sym-node__svg">
  <ellipse cx="30" cy="10" rx="26" ry="6" fill="#fff" stroke="#2a2a2a" stroke-width="1.5" />
  <rect x="4" y="10" width="52" height="60" fill="#fff" stroke="#2a2a2a" stroke-width="1.5" />
  <ellipse cx="30" cy="70" rx="26" ry="6" fill="#fff" stroke="#2a2a2a" stroke-width="1.5" />
</svg>
```

在 `<style scoped>` 里给一个尺寸（和上面 `viewBox` 同比例）：

```css
.sym-node--tank .sym-node__svg { width: 60px; height: 80px; }
```

### Step 2 — `ToolboxPanel.vue`

在其它 `Preview` 函数附近加预览图：

```js
const TankPreview = () =>
  h('svg', { viewBox: '0 0 40 40', class: 'svg' }, [
    h('ellipse', { cx: 20, cy: 8, rx: 14, ry: 4, fill: '#fff', stroke: '#2a2a2a', 'stroke-width': 1.5 }),
    h('rect', { x: 6, y: 8, width: 28, height: 24, fill: '#fff', stroke: '#2a2a2a', 'stroke-width': 1.5 }),
    h('ellipse', { cx: 20, cy: 32, rx: 14, ry: 4, fill: '#fff', stroke: '#2a2a2a', 'stroke-width': 1.5 }),
  ])
```

在 `palette` 数组里加一项：

```js
{ type: 'tank', label: '储罐', preview: TankPreview, defaultData: { label: 'V-1' } },
```

### Step 3 — `DiagramEditor.vue`

在 `<template #node-filter>` 那段下方加注册：

```vue
<template #node-tank="nodeProps">
  <SimpleSymbolNode v-bind="nodeProps" kind="tank" />
</template>
```

完成。重启 `npm run dev` 后，工具箱多出"储罐"，可拖、可连线、可保存。

---

## 四、关键约定与常见坑

1. **三处字符串必须严格一致**
   - ToolboxPanel 的 `palette[].type` = `'tank'`
   - DiagramEditor 的 `<template #node-tank>`
   - SimpleSymbolNode 的 `kind === 'tank'`
   
   不一致会导致工具箱能拖出来但画布上不渲染。

2. **后端无需改动** — `PlantDiagram.canvas` 是 JSONField，新 `type` 自动存得下，**不用 migrate**。

3. **viewBox 与 CSS 尺寸要匹配** — SVG 内部用 `viewBox` 坐标系，外部用 `.sym-node--xxx .sym-node__svg { width; height; }` 写死像素。两者比例不一致会被拉伸/压缩。

4. **连接点自动有** — `SimpleSymbolNode.vue` 第 3-6 行的 4 个 `<Handle>` 已经布在四边，任何新符号都自动有上下左右 4 个连线锚点，不需要单独处理。

5. **defaultData 决定新节点的初始字段** — 工具箱拖进画布时，`payload.defaultData` 会原样写入节点的 `data`。如果新符号要有特殊默认（比如阀门开度），加在这里。

---

## 五、什么时候要新建独立组件？

`SimpleSymbolNode` 不够用的场景：

- 节点要显示**实时绑定值**（参考 `InstrumentNode.vue`，它读 `data.binding` 显示数字 + 阈值条）
- 节点形状要随某个 `data` 字段**动态变化**（参考 `VesselNode.vue` 的 `shape: cstr / pfr`）
- 节点需要**非四边的特殊 handle 位置**（默认 4 个 Handle 不够用）
- 节点要有**交互按钮**（点击展开/收起、内嵌操作）

新建独立组件的步骤：

1. 在 `nodes/` 下新建 `YourNode.vue`，结构参考 `InstrumentNode.vue`：
   - 顶部放 `<Handle>`
   - 中间放 SVG / 内容
   - props 接收 `id` / `data` / `selected` 等 VueFlow 透传的字段
2. `DiagramEditor.vue` 顶部 `import YourNode from './nodes/YourNode.vue'`
3. 加 `<template #node-your="nodeProps"><YourNode v-bind="nodeProps" /></template>`
4. `ToolboxPanel.vue` 的 `palette` 加 `{ type: 'your', ... }`（不再需要 `kind`，因为不走 SimpleSymbolNode）

---

## 六、进阶：符号库膨胀后的重构方向

当前 SimpleSymbolNode 用 `v-if/v-else-if` 链切换 SVG，9 种以内可读性良好。如果符号数超过 20+，建议：

- 把每个符号的 SVG 拆成 `nodes/symbols/Tank.vue` 之类的微组件
- SimpleSymbolNode 用 `<component :is="symbolMap[kind]">` 动态选
- 符号 + 预览 + 默认数据通过一个对象集中登记，避免三个文件手动同步

但这是预防性重构，**不要为了"未来可能扩展"提前做** —— 等真的超过 15 种符号再说。

---

## 速查清单

加一个静态符号 = 改这 3 处：

- [ ] `nodes/SimpleSymbolNode.vue`：加 `<svg v-else-if="kind === 'xxx'">` 块 + CSS 尺寸
- [ ] `ToolboxPanel.vue`：加 `XxxPreview` 函数 + `palette` 数组一项
- [ ] `DiagramEditor.vue`：加 `<template #node-xxx>` 注册块
