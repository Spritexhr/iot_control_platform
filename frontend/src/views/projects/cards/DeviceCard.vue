<template>
  <div class="dev-card" :class="{ 'dev-card--offline': isOnline === false }" :title="title">
    <!-- 离线态高斯模糊与去色遮罩层 -->
    <div v-if="isOnline === false" class="dev-card__offline-overlay">
      <span class="offline-badge">已离线</span>
    </div>

    <div class="dev-card__header">
      <span class="dev-card__badge">DEV</span>
      <span class="dev-card__name">{{ name }}</span>
      <span class="dev-card__online" :class="onlineClass">{{ onlineLabel }}</span>
    </div>

    <!-- 运行指标面板 -->
    <div class="dev-card__status">
      <div v-if="statusRows.length === 0" class="dev-card__status-empty">暂无数据上报</div>
      <div v-for="row in statusRows" :key="row.key" class="dev-card__status-row">
        <span class="dev-card__status-key">{{ row.key }}</span>
        <span
          v-if="row.type === 'bool'"
          class="dev-card__pill"
          :class="row.value ? 'dev-card__pill--on' : 'dev-card__pill--off'"
        >{{ row.value ? 'ON' : 'OFF' }}</span>
        <span v-else class="dev-card__status-val">{{ row.display }}</span>
      </div>
    </div>

    <!-- 命令区：仅管理员可见且该设备有命令时显示 -->
    <div v-if="canControl && hasCommands" class="dev-card__commands">
      <div class="dev-card__commands-title">远程命令控制</div>
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
  gap: 10px;
  padding: 14px 16px;
  background: var(--iot-bg-card);
  border: 1px solid var(--iot-border-color);
  border-left: 3px solid var(--iot-color-primary);
  border-radius: var(--iot-radius-base);
  transition: all var(--iot-transition-base);
  position: relative;
  overflow: hidden;

  &:hover {
    box-shadow: var(--iot-shadow-sm);
    border-color: var(--iot-color-primary-light);
  }
}

.dev-card--offline {
  border-left-color: var(--iot-text-placeholder);
}

/* 离线态遮罩层 */
.dev-card__offline-overlay {
  position: absolute;
  inset: 0;
  background: rgba(26, 23, 20, 0.4);
  backdrop-filter: blur(1.5px) grayscale(100%);
  -webkit-backdrop-filter: blur(1.5px) grayscale(100%);
  z-index: 5;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--iot-radius-base);
  pointer-events: all;
}

.offline-badge {
  background: var(--iot-color-danger);
  color: var(--iot-text-inverse);
  font-size: 11px;
  font-weight: 600;
  padding: 4px 12px;
  border-radius: 20px;
  box-shadow: var(--iot-shadow-sm);
  letter-spacing: 0.5px;
  animation: offline-badge-pulse 1.8s infinite alternate;
}

.dev-card__header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dev-card__badge {
  font-size: 9px;
  letter-spacing: 1px;
  padding: 1px 6px;
  background: var(--iot-color-primary-bg);
  color: var(--iot-color-primary);
  border-radius: var(--iot-radius-sm);
  flex-shrink: 0;
  font-weight: 600;
}

.dev-card__name {
  font-size: var(--iot-font-size-sm);
  color: var(--iot-text-primary);
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
}

.dev-card__online {
  font-size: var(--iot-font-size-xs);
  padding: 1px 8px;
  border-radius: 20px;
  flex-shrink: 0;
  font-weight: 500;

  &--on { background: var(--iot-color-success-bg); color: var(--iot-color-success); }
  &--off { background: var(--iot-color-danger-bg); color: var(--iot-color-danger); }
  &--unknown { background: rgba(139, 123, 107, 0.10); color: var(--iot-text-secondary); }
}

/* 运行指标面板 */
.dev-card__status {
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: var(--iot-border-color-lighter);
  padding: 8px 12px;
  border-radius: var(--iot-radius-sm);
  border: 1px solid var(--iot-border-color-light);
}

.dev-card__status-empty {
  font-size: var(--iot-font-size-xs);
  color: var(--iot-text-placeholder);
  text-align: center;
  padding: 4px 0;
}

.dev-card__status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.dev-card__status-key {
  font-size: var(--iot-font-size-xs);
  color: var(--iot-text-secondary);
  font-weight: 500;
}

.dev-card__status-val {
  font-size: var(--iot-font-size-sm);
  font-weight: 600;
  color: var(--iot-text-primary);
  font-variant-numeric: tabular-nums;
  font-family: var(--iot-font-mono, monospace);
}

.dev-card__pill {
  font-size: 10px;
  font-weight: 600;
  padding: 1px 8px;
  border-radius: 20px;
  line-height: 1.4;

  &--on { background: var(--iot-color-success-bg); color: var(--iot-color-success); }
  &--off { background: rgba(139, 123, 107, 0.10); color: var(--iot-text-secondary); }
}

/* 命令区 */
.dev-card__commands {
  margin-top: 4px;
  padding-top: 8px;
  border-top: 1px dashed var(--iot-border-color-light);
}

.dev-card__commands-title {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.5px;
  color: var(--iot-text-secondary);
  margin-bottom: 4px;
  text-transform: uppercase;
}

@keyframes offline-badge-pulse {
  from {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(201, 74, 58, 0.4);
  }
  to {
    transform: scale(1.03);
    box-shadow: 0 0 10px 2px rgba(201, 74, 58, 0.15);
  }
}
</style>

