<template>
  <div class="instr-node" :class="statusClass" :title="tooltip">
    <Handle id="left"   type="source" :position="Position.Left" />
    <Handle id="right"  type="source" :position="Position.Right" />
    <Handle id="top"    type="source" :position="Position.Top" />
    <Handle id="bottom" type="source" :position="Position.Bottom" />

    <!-- 标题行：名称 + 在线状态 -->
    <div class="instr-node__header">
      <span class="instr-node__name">{{ data.label || '未命名' }}</span>
      <span v-if="binding" class="instr-node__online" :class="onlineClass">{{ onlineLabel }}</span>
      <span v-else class="instr-node__unbound">未绑定</span>
    </div>

    <!-- 数值 + 单位 -->
    <div class="instr-node__value-row">
      <span class="instr-node__value">{{ displayValue }}</span>
      <span v-if="unit" class="instr-node__unit">{{ unit }}</span>
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
const sample  = computed(() => plantStore.findByBinding(binding.value))

const unit = computed(() => sample.value?.unit || props.data?.unit || '')

const displayValue = computed(() => {
  const v = sample.value?.value
  if (v === null || v === undefined || Number.isNaN(v)) return '--'
  const abs = Math.abs(v)
  if (abs >= 100) return v.toFixed(1)
  if (abs >= 1)   return v.toFixed(2)
  return v.toFixed(3)
})

// 在线判断：120s 内有数据 = 在线
const ONLINE_MS = 120_000
const isOnline = computed(() => {
  const ts = sample.value?.ts
  if (!ts) return null
  return (Date.now() - ts * 1000) < ONLINE_MS
})
const onlineLabel = computed(() => {
  if (isOnline.value === null) return '未知'
  return isOnline.value ? '在线' : '离线'
})
const onlineClass = computed(() => ({
  'instr-node__online--on':      isOnline.value === true,
  'instr-node__online--off':     isOnline.value === false,
  'instr-node__online--unknown': isOnline.value === null,
}))

const status = computed(() => sample.value?.status || 'normal')
const statusClass = computed(() => ({
  'instr-node--warn':    status.value === 'warn_high'  || status.value === 'warn_low',
  'instr-node--alarm':   status.value === 'alarm_high' || status.value === 'alarm_low',
  'instr-node--unbound': !binding.value,
}))

const tooltip = computed(() => {
  const id = binding.value || '(未绑定)'
  const ts = sample.value?.ts ? new Date(sample.value.ts * 1000).toLocaleTimeString() : '—'
  return `${props.data?.label || ''}\n绑定: ${id}\n最近: ${ts}`
})
</script>

<style scoped>
.instr-node {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  background: #fafaf7;
  border: 1px solid #2a2a2a;
  border-radius: 4px;
  font-family: 'JetBrains Mono', 'SFMono-Regular', Consolas, monospace;
  width: 160px;
  transition: background var(--iot-transition-fast), border-color var(--iot-transition-fast);
}

.instr-node__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.instr-node__name {
  font-size: 11px;
  color: #555;
  font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
}

.instr-node__online {
  font-size: 10px;
  font-family: -apple-system, 'PingFang SC', sans-serif;
  padding: 1px 5px;
  border-radius: 10px;
  flex-shrink: 0;
}
.instr-node__online--on      { background: #e6f4ea; color: #2e7d4f; }
.instr-node__online--off     { background: #fdecea; color: #c0392b; }
.instr-node__online--unknown { background: #f0f0f0; color: #999; }

.instr-node__unbound {
  font-size: 10px;
  color: #999;
  font-family: -apple-system, sans-serif;
  flex-shrink: 0;
}

.instr-node__value-row {
  display: flex;
  align-items: baseline;
  gap: 5px;
  margin-top: 2px;
}

.instr-node__value {
  font-size: 20px;
  font-weight: 600;
  color: #2a2a2a;
  font-variant-numeric: tabular-nums;
}

.instr-node__unit {
  font-size: 11px;
  color: #888;
}

/* 报警态 */
.instr-node--warn {
  background: #fef9e7;
  border-color: #c9a227;
}

.instr-node--alarm {
  background: #fdecea;
  border-color: #d14b3b;
  animation: alarm-pulse 1.2s ease-in-out infinite;
}
.instr-node--alarm .instr-node__value { color: #c0392b; }

.instr-node--unbound {
  border-style: dashed;
  border-color: #bbb;
}

@keyframes alarm-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(209, 75, 59, 0); }
  50%      { box-shadow: 0 0 0 4px rgba(209, 75, 59, 0.25); }
}
</style>
