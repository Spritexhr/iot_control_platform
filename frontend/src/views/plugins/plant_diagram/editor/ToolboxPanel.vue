<template>
  <aside class="toolbox">
    <div class="toolbox__section-title">图元</div>
    <div
      v-for="item in palette"
      :key="item.type"
      class="toolbox__item"
      :draggable="true"
      @dragstart="onDragStart($event, item)"
    >
      <component :is="item.preview" class="toolbox__preview" />
      <div class="toolbox__label">{{ item.label }}</div>
    </div>

    <div class="toolbox__hint">
      把图元拖到画布即可放置<br />
      节点四边为连接点，鼠标拖出生成连线
    </div>
  </aside>
</template>

<script setup>
import { h } from 'vue'

const InstrumentPreview = () =>
  h('svg', { viewBox: '0 0 40 40', class: 'svg' }, [
    h('circle', { cx: 20, cy: 20, r: 16, fill: '#fff', stroke: '#2a2a2a', 'stroke-width': 1.5 }),
    h('line', { x1: 4, y1: 20, x2: 36, y2: 20, stroke: '#2a2a2a', 'stroke-width': 1 }),
    h('text', { x: 20, y: 16, 'text-anchor': 'middle', 'font-size': 9, fill: '#2a2a2a' }, 'TT'),
    h('text', { x: 20, y: 30, 'text-anchor': 'middle', 'font-size': 8, fill: '#2a2a2a' }, '—'),
  ])

const VesselPreview = () =>
  h('svg', { viewBox: '0 0 40 40', class: 'svg' }, [
    h('rect', { x: 8, y: 6, width: 24, height: 28, rx: 12, fill: '#fff', stroke: '#2a2a2a', 'stroke-width': 1.5 }),
  ])

const ColumnPreview = () =>
  h('svg', { viewBox: '0 0 40 40', class: 'svg' }, [
    h('rect', { x: 14, y: 4, width: 12, height: 32, fill: '#fff', stroke: '#2a2a2a', 'stroke-width': 1.5 }),
    h('line', { x1: 14, y1: 14, x2: 26, y2: 14, stroke: '#2a2a2a', 'stroke-width': 0.8 }),
    h('line', { x1: 14, y1: 20, x2: 26, y2: 20, stroke: '#2a2a2a', 'stroke-width': 0.8 }),
    h('line', { x1: 14, y1: 26, x2: 26, y2: 26, stroke: '#2a2a2a', 'stroke-width': 0.8 }),
  ])

const ValvePreview = () =>
  h('svg', { viewBox: '0 0 40 40', class: 'svg' }, [
    h('polygon', { points: '6,10 20,20 6,30', fill: '#fff', stroke: '#2a2a2a', 'stroke-width': 1.5 }),
    h('polygon', { points: '34,10 20,20 34,30', fill: '#fff', stroke: '#2a2a2a', 'stroke-width': 1.5 }),
  ])

const PumpPreview = () =>
  h('svg', { viewBox: '0 0 40 40', class: 'svg' }, [
    h('circle', { cx: 20, cy: 20, r: 14, fill: '#fff', stroke: '#2a2a2a', 'stroke-width': 1.5 }),
    h('line', { x1: 20, y1: 6, x2: 34, y2: 6, stroke: '#2a2a2a', 'stroke-width': 1.5 }),
  ])

const HeatExchangerPreview = () =>
  h('svg', { viewBox: '0 0 40 40', class: 'svg' }, [
    h('rect', { x: 4, y: 14, width: 32, height: 12, rx: 3, fill: '#fff', stroke: '#2a2a2a', 'stroke-width': 1.5 }),
    h('line', { x1: 4, y1: 18, x2: 36, y2: 18, stroke: '#2a2a2a', 'stroke-width': 0.8 }),
    h('line', { x1: 4, y1: 22, x2: 36, y2: 22, stroke: '#2a2a2a', 'stroke-width': 0.8 }),
    h('line', { x1: 10, y1: 6, x2: 10, y2: 14, stroke: '#2a2a2a', 'stroke-width': 1.5 }),
    h('line', { x1: 30, y1: 26, x2: 30, y2: 34, stroke: '#2a2a2a', 'stroke-width': 1.5 }),
  ])

