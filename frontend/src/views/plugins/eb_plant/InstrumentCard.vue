<template>
  <div class="instr-card" :class="statusClass" :title="title">
    <!-- ISA 风格圆形位号 -->
    <div class="instr-card__symbol">
      <svg viewBox="0 0 60 60" class="instr-card__svg">
        <circle cx="30" cy="30" r="26" class="instr-card__ring" />
        <line x1="4" y1="30" x2="56" y2="30" class="instr-card__divider" />
        <text x="30" y="22" text-anchor="middle" class="instr-card__type">{{ tagType }}</text>
        <text x="30" y="48" text-anchor="middle" class="instr-card__num">{{ tagNum }}</text>
      </svg>
    </div>

    <div class="instr-card__body">
      <div class="instr-card__name">{{ name }}</div>

      <div class="instr-card__value-row">
        <span class="instr-card__value">{{ displayValue }}</span>
        <span class="instr-card__unit">{{ unit }}</span>
      </div>

      <div class="instr-card__meta">
        <span class="instr-card__range">
          {{ formatThreshold(loThreshold) }} ~ {{ formatThreshold(hiThreshold) }}
        </span>
        <span class="instr-card__status">{{ statusLabel }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  sample: { type: Object, required: true },
})

const tag = computed(() => props.sample?.tag || '')
const tagType = computed(() => tag.value.split('-')[0] || '')
const tagNum = computed(() => tag.value.split('-')[1] || '')
const name = computed(() => props.sample?.metadata?.name || tag.value)
const unit = computed(() => props.sample?.unit || '')

const status = computed(() => props.sample?.status || 'normal')
const hiThreshold = computed(() => props.sample?.metadata?.hi_threshold)
const loThreshold = computed(() => props.sample?.metadata?.lo_threshold)

const displayValue = computed(() => {
  const v = props.sample?.value
  if (v === null || v === undefined || Number.isNaN(v)) return '--'
  const abs = Math.abs(v)
  if (abs >= 100) return v.toFixed(1)
  if (abs >= 1) return v.toFixed(2)
  return v.toFixed(3)
})

const statusClass = computed(() => ({
  'instr-card--normal': status.value === 'normal',
  'instr-card--warn': status.value === 'warn_high' || status.value === 'warn_low',
  'instr-card--alarm': status.value === 'alarm_high' || status.value === 'alarm_low',
}))

const statusLabel = computed(() => {
  switch (status.value) {
    case 'warn_high': return '↑ 高警'
    case 'warn_low': return '↓ 低警'
    case 'alarm_high': return '↑ 高报'
    case 'alarm_low': return '↓ 低报'
    default: return '正常'
  }
})

const title = computed(() => {
  const ts = props.sample?.ts ? new Date(props.sample.ts * 1000).toLocaleTimeString() : ''
  return `${tag.value} ${name.value}\n最近更新: ${ts}`
})

function formatThreshold(v) {
  if (v === null || v === undefined) return '—'
  return Number(v).toFixed(Math.abs(v) >= 100 ? 0 : 1)
}
</script>

<style scoped lang="scss">
.instr-card {
  display: flex;
  align-items: stretch;
  gap: 12px;
  padding: 12px 14px;
  background: #fafaf7;
  border: 1px solid #2a2a2a;
  border-radius: 4px;
  transition: background-color 0.2s, border-color 0.2s;
  position: relative;
  font-family: 'JetBrains Mono', 'SFMono-Regular', Consolas, monospace;
}

.instr-card__symbol {
  width: 60px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
}

.instr-card__svg {
  width: 100%;
  height: 60px;
}

.instr-card__ring {
  fill: #ffffff;
  stroke: #2a2a2a;
  stroke-width: 1.5;
}

.instr-card__divider {
  stroke: #2a2a2a;
  stroke-width: 1;
}

.instr-card__type,
.instr-card__num {
  font-size: 12px;
  font-family: inherit;
  fill: #2a2a2a;
  letter-spacing: 0.5px;
}

.instr-card__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.instr-card__name {
  font-size: 12px;
  color: #555;
  font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.instr-card__value-row {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.instr-card__value {
  font-size: 24px;
  font-weight: 600;
  color: #2a2a2a;
  font-variant-numeric: tabular-nums;
}

.instr-card__unit {
  font-size: 12px;
  color: #888;
}

.instr-card__meta {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #888;
}

.instr-card__range {
  font-variant-numeric: tabular-nums;
}

.instr-card__status {
  font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

// ============ 报警态 ============
.instr-card--warn {
  background: #fef9e7;
  border-color: #c9a227;
  .instr-card__status { color: #b07a16; font-weight: 600; }
  .instr-card__ring   { stroke: #b07a16; stroke-width: 2; }
}

.instr-card--alarm {
  background: #fdecea;
  border-color: #d14b3b;
  animation: alarm-pulse 1.2s ease-in-out infinite;
  .instr-card__status { color: #c0392b; font-weight: 700; }
  .instr-card__ring   { stroke: #d14b3b; stroke-width: 2.5; }
  .instr-card__value  { color: #c0392b; }
}

@keyframes alarm-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(209, 75, 59, 0); }
  50%      { box-shadow: 0 0 0 4px rgba(209, 75, 59, 0.2); }
}
</style>
