/**
 * P&ID 图元注册表（唯一数据源）。
 *
 * 新增一个工业图元 = 在 SIMPLE_SYMBOLS 里加一条，再把 type 挂进 ORDER。
 * 渲染由通用 SymbolNode + SymbolGlyph 自动完成，无需新建 .vue 文件、
 * 无需改 DiagramEditor / DiagramRuntime 的节点插槽。
 *
 * 几何用基础图形数组 draw 描述，坐标基于该图元自己的 viewBox：
 *   { el: 'line'|'polyline'|'rect'|'circle'|'ellipse'|'polygon'|'path'|'text', ...svg属性 }
 * 约定的简写：
 *   sw     -> stroke-width
 *   fill   -> 填充（默认：闭合图形 #fff，线条/路径 none）
 *   stroke -> 描边（默认 #2a2a2a）
 *   text/anchor/size -> 仅 el:'text' 用（文本内容 / text-anchor / font-size）
 *
 * 仪表(instrument)、容器(vessel) 有各自的专用节点组件（实时取值 / 可缩放），
 * 不走 SIMPLE_SYMBOLS，只在 PALETTE 里给一个工具箱预览。
 */

// labelMode: 'below' 图形下方小标签 | 'plain' 纯文本注释块 | 'none' 不显示
export const SIMPLE_SYMBOLS = {
  vessel: {
    label: '反应器', group: '仪表/容器', defaultData: { label: '反应器' },
    size: { w: 56, h: 94 }, viewBox: '0 0 56 94', labelMode: 'below',
    draw: [
      { el: 'ellipse', cx: 28, cy: 32, rx: 22, ry: 7 },
      { el: 'line', x1: 6, y1: 32, x2: 6, y2: 83 },
      { el: 'line', x1: 50, y1: 32, x2: 50, y2: 83 },
      { el: 'ellipse', cx: 28, cy: 83, rx: 22, ry: 7 },
      { el: 'circle', cx: 28, cy: 8, r: 5 },
      { el: 'line', x1: 28, y1: 13, x2: 28, y2: 61 },
      { el: 'polyline', points: '21,67 21,55 34,66 34,54' },
    ],
  },

  valve: {
    label: '阀门', group: '管路', defaultData: { label: 'FCV' },
    size: { w: 80, h: 50 }, viewBox: '0 0 80 50', labelMode: 'below',
    draw: [
      { el: 'polygon', points: '6,8 40,25 6,42' },
      { el: 'polygon', points: '74,8 40,25 74,42' },
    ],
  },

  column: {
    label: '塔', group: '仪表/容器', defaultData: { label: 'T-1' },
    size: { w: 60, h: 140 }, viewBox: '0 0 60 140', labelMode: 'below',
    draw: [
      { el: 'ellipse', cx: 30, cy: 10, rx: 26, ry: 8 },
      { el: 'rect', x: 4, y: 10, width: 52, height: 120 },
      { el: 'ellipse', cx: 30, cy: 130, rx: 26, ry: 8 },
      { el: 'line', x1: 4, y1: 40, x2: 56, y2: 40, sw: 0.7 },
      { el: 'line', x1: 4, y1: 60, x2: 56, y2: 60, sw: 0.7 },
      { el: 'line', x1: 4, y1: 80, x2: 56, y2: 80, sw: 0.7 },
      { el: 'line', x1: 4, y1: 100, x2: 56, y2: 100, sw: 0.7 },
    ],
  },

  pump: {
    label: '泵', group: '动设备', defaultData: { label: 'P-1' },
    size: { w: 70, h: 80 }, viewBox: '0 0 70 80', labelMode: 'below',
    draw: [
      { el: 'circle', cx: 40, cy: 40, r: 20 },
      { el: 'line', x1: 28, y1: 57, x2: 19, y2: 69 },
      { el: 'line', x1: 53, y1: 56, x2: 63, y2: 70 },
      { el: 'line', x1: 20, y1: 69, x2: 62, y2: 69 },
      { el: 'line', x1: 6, y1: 40, x2: 40, y2: 40 },
      { el: 'line', x1: 60, y1: 40, x2: 60, y2: 10 },
      { el: 'polyline', points: '37,36 41,40 37,44' },
      { el: 'polyline', points: '56,15 60,10 64,15' },
    ],
  },


  compressor: {
    label: '压缩机', group: '动设备', defaultData: { label: 'C-1' },
    size: { w: 80, h: 56 }, viewBox: '0 0 80 56', labelMode: 'below',
    draw: [
      { el: 'polygon', points: '8,16 72,6 72,50 8,40' },
    ],
  },

  mixer: {
    label: '混合器', group: '动设备', defaultData: { label: 'MIX' },
    size: { w: 76, h: 48 }, viewBox: '0 0 76 48', labelMode: 'below',
    draw: [
      { el: 'rect', x: 9, y: 16, width: 58, height: 16 },
      { el: 'rect', x: 18, y: 7, width: 12, height: 9 },
      { el: 'line', x1: 9, y1: 9, x2: 9, y2: 39 },
      { el: 'line', x1: 67, y1: 9, x2: 67, y2: 39 },
      { el: 'line', x1: 18, y1: 16, x2: 18, y2: 32 },
      { el: 'line', x1: 28, y1: 16, x2: 28, y2: 32 },
      { el: 'line', x1: 38, y1: 16, x2: 38, y2: 32 },
      { el: 'line', x1: 48, y1: 16, x2: 48, y2: 32 },
      { el: 'line', x1: 58, y1: 16, x2: 58, y2: 32 },
    ],
  },

  heat_exchanger: {
    label: '换热器', group: '换热/分离', defaultData: { label: 'E-1' },
    size: { w: 110, h: 56 }, viewBox: '0 0 100 50', labelMode: 'below',
    draw: [
      { el: 'rect', x: 6, y: 10, width: 88, height: 30, rx: 6 },
      { el: 'line', x1: 6, y1: 20, x2: 94, y2: 20, sw: 1 },
      { el: 'line', x1: 6, y1: 30, x2: 94, y2: 30, sw: 1 },
      { el: 'line', x1: 18, y1: 2, x2: 18, y2: 10, sw: 1.5 },
      { el: 'line', x1: 82, y1: 40, x2: 82, y2: 48, sw: 1.5 },
    ],
  },

  filter: {
    label: '过滤器', group: '换热/分离', defaultData: { label: 'FT' },
    size: { w: 60, h: 70 }, viewBox: '0 0 60 70', labelMode: 'below',
    draw: [
      { el: 'polygon', points: '6,8 54,8 36,36 36,62 24,62 24,36' },
      { el: 'line', x1: 10, y1: 20, x2: 10, y2: 14, sw: 0.8 },
      { el: 'line', x1: 18, y1: 20, x2: 18, y2: 14, sw: 0.8 },
      { el: 'line', x1: 26, y1: 20, x2: 26, y2: 14, sw: 0.8 },
      { el: 'line', x1: 34, y1: 20, x2: 34, y2: 14, sw: 0.8 },
      { el: 'line', x1: 42, y1: 20, x2: 42, y2: 14, sw: 0.8 },
      { el: 'line', x1: 50, y1: 20, x2: 50, y2: 14, sw: 0.8 },
    ],
  },

  storage_tank: {
    label: '储罐', group: '仪表/容器', defaultData: { label: 'TK-1' },
    size: { w: 70, h: 90 }, viewBox: '0 0 70 90', labelMode: 'below',
    draw: [
      { el: 'rect', x: 6, y: 14, width: 58, height: 64 },
      { el: 'ellipse', cx: 35, cy: 14, rx: 29, ry: 9 },
      { el: 'ellipse', cx: 35, cy: 78, rx: 29, ry: 9 },
    ],
  },

  label: {
    label: '文本', group: '标注', defaultData: { label: '注释' },
    labelMode: 'plain', rotatable: false, // 整个图元就是文字本身，没有独立于文字的图形可转
  },

  stream_inlet: {
    label: '物流进口标签', group: '物流标签', defaultData: { label: '物流进口' },
    size: { w: 56, h: 25 }, viewBox: '0 0 56 25', labelMode: 'below',
    draw: [
        { el: 'polygon', points: '8,6 40,6 47,12 40,18 8,18' },
    ],
  },

  stream_outlet: {
    label: '物流出口标签', group: '物流标签', defaultData: { label: '物流出口' },
    size: { w: 56, h: 25 }, viewBox: '0 0 56 25', labelMode: 'below',
    draw: [
        { el: 'polygon', points: '47,6 47,18 17,18 9,12 18,6' },
    ],
  },
}

