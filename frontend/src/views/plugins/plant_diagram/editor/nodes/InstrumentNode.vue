<template>
  <div class="instr-node" :class="statusClass" :title="title">
    <Handle id="left"   type="source" :position="Position.Left" />
    <Handle id="right"  type="source" :position="Position.Right" />
    <Handle id="top"    type="source" :position="Position.Top" />
    <Handle id="bottom" type="source" :position="Position.Bottom" />

    <svg viewBox="0 0 60 60" class="instr-node__svg">
      <circle cx="30" cy="30" r="26" class="instr-node__ring" />
      <line x1="4" y1="30" x2="56" y2="30" class="instr-node__divider" />
      <text x="30" y="22" text-anchor="middle" class="instr-node__type">{{ tagType }}</text>
      <text x="30" y="48" text-anchor="middle" class="instr-node__num">{{ tagNum }}</text>
    </svg>

    <div class="instr-node__body">
      <div class="instr-node__label">{{ data.label || '未命名' }}</div>
      <div v-if="data.show_value !== false" class="instr-node__value-row">
        <span class="instr-node__value">{{ displayValue }}</span>
        <span class="instr-node__unit">{{ unit }}</span>
      </div>
      <div v-if="data.show_threshold !== false && hasThreshold" class="instr-node__meta">
        {{ formatThr(loThreshold) }} ~ {{ formatThr(hiThreshold) }}
      </div>
      <div v-if="!binding" class="instr-node__unbound">未绑定</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'

import { usePlantStore } from '@/stores/plant'

const props = defineProps({
  id:   { type: String, required: true },
  data: { type: Object, required: true },
})

const plantStore = usePlantStore()

const binding = computed(() => props.data?.binding?.id || '')
const sample = computed(() => binding.value ? plantStore.samples.get(binding.value) : null)

const tagSymbol = computed(() => props.data?.symbol || (sample.value?.tag?.split('-')[0] ?? ''))
const tagType = computed(() => tagSymbol.value)
const tagNum = computed(() => {
  // 优先用绑定数据里的 tag 后段，否则用 data.label 截短
  const tag = sample.value?.tag || ''
  const parts = tag.split('-')
  return parts.length > 1 ? parts[1] : (props.data?.tag_num || '')
})

const unit = computed(() => sample.value?.unit || props.data?.unit || '')
const hiThreshold = computed(() => sample.value?.metadata?.hi_threshold ?? props.data?.hi_threshold)
const loThreshold = computed(() => sample.value?.metadata?.lo_threshold ?? props.data?.lo_threshold)
const hasThreshold = computed(() => hiThreshold.value != null || loThreshold.value != null)

const displayValue = computed(() => {
  const v = sample.value?.value
  if (v === null || v === undefined || Number.isNaN(v)) return '--'
  const abs = Math.abs(v)
  if (abs >= 100) return v.toFixed(1)
  if (abs >= 1) return v.toFixed(2)
  return v.toFixed(3)
})

const status = computed(() => sample.value?.status || 'normal')
const statusClass = computed(() => ({
  'instr-node--warn':  status.value === 'warn_high' || status.value === 'warn_low',
  'instr-node--alarm': status.value === 'alarm_high' || status.value === 'alarm_low',
  'instr-node--unbound': !binding.value,
}))

const title = computed(() => {
  const id = binding.value || '(未绑定)'
  const ts = sample.value?.ts ? new Date(sample.value.ts * 1000).toLocaleTimeString() : ''
  return `${props.data?.label || ''}\n绑定: ${id}\n最近: ${ts}`
})

function formatThr(v) {
  if (v == null) return '—'
  return Number(v).toFixed(Math.abs(v) >= 100 ? 0 : 1)
}
</script>

<style scoped>
.instr-node {
  display: flex;
  align-items: stretch;
  gap: 8px;
  padding: 8px 10px;
  background: #fafaf7;
  border: 1px solid #2a2a2a;
  border-radius: 4px;
  font-family: 'JetBrains Mono', 'SFMono-Regular', Consolas, monospace;
  width: 180px;
  min-height: 72px;
  transition: background var(--iot-transition-fast), border-color var(--iot-transition-fast);
}

.instr-node__svg {
  width: 52px;
  height: 52px;
  flex-shrink: 0;
}

.instr-node__ring     { fill: #fff; stroke: #2a2a2a; stroke-width: 1.5; }
.instr-node__divider  { stroke: #2a2a2a; stroke-width: 1; }
.instr-node__type,
.instr-node__num      { font-size: 12px; fill: #2a2a2a; letter-spacing: 0.5px; font-family: inherit; }

.instr-node__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.instr-node__label {
  font-size: 11px;
  color: #555;
  font-family: -apple-system, 'PingFang SC', sans-serif;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.instr-node__value-row {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.instr-node__value {
  font-size: 18px;
  font-weight: 600;
  color: #2a2a2a;
  font-variant-numeric: tabular-nums;
}

.instr-node__unit { font-size: 11px; color: #888; }

.instr-node__meta {
  font-size: 10px;
  color: #888;
  font-variant-numeric: tabular-nums;
}

.instr-node__unbound {
  font-size: 10px;
  color: #c0392b;
  font-family: -apple-system, sans-serif;
}

.instr-node--warn {
  background: #fef9e7;
  border-color: #c9a227;
  .instr-node__ring { stroke: #b07a16; stroke-width: 2; }
}

.instr-node--alarm {
  background: #fdecea;
  border-color: #d14b3b;
  animation: alarm-pulse 1.2s ease-in-out infinite;
  .instr-node__ring  { stroke: #d14b3b; stroke-width: 2.5; }
  .instr-node__value { color: #c0392b; }
}

.instr-node--unbound {
  border-style: dashed;
  border-color: #999;
}

@keyframes alarm-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(209, 75, 59, 0); }
  50%      { box-shadow: 0 0 0 4px rgba(209, 75, 59, 0.25); }
}
</style>
