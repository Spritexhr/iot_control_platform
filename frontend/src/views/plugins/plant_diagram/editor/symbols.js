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
    size: { w: 70, h: 60 }, viewBox: '0 0 70 60', labelMode: 'below',
    draw: [
      { el: 'circle', cx: 35, cy: 35, r: 22 },
      { el: 'line', x1: 35, y1: 13, x2: 62, y2: 6, sw: 1.5 },
      { el: 'polygon', points: '35,35 22,28 22,42', fill: '#2a2a2a', stroke: 'none' },
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
    size: { w: 70, h: 60 }, viewBox: '0 0 70 60', labelMode: 'below',
    draw: [
      { el: 'circle', cx: 35, cy: 30, r: 22 },
      { el: 'line', x1: 35, y1: 8, x2: 35, y2: 52, sw: 1.2 },
      { el: 'line', x1: 13, y1: 30, x2: 57, y2: 30, sw: 1.2 },
      { el: 'line', x1: 19, y1: 14, x2: 51, y2: 46, sw: 1 },
      { el: 'line', x1: 51, y1: 14, x2: 19, y2: 46, sw: 1 },
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
    labelMode: 'plain',
  },
}

// 工具箱面板里仪表/容器的预览图形（这两类有专用节点组件，不在 SIMPLE_SYMBOLS）
const SPECIAL = {
  instrument: {
    label: '仪表', group: '仪表/容器',
    defaultData: { symbol: 'TT', label: '新仪表', show_value: true, show_threshold: true },
    glyph: {
      viewBox: '0 0 40 40',
      draw: [
        { el: 'circle', cx: 20, cy: 20, r: 16 },
        { el: 'line', x1: 4, y1: 20, x2: 36, y2: 20, sw: 1 },
        { el: 'text', x: 20, y: 16, text: 'TT', anchor: 'middle', size: 9 },
        { el: 'text', x: 20, y: 30, text: '—', anchor: 'middle', size: 8 },
      ],
    },
  },
  vessel: {
    label: '反应器', group: '仪表/容器',
    defaultData: { label: '反应器', shape: 'cstr' },
    glyph: {
      viewBox: '0 0 40 44',
      draw: [
        { el: 'rect', x: 8, y: 12, width: 24, height: 20 },
        { el: 'ellipse', cx: 20, cy: 12, rx: 12, ry: 5 },
        { el: 'ellipse', cx: 20, cy: 32, rx: 12, ry: 5 },
      ],
    },
  },
}

// 工具箱显示顺序
const ORDER = [
  'instrument', 'vessel', 'storage_tank', 'column',
  'pump', 'compressor', 'mixer',
  'heat_exchanger', 'filter',
  'valve', 'label',
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
