<template>
  <div class="device-detail-view" v-loading="pageLoading">
    <!-- 顶部：返回 + 标题 -->
    <div class="iot-page-header">
      <div class="header-left">
        <el-button text :icon="ArrowLeft" @click="router.push('/devices')">{{ ls.t('common.backToList') }}</el-button>
        <div v-if="device" class="header-title-group">
          <span
            class="iot-status-dot iot-status-dot--lg"
            :class="device.is_online ? 'iot-status-dot--online' : 'iot-status-dot--offline'"
          ></span>
          <div>
            <h1 class="iot-page-title">{{ device.name }}</h1>
            <p class="iot-page-subtitle">{{ device.device_id }} / {{ device.device_type_info?.name || '--' }}</p>
          </div>
        </div>
      </div>
      <div v-if="device" class="header-right">
        <span
          class="iot-status-tag"
          :class="device.is_online ? 'iot-status-tag--online' : 'iot-status-tag--offline'"
        >
          {{ device.is_online ? ls.t('common.online') : ls.t('common.offline') }}
        </span>
      </div>
    </div>

    <template v-if="device">
      <!-- ========== 第一行：基本信息 + 最新状态 + 命令控制 ========== -->
      <div class="detail-row">
        <!-- 基本信息卡片 -->
        <div class="iot-card detail-info-card">
          <div class="iot-card__header">
            <span class="section-title">{{ ls.t('deviceDetail.basicInfo') }}</span>
          </div>
          <div class="iot-card__body">
            <div class="info-grid">
              <div class="info-item">
                <span class="info-item__label">{{ ls.t('deviceDetail.deviceId') }}</span>
                <span class="info-item__value mono">{{ device.device_id }}</span>
              </div>
              <div class="info-item">
                <span class="info-item__label">{{ ls.t('deviceDetail.deviceType') }}</span>
                <span class="info-item__value">{{ device.device_type_info?.name || '--' }}</span>
              </div>
              <div class="info-item">
                <span class="info-item__label">{{ ls.t('common.location') }}</span>
                <span class="info-item__value">{{ device.location || ls.t('common.unset') }}</span>
              </div>
              <div class="info-item">
                <span class="info-item__label">{{ ls.t('common.description') }}</span>
                <span class="info-item__value">{{ device.description || ls.t('common.none') }}</span>
              </div>
              <div class="info-item">
                <span class="info-item__label">{{ ls.t('deviceDetail.mqttStatusTopic') }}</span>
                <span class="info-item__value mono">{{ device.mqtt_topic_data || '--' }}</span>
              </div>
              <div class="info-item">
                <span class="info-item__label">{{ ls.t('deviceDetail.mqttControlTopic') }}</span>
                <span class="info-item__value mono">{{ device.mqtt_topic_control || '--' }}</span>
              </div>
              <div class="info-item">
                <span class="info-item__label">{{ ls.t('deviceDetail.lastSeen') }}</span>
                <span class="info-item__value">{{ device.last_seen ? formatTime(device.last_seen) : ls.t('common.never') }}</span>
              </div>
              <div class="info-item">
                <span class="info-item__label">{{ ls.t('deviceDetail.createdAt') }}</span>
                <span class="info-item__value">{{ formatTime(device.created_at) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 最新状态 + 命令控制 -->
        <div class="detail-side">
          <!-- 最新状态 -->
          <div class="iot-card">
            <div class="iot-card__header">
              <span class="section-title">{{ ls.t('deviceDetail.latestStatus') }}</span>
              <span v-if="device.latest_data" class="iot-text-secondary" style="font-size: 12px;">
                {{ formatTime(device.latest_data.timestamp) }}
              </span>
            </div>
            <div class="iot-card__body">
              <div v-if="fields.length" class="realtime-values">
                <div v-for="field in fields" :key="field" class="realtime-item">
                  <div class="iot-data-label">{{ field }}</div>
                  <div class="iot-data-value">{{ formatState(latestValue(field)) }}</div>
                </div>
              </div>
              <div v-else class="empty-hint">{{ ls.t('deviceDetail.noFields') }}</div>
            </div>
          </div>

          <!-- 命令控制（仅工作人员可见） -->
          <div v-if="isStaff" class="iot-card">
            <div class="iot-card__header">
              <span class="section-title">{{ ls.t('deviceDetail.commandControl') }}</span>
            </div>
            <div class="iot-card__body">
              <CommandPanel
                :commands="device.device_type_info?.commands || {}"
                :device-id="device.device_id"
                :send-fn="sendDeviceCommand"
                @command-sent="onCommandSent"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- ========== 第二行：状态记录表格（对齐 SensorStatusCollection 风格）========== -->
      <div class="iot-card iot-mt-lg">
        <div class="iot-card__header">
          <span class="section-title">{{ `${ls.t('deviceDetail.statusRecords')} (DeviceStatusCollection)` }}</span>
          <el-button :icon="Refresh" size="small" @click="fetchStatusRecords">{{ ls.t('common.refresh') }}</el-button>
        </div>
        <div class="iot-card__body" style="padding-top: 0;">
          <el-table :data="statusRecords" v-loading="statusLoading" size="small" stripe max-height="420">
            <el-table-column label="#" type="index" width="50" />
            <el-table-column :label="ls.t('deviceDetail.time')" width="180">
              <template #default="{ row }">{{ formatTime(row.timestamp) }}</template>
            </el-table-column>
            <el-table-column :label="ls.t('deviceDetail.event')" width="140">
              <template #default="{ row }">
                <el-tag size="small" :type="eventTagType(row.event_name)">
                  {{ row.event_name || '--' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column v-for="field in fields" :key="field" :label="field" min-width="110">
              <template #default="{ row }">
                {{ formatField(row.data?.[field]) }}
              </template>
            </el-table-column>
            <el-table-column :label="ls.t('deviceDetail.rawJson')" min-width="220">
              <template #default="{ row }">
                <span class="raw-json">{{ JSON.stringify(row.data) }}</span>
              </template>
            </el-table-column>
            <el-table-column :label="ls.t('deviceDetail.receivedAt')" width="180">
              <template #default="{ row }">{{ formatTime(row.received_at) }}</template>
            </el-table-column>
          </el-table>
          <div class="table-footer">
            {{ `${ls.t('common.total')} ${statusRecords.length} ${ls.t('common.records')}` }}
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Refresh } from '@element-plus/icons-vue'
import CommandPanel from '@/components/common/CommandPanel.vue'
import { useUserStore } from '@/stores/user'
import { useLocaleStore } from '@/stores/locale'
import { getDevice, getDeviceStatus, sendDeviceCommand } from '@/api/devices'
import { useWebSocket, buildWsUrl } from '@/composables/useWebSocket'

const ls = useLocaleStore()
const route = useRoute()
const userStore = useUserStore()
const isStaff = computed(() => userStore.userInfo?.is_staff === true)
const router = useRouter()

// ==================== 设备详情 ====================
const device = ref(null)
const pageLoading = ref(false)

const fields = computed(() => {
  return device.value?.device_type_info?.config_parameters || []
})

function latestValue(field) {
  const val = device.value?.latest_data?.data?.[field]
  if (val === undefined || val === null) return null
  return val
}

function formatState(val) {
  if (val === null || val === undefined) return '--'
  if (typeof val === 'boolean') return val ? ls.t('common.on') : ls.t('common.off')
  if (typeof val === 'number') return Number(val.toFixed(2))
  return String(val)
}

function formatField(val) {
  if (val === undefined || val === null) return '--'
  if (typeof val === 'number') return val.toFixed(2)
  if (typeof val === 'boolean') return val ? ls.t('common.yes') : ls.t('common.no')
  if (typeof val === 'object') return JSON.stringify(val)
  return String(val)
}

async function fetchDeviceDetail() {
  const deviceId = route.params.deviceId
  if (!deviceId) return
  pageLoading.value = true
  try {
    device.value = await getDevice(deviceId)
  } catch {
    ElMessage.error(ls.t('deviceDetail.fetchFailed'))
    device.value = null
  } finally {
    pageLoading.value = false
  }
}

// ==================== 状态记录 ====================
const statusRecords = ref([])
const statusLoading = ref(false)

async function fetchStatusRecords() {
  if (!device.value) return
  statusLoading.value = true
  try {
    const res = await getDeviceStatus(device.value.device_id, { limit: 100 })
    statusRecords.value = Array.isArray(res) ? res : (res.results || [])
  } catch {
    statusRecords.value = []
  } finally {
    statusLoading.value = false
  }
}

// ==================== 工具函数 ====================
function formatTime(str) {
  if (!str) return '--'
  const d = new Date(str)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function eventTagType(name) {
  if (!name) return 'info'
  if (name.includes('online') || name.includes('enable') || name.includes('start')) return 'success'
  if (name.includes('offline') || name.includes('disable') || name.includes('stop')) return 'danger'
  return 'info'
}

function onCommandSent() {
  ElMessage.success(ls.t('common.commandSent'))
  // 命令效果由设备响应的 status 上报驱动 WS 推送；不再轮询拉详情
}

// ==================== WebSocket 实时推送 ====================
function onDeviceStatus(data) {
  if (!device.value || data?.device_id !== device.value.device_id) return
  const tsIso = data.timestamp ? new Date(data.timestamp * 1000).toISOString() : null
  const receivedIso = data.received_at ? new Date(data.received_at * 1000).toISOString() : tsIso
  // 更新最新状态 + 顶部"在线"标识
  device.value.latest_data = {
    data: data.status,
    timestamp: tsIso,
    received_at: receivedIso,
  }
  device.value.is_online = !!data.is_online
  if (data.last_seen) {
    device.value.last_seen = new Date(data.last_seen * 1000).toISOString()
  }
  // 状态记录表顶部插入
  statusRecords.value = [
    {
      data: data.status,
      event_name: data.event,
      timestamp: tsIso,
      received_at: receivedIso,
    },
    ...statusRecords.value,
  ].slice(0, 200)
}

const ws = useWebSocket(
  () => {
    const id = device.value?.device_id
    return id ? buildWsUrl(`/ws/devices/${encodeURIComponent(id)}/`) : ''
  },
  { 'device.status': onDeviceStatus },
  { autoStart: false },
)

// ==================== 初始化 ====================
onMounted(async () => {
  await fetchDeviceDetail()
  if (device.value) {
    fetchStatusRecords()
    ws.start()
  }
})
</script>

<style scoped>
.header-left {
  display: flex;
  align-items: center;
  gap: var(--iot-spacing-md);
}

.header-title-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--iot-spacing-sm);
}

.section-title {
  font-weight: 600;
  font-size: var(--iot-font-size-md);
}

/* 第一行两列布局 */
.detail-row {
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: var(--iot-spacing-md);
  align-items: start;
}

.detail-side {
  display: flex;
  flex-direction: column;
  gap: var(--iot-spacing-md);
}

/* 基本信息网格 */
.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px 0;
  border-bottom: 1px solid var(--iot-border-color-lighter);
}

.info-item__label {
  font-size: var(--iot-font-size-xs);
  color: var(--iot-text-secondary);
}

.info-item__value {
  font-size: var(--iot-font-size-sm);
  color: var(--iot-text-primary);
  word-break: break-all;
}

.info-item__value.mono {
  font-family: 'Courier New', monospace;
  font-size: 12px;
}

/* 最新状态大字 */
.realtime-values {
  display: flex;
  flex-wrap: wrap;
  gap: var(--iot-spacing-lg);
}

.realtime-item {
  min-width: 80px;
}

.realtime-item .iot-data-value {
  font-size: var(--iot-font-size-data);
}

/* 原始 JSON */
.raw-json {
  font-size: 11px;
  color: var(--iot-text-secondary);
  font-family: 'Courier New', monospace;
  word-break: break-all;
}

/* 表格底部 */
.table-footer {
  padding: 8px 0;
  text-align: right;
  font-size: var(--iot-font-size-xs);
  color: var(--iot-text-secondary);
}

.empty-hint {
  text-align: center;
  color: var(--iot-text-secondary);
  padding: 16px;
  font-size: var(--iot-font-size-sm);
}

@media (max-width: 1024px) {
  .detail-row {
    grid-template-columns: 1fr;
  }
  .info-grid {
    grid-template-columns: 1fr;
  }
}
</style>
