<template>
  <div class="dev-card" :class="{ 'dev-card--offline': isOnline === false }" :title="title">
    <div class="dev-card__header">
      <span class="dev-card__badge">DEV</span>
      <span class="dev-card__name">{{ name }}</span>
      <span class="dev-card__online" :class="onlineClass">{{ onlineLabel }}</span>
    </div>

    <div class="dev-card__status">
      <div v-if="statusRows.length === 0" class="dev-card__status-empty">暂无状态上报</div>
      <div v-for="row in statusRows" :key="row.key" class="dev-card__status-row">
        <span class="dev-card__status-key">{{ row.key }}</span>
        <span
          v-if="row.type === 'bool'"
          class="dev-card__pill"
          :class="row.value ? 'dev-card__pill--on' : 'dev-card__pill--off'"
        >{{ row.value ? '开' : '关' }}</span>
        <span v-else class="dev-card__status-val">{{ row.display }}</span>
      </div>
    </div>

    <!-- 命令区：仅管理员可见且该设备有命令时显示 -->
    <div v-if="canControl && hasCommands" class="dev-card__commands">
      <div class="dev-card__commands-title">命令控制</div>
      <CommandPanel
        :commands="binding.commands || {}"
        :device-id="binding.device_id"
        :send-fn="sendDeviceCommand"
        @command-sent="onCommandSent"
        @command-failed="onCommandFailed"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ElMessage } from 'element-plus'

import CommandPanel from '@/components/common/CommandPanel.vue'
import { sendDeviceCommand } from '@/api/devices'

const props = defineProps({
  binding: { type: Object, required: true },
  state: { type: Object, default: null },
  now: { type: Number, default: () => Date.now() },
  canControl: { type: Boolean, default: false },
})

const name = computed(() => props.binding?.tag || props.binding?.device_name || props.binding?.device_id || '')

const hasCommands = computed(() => {
  const c = props.binding?.commands
  return c && typeof c === 'object' && Object.keys(c).length > 0
})

const ONLINE_THRESHOLD_MS = 180_000
const lastTs = computed(() => {
  const s = props.state
  if (!s) return null
  const best = Math.max(s.last_seen || 0, s.ts || 0)
  return best > 0 ? best : null
})
const isOnline = computed(() => {
  if (lastTs.value) return (props.now - lastTs.value * 1000) < ONLINE_THRESHOLD_MS
  if (props.state && typeof props.state.is_online === 'boolean') return props.state.is_online
  return null
})
const onlineLabel = computed(() => {
  if (isOnline.value === null) return '未知'
  return isOnline.value ? '在线' : '离线'
})
const onlineClass = computed(() => ({
  'dev-card__online--on': isOnline.value === true,
  'dev-card__online--off': isOnline.value === false,
  'dev-card__online--unknown': isOnline.value === null,
}))

function fmtNumber(v) {
  if (!Number.isFinite(v)) return String(v)
  if (Number.isInteger(v)) return String(v)
  const abs = Math.abs(v)
  if (abs >= 100) return v.toFixed(1)
  if (abs >= 1) return v.toFixed(2)
  return v.toFixed(3)
}

const statusRows = computed(() => {
  const st = props.state?.status
  if (!st || typeof st !== 'object') return []
  return Object.entries(st).map(([key, value]) => {
    if (typeof value === 'boolean') return { key, type: 'bool', value }
    if (typeof value === 'number') return { key, type: 'num', value, display: fmtNumber(value) }
    if (value !== null && typeof value === 'object') return { key, type: 'str', value, display: JSON.stringify(value) }
    return { key, type: 'str', value, display: value === null || value === undefined ? '--' : String(value) }
  })
})

const title = computed(() => {
  const ts = lastTs.value ? new Date(lastTs.value * 1000).toLocaleString() : '—'
  return `${props.binding?.tag || ''}  ${props.binding?.device_name || ''}\n最近更新: ${ts}`
})

function onCommandSent({ command }) {
  ElMessage.success(`命令已下发: ${command}`)
}
function onCommandFailed({ command }) {
  ElMessage.error(`命令失败: ${command}`)
}
</script>

<style scoped lang="scss">
.dev-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px 14px;
  background: #f3f6fb;
  border: 1px solid #2a3a55;
  border-left: 3px solid #2a3a55;
  border-radius: 4px;
  transition: background-color 0.2s, border-color 0.2s;
  font-family: 'JetBrains Mono', 'SFMono-Regular', Consolas, monospace;
}

.dev-card--offline {
  background: #f6f6f4;
  border-color: #999;
  border-left-color: #999;
}

.dev-card__header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dev-card__badge {
  font-size: 9px;
  letter-spacing: 1px;
  padding: 1px 5px;
  background: #2a3a55;
  color: #f3f6fb;
  border-radius: 3px;
  flex-shrink: 0;
}

.dev-card__name {
  font-size: 12px;
  color: #2a3a55;
  font-weight: 600;
  font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
}

.dev-card__online {
  font-size: 10px;
  font-family: -apple-system, 'PingFang SC', sans-serif;
  padding: 1px 6px;
  border-radius: 10px;
  flex-shrink: 0;

  &--on { background: #e6f4ea; color: #2e7d4f; }
  &--off { background: #fdecea; color: #c0392b; }
  &--unknown { background: #f0f0f0; color: #999; }
}

.dev-card__status {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.dev-card__status-empty {
  font-size: 11px;
  color: #aaa;
  font-family: -apple-system, 'PingFang SC', sans-serif;
}

.dev-card__status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.dev-card__status-key {
  font-size: 11px;
  color: #6b7896;
  font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.dev-card__status-val {
  font-size: 14px;
  font-weight: 600;
  color: #1f2a44;
  font-variant-numeric: tabular-nums;
}

.dev-card__pill {
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 10px;
  font-family: -apple-system, 'PingFang SC', sans-serif;

  &--on { background: #e6f4ea; color: #2e7d4f; }
  &--off { background: #eceff4; color: #8a93a6; }
}

.dev-card__commands {
  margin-top: 4px;
  padding-top: 6px;
  border-top: 1px dashed #c7d0e0;
}

.dev-card__commands-title {
  font-size: 10px;
  letter-spacing: 0.5px;
  color: #8a93a6;
  font-family: -apple-system, 'PingFang SC', sans-serif;
  margin-bottom: 2px;
}
</style>
