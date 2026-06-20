<template>
  <div class="instr-card" :class="statusClass" :title="title">
    <div class="instr-card__header">
      <span class="instr-card__name">{{ name }}</span>
      <span class="instr-card__online" :class="onlineClass">{{ onlineLabel }}</span>
    </div>

    <div v-if="description" class="instr-card__desc">{{ description }}</div>

    <div class="instr-card__value-row">
      <span class="instr-card__value">{{ displayValue }}</span>
      <span class="instr-card__unit">{{ unit }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  sample: { type: Object, required: true },
  now:    { type: Number, default: () => Date.now() },
})

const tag         = computed(() => props.sample?.tag || '')
const name        = computed(() => props.sample?.metadata?.name || tag.value)
const description = computed(() => props.sample?.metadata?.description || '')
const unit        = computed(() => props.sample?.unit || '')
const status      = computed(() => props.sample?.status || 'normal')

// 在线判断：最近 120s 内有数据视为在线；ts 为 0 或 null → 未知
const ONLINE_THRESHOLD_MS = 120_000
const isOnline = computed(() => {
  const ts = props.sample?.ts
  if (!ts) return null
  return (props.now - ts * 1000) < ONLINE_THRESHOLD_MS
})
const onlineLabel = computed(() => {
  if (isOnline.value === null) return '未知'
  return isOnline.value ? '在线' : '离线'
})
const onlineClass = computed(() => ({
  'instr-card__online--on':      isOnline.value === true,
  'instr-card__online--off':     isOnline.value === false,
  'instr-card__online--unknown': isOnline.value === null,
}))

const displayValue = computed(() => {
  const v = props.sample?.value
  if (v === null || v === undefined || Number.isNaN(v)) return '--'
  const abs = Math.abs(v)
  if (abs >= 100) return v.toFixed(1)
  if (abs >= 1)   return v.toFixed(2)
  return v.toFixed(3)
})

const statusClass = computed(() => ({
  'instr-card--warn':  status.value === 'warn_high'  || status.value === 'warn_low',
  'instr-card--alarm': status.value === 'alarm_high' || status.value === 'alarm_low',
}))

const title = computed(() => {
  const ts = props.sample?.ts ? new Date(props.sample.ts * 1000).toLocaleString() : '—'
  return `${tag.value}  ${name.value}\n${description.value ? description.value + '\n' : ''}最近更新: ${ts}`
})
</script>

<style scoped lang="scss">
.instr-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 14px;
  background: var(--iot-bg-card);
  border: 1px solid var(--iot-border-color);
  border-radius: var(--iot-radius-base);
  transition: background-color var(--iot-transition-fast), border-color var(--iot-transition-fast);
}

.instr-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.instr-card__name {
  font-size: var(--iot-font-size-sm);
  color: var(--iot-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
}

.instr-card__online {
  font-size: var(--iot-font-size-xs);
  padding: 1px 8px;
  border-radius: 20px;
  flex-shrink: 0;

  &--on      { background: var(--iot-color-success-bg); color: var(--iot-color-success); }
  &--off     { background: var(--iot-color-danger-bg); color: var(--iot-color-danger); }
  &--unknown { background: rgba(139, 123, 107, 0.10); color: var(--iot-text-secondary); }
}

.instr-card__desc {
  font-size: var(--iot-font-size-xs);
  color: var(--iot-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.instr-card__value-row {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-top: 2px;
}

.instr-card__value {
  font-size: var(--iot-font-size-xl);
  font-weight: 600;
  color: var(--iot-text-primary);
  font-variant-numeric: tabular-nums;
}

.instr-card__unit {
  font-size: var(--iot-font-size-xs);
  color: var(--iot-text-secondary);
}

.instr-card--warn {
  background: var(--iot-color-warning-bg);
  border-color: var(--iot-color-warning);
}

.instr-card--alarm {
  background: var(--iot-color-danger-bg);
  border-color: var(--iot-color-danger);
  animation: alarm-pulse 1.2s ease-in-out infinite;
  .instr-card__value { color: var(--iot-color-danger); }
}

@keyframes alarm-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(201, 74, 58, 0); }
  50%      { box-shadow: 0 0 0 4px rgba(201, 74, 58, 0.2); }
}
</style>
