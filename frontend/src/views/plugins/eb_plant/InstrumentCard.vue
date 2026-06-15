<template>
  <div class="instr-card" :class="statusClass" :title="title">
    <!-- 标题行：名称 + 在线状态 -->
    <div class="instr-card__header">
      <span class="instr-card__name">{{ name }}</span>
      <span class="instr-card__online" :class="onlineClass">{{ onlineLabel }}</span>
    </div>

    <!-- 描述（有值才显示） -->
    <div v-if="description" class="instr-card__desc">{{ description }}</div>

    <!-- 数值行 -->
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
  if (!ts) return null                        // null = 从未上报
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
  background: #fafaf7;
  border: 1px solid #2a2a2a;
  border-radius: 4px;
  transition: background-color 0.2s, border-color 0.2s;
  font-family: 'JetBrains Mono', 'SFMono-Regular', Consolas, monospace;
}

.instr-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.instr-card__name {
  font-size: 12px;
  color: #555;
  font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
}

.instr-card__online {
  font-size: 10px;
  font-family: -apple-system, 'PingFang SC', sans-serif;
  padding: 1px 6px;
  border-radius: 10px;
  flex-shrink: 0;

  &--on      { background: #e6f4ea; color: #2e7d4f; }
  &--off     { background: #fdecea; color: #c0392b; }
  &--unknown { background: #f0f0f0; color: #999; }
}

.instr-card__desc {
  font-size: 11px;
  color: #888;
  font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
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
  font-size: 24px;
  font-weight: 600;
  color: #2a2a2a;
  font-variant-numeric: tabular-nums;
}

.instr-card__unit {
  font-size: 12px;
  color: #888;
}

// ============ 报警态 ============
.instr-card--warn {
  background: #fef9e7;
  border-color: #c9a227;
}

.instr-card--alarm {
  background: #fdecea;
  border-color: #d14b3b;
  animation: alarm-pulse 1.2s ease-in-out infinite;
  .instr-card__value { color: #c0392b; }
}

@keyframes alarm-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(209, 75, 59, 0); }
  50%      { box-shadow: 0 0 0 4px rgba(209, 75, 59, 0.2); }
}
</style>