const MixerPreview = () =>
  h('svg', { viewBox: '0 0 40 40', class: 'svg' }, [
    h('circle', { cx: 20, cy: 20, r: 14, fill: '#fff', stroke: '#2a2a2a', 'stroke-width': 1.5 }),
    h('line', { x1: 10, y1: 10, x2: 30, y2: 30, stroke: '#2a2a2a', 'stroke-width': 1 }),
    h('line', { x1: 30, y1: 10, x2: 10, y2: 30, stroke: '#2a2a2a', 'stroke-width': 1 }),
  ])

const FilterPreview = () =>
  h('svg', { viewBox: '0 0 40 40', class: 'svg' }, [
    h('polygon', { points: '6,6 34,6 24,20 24,34 16,34 16,20', fill: '#fff', stroke: '#2a2a2a', 'stroke-width': 1.5 }),
  ])

const LabelPreview = () =>
  h('svg', { viewBox: '0 0 40 40', class: 'svg' }, [
    h('text', { x: 20, y: 24, 'text-anchor': 'middle', 'font-size': 14, fill: '#2a2a2a' }, 'A'),
  ])

const palette = [
  { type: 'instrument',     label: '仪表',   preview: InstrumentPreview,    defaultData: { symbol: 'TT', label: '新仪表', show_value: true, show_threshold: true } },
  { type: 'vessel',         label: '反应器', preview: VesselPreview,        defaultData: { label: '反应器', shape: 'cstr' } },
  { type: 'column',         label: '塔',     preview: ColumnPreview,        defaultData: { label: 'T-1' } },
  { type: 'valve',          label: '阀门',   preview: ValvePreview,         defaultData: { label: 'FCV' } },
  { type: 'pump',           label: '泵',     preview: PumpPreview,          defaultData: { label: 'P-1' } },
  { type: 'heat_exchanger', label: '换热器', preview: HeatExchangerPreview, defaultData: { label: 'E-1' } },
  { type: 'mixer',          label: '混合器', preview: MixerPreview,         defaultData: { label: 'MIX' } },
  { type: 'filter',         label: '过滤器', preview: FilterPreview,        defaultData: { label: 'FT' } },
  { type: 'label',          label: '文本',   preview: LabelPreview,         defaultData: { label: '注释' } },
]

function onDragStart(event, item) {
  const payload = {
    type: item.type,
    defaultData: item.defaultData,
  }
  event.dataTransfer.setData('application/x-plant-node', JSON.stringify(payload))
  event.dataTransfer.effectAllowed = 'copy'
}
</script>

<style scoped>
.toolbox {
  width: 110px;
  flex-shrink: 0;
  background: var(--iot-bg-card);
  border-right: 1px solid var(--iot-border-color-light);
  padding: 10px 8px;
  overflow-y: auto;
}

.toolbox__section-title {
  font-size: var(--iot-font-size-xs);
  color: var(--iot-text-secondary);
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.toolbox__item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 8px 4px;
  margin-bottom: 6px;
  border: 1px solid var(--iot-border-color-light);
  border-radius: var(--iot-radius-sm);
  background: var(--iot-bg-card-hover);
  cursor: grab;
  user-select: none;
  transition: border-color var(--iot-transition-fast), background var(--iot-transition-fast);
}

.toolbox__item:hover {
  border-color: var(--iot-color-primary);
  background: var(--iot-color-primary-bg);
}

.toolbox__item:active {
  cursor: grabbing;
}

.toolbox__preview :deep(.svg) {
  width: 40px;
  height: 40px;
}

.toolbox__label {
  font-size: var(--iot-font-size-xs);
  color: var(--iot-text-regular);
}

.toolbox__hint {
  margin-top: 14px;
  font-size: 11px;
  color: var(--iot-text-secondary);
  line-height: 1.5;
  padding: 8px 4px;
  border-top: 1px dashed var(--iot-border-color-light);
}
</style>
