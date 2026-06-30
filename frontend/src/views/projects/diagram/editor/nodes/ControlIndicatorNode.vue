<template>
  <div class="control-node" :class="stateClass" :title="tooltip">
    <Handle id="left" type="source" :position="Position.Left" />
    <Handle id="right" type="source" :position="Position.Right" />
    <Handle id="top" type="source" :position="Position.Top" />
    <Handle id="bottom" type="source" :position="Position.Bottom" />

    <div class="control-node__header">
      <span class="control-node__title">{{ data.label || '自动化控制' }}</span>
      <span class="control-node__type">{{ typeLabel }}</span>
    </div>
    <div class="control-node__name">{{ control?.name || '未绑定控制' }}</div>
    <div class="control-node__status">
      <span class="control-node__dot"></span>
      <span>{{ statusLabel }}</span>
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
const binding = computed(() => props.data?.binding || { kind: 'none', id: '' })
const control = computed(() => projectStore.findAutomationControl(binding.value.kind, binding.value.id))

const typeLabel = computed(() => {
  if (binding.value.kind === 'automation_rule') return '脚本'
  if (binding.value.kind === 'control_scheme') {
    return control.value?.control_type_display || String(control.value?.control_type || 'PI/PID').toUpperCase()
  }
  return '未绑定'
})

const rawStatus = computed(() => {
  if (binding.value.kind === 'automation_rule') return control.value?.process_status || 'idle'
  if (binding.value.kind === 'control_scheme') return control.value?.status || 'idle'
  return 'unbound'
})

const STATUS_LABELS = {
  running: '运行中',
  idle: '未启动',
  stopped_by_user: '已停止',
  error_stopped: '错误停止',
  error: '错误停止',
  unbound: '未绑定',
}
const statusLabel = computed(() => control.value?.status_display || STATUS_LABELS[rawStatus.value] || rawStatus.value)
const stateClass = computed(() => ({
  'control-node--running': rawStatus.value === 'running',
  'control-node--error': rawStatus.value === 'error' || rawStatus.value === 'error_stopped',
  'control-node--unbound': !binding.value.id,
}))
const tooltip = computed(() => {
  const error = control.value?.error_message ? `\n错误: ${control.value.error_message}` : ''
  return `${typeLabel.value}: ${control.value?.name || '(未绑定)'}\n状态: ${statusLabel.value}${error}`
})
</script>

<style scoped>
.control-node {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 170px;
  padding: 10px 12px;
  background: #fafaf7;
  border: 1px solid #2a2a2a;
  border-radius: 4px;
  font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}
.control-node__header { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.control-node__title { color: #777; font-size: 10px; }
.control-node__type {
  max-width: 88px;
  overflow: hidden;
  padding: 1px 5px;
  border-radius: 3px;
  color: #8a552e;
  background: #f5e6d8;
  font-size: 9px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.control-node__name {
  overflow: hidden;
  color: #2a2a2a;
  font-size: 13px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.control-node__status { display: flex; align-items: center; gap: 6px; color: #777; font-size: 11px; }
.control-node__dot { width: 7px; height: 7px; border-radius: 50%; background: #aaa; }
.control-node--running { border-color: #4d9b68; background: #f3faf5; }
.control-node--running .control-node__status { color: #2e7d4f; }
.control-node--running .control-node__dot { background: #4d9b68; box-shadow: 0 0 0 3px rgba(77, 155, 104, 0.14); }
.control-node--error { border-color: #d14b3b; background: #fdecea; }
.control-node--error .control-node__status { color: #c0392b; }
.control-node--error .control-node__dot { background: #d14b3b; }
.control-node--unbound { border-style: dashed; border-color: #bbb; }
</style>
