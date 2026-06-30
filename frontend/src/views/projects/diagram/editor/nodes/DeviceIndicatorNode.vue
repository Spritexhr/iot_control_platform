<template>
  <div class="device-node" :class="{ 'device-node--unbound': !binding }" :title="tooltip">
    <Handle id="left" type="source" :position="Position.Left" />
    <Handle id="right" type="source" :position="Position.Right" />
    <Handle id="top" type="source" :position="Position.Top" />
    <Handle id="bottom" type="source" :position="Position.Bottom" />

    <div class="device-node__header">
      <span class="device-node__name">{{ data.label || '设备变量' }}</span>
      <span v-if="binding" class="device-node__online" :class="onlineClass">{{ onlineLabel }}</span>
      <span v-else class="device-node__unbound-label">未绑定</span>
    </div>

    <div class="device-node__key">{{ dataKey || '未选择变量' }}</div>
    <div class="device-node__value-row">
      <span class="device-node__value">{{ displayValue }}</span>
      <span v-if="data.unit" class="device-node__unit">{{ data.unit }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import { useProjectStore } from '@/stores/project'

const props = defineProps({
  id: { type: String, required: true },
  data: { type: Object, required: true },
})

const projectStore = useProjectStore()
const binding = computed(() => props.data?.binding?.id || '')
const device = computed(() => projectStore.findDevice(binding.value))
const dataKey = computed(() => props.data?.dataKey || '')

function formatValue(value) {
  if (value === null || value === undefined || value === '') return '--'
  if (typeof value === 'boolean') return value ? 'ON' : 'OFF'
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) return '--'
    const abs = Math.abs(value)
    if (abs >= 100) return value.toFixed(1)
    if (abs >= 1) return value.toFixed(2)
    return value.toFixed(3)
  }
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

const displayValue = computed(() => formatValue(device.value?.status?.[dataKey.value]))
const isOnline = computed(() => device.value?.is_online ?? null)
const onlineLabel = computed(() => {
  if (isOnline.value === null) return '未知'
  return isOnline.value ? '在线' : '离线'
})
const onlineClass = computed(() => ({
  'device-node__online--on': isOnline.value === true,
  'device-node__online--off': isOnline.value === false,
  'device-node__online--unknown': isOnline.value === null,
}))

const tooltip = computed(() => {
  const id = binding.value || '(未绑定)'
  const ts = device.value?.ts ? new Date(device.value.ts * 1000).toLocaleTimeString() : '—'
  return `设备: ${id}\n变量: ${dataKey.value || '(未选择)'}\n最近: ${ts}`
})
</script>

<style scoped>
.device-node {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 160px;
  padding: 10px 12px;
  background: #fafaf7;
  border: 1px solid #2a2a2a;
  border-radius: 4px;
  font-family: 'JetBrains Mono', 'SFMono-Regular', Consolas, monospace;
}

.device-node--unbound { border-style: dashed; border-color: #bbb; }
.device-node__header { display: flex; align-items: center; justify-content: space-between; gap: 6px; }
.device-node__name {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  color: #555;
  font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.device-node__online, .device-node__unbound-label {
  flex-shrink: 0;
  padding: 1px 5px;
  border-radius: 10px;
  font-family: -apple-system, 'PingFang SC', sans-serif;
  font-size: 10px;
}
.device-node__unbound-label { color: #999; }
.device-node__online--on { color: #2e7d4f; background: #e6f4ea; }
.device-node__online--off { color: #c0392b; background: #fdecea; }
.device-node__online--unknown { color: #999; background: #f0f0f0; }
.device-node__key { color: #999; font-size: 10px; }
.device-node__value-row { display: flex; align-items: baseline; gap: 5px; margin-top: 2px; }
.device-node__value {
  max-width: 132px;
  overflow: hidden;
  color: #2a2a2a;
  font-size: 20px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.device-node__unit { color: #888; font-size: 11px; }
</style>