// instrument 有专用节点组件（传感器绑定 + 实时取值），不在 SIMPLE_SYMBOLS
const SPECIAL = {
  instrument: {
    label: '仪表', group: '仪表/容器',
    defaultData: { symbol: 'TT', label: '新仪表', show_value: true, show_threshold: true },
    // 目前唯一支持绑定的图元（绑传感器实时取值）。以后要给其他图元（如阀门/泵）
    // 加设备绑定+命令，只需在对应条目加 bindable:['device']，PropertiesPanel 会自动出现绑定 UI
    bindable: ['sensor'],
    // 仪表泡是纯文字/数值卡片，没有独立于文字的图形，P&ID 里也永远正向显示，不参与旋转/镜像
    rotatable: false,
    // 预览跟画布上的 InstrumentNode 保持一致的卡片造型（名称行 + 数值/单位行），
    // 而不是传统 ISA 气泡符号，避免拖出来的图元跟预览长得不一样
    glyph: {
      viewBox: '0 0 40 40',
      draw: [
        { el: 'rect', x: 2, y: 7, width: 36, height: 26, rx: 2 },
        { el: 'line', x1: 2, y1: 17, x2: 38, y2: 17, sw: 0.6 },
        { el: 'text', x: 20, y: 14, text: 'PT-01', anchor: 'middle', size: 6 },
        { el: 'text', x: 13, y: 29, text: '88.2', anchor: 'middle', size: 9 },
        { el: 'text', x: 32, y: 29, text: 'kPa', anchor: 'middle', size: 5 },
      ],
    },
  },
}

// 按 type 查图元的注册表条目（label/group/defaultData/bindable/rotatable 等）
export function getNodeMeta(type) {
  return SPECIAL[type] || SIMPLE_SYMBOLS[type] || null
}

// 工具箱显示顺序
const ORDER = [
  'instrument', 'vessel', 'storage_tank', 'column',
  'pump', 'compressor', 'mixer',
  'heat_exchanger', 'filter',
  'valve', 'label',
  'stream_inlet', 'stream_outlet',
]

function labelGlyph() {
  return { viewBox: '0 0 40 40', draw: [{ el: 'text', x: 20, y: 26, text: 'A', anchor: 'middle', size: 16 }] }
}

// 工具箱面板用的有序清单：每项 { type, label, group, defaultData, glyph:{viewBox,draw} }
export const PALETTE = ORDER.map((type) => {
  if (SPECIAL[type]) {
    const s = SPECIAL[type]
    return { type, label: s.label, group: s.group, defaultData: s.defaultData, glyph: s.glyph }
  }
  const s = SIMPLE_SYMBOLS[type]
  return {
    type,
    label: s.label,
    group: s.group,
    defaultData: s.defaultData,
    glyph: s.draw ? { viewBox: s.viewBox, draw: s.draw } : labelGlyph(),
  }
})
