<template>
  <div class="sensor-detail-view" v-loading="pageLoading">
    <!-- 顶部：返回 + 标题 -->
    <div class="iot-page-header">
      <div class="header-left">
        <el-button text :icon="ArrowLeft" @click="router.push('/sensors')">{{ ls.t('common.backToList') }}</el-button>
        <div v-if="sensor" class="header-title-group">
          <span
            class="iot-status-dot iot-status-dot--lg"
            :class="sensor.is_online ? 'iot-status-dot--online' : 'iot-status-dot--offline'"
          ></span>
          <div>
            <h1 class="iot-page-title">{{ sensor.name }}</h1>
            <p class="iot-page-subtitle">{{ sensor.sensor_id }} / {{ sensor.sensor_type_info?.name || '--' }}</p>
          </div>
        </div>
      </div>
      <div v-if="sensor" class="header-right">
        <span
          class="iot-status-tag"
          :class="sensor.is_online ? 'iot-status-tag--online' : 'iot-status-tag--offline'"
        >
          {{ sensor.is_online ? ls.t('common.online') : ls.t('common.offline') }}
        </span>
      </div>
    </div>

    <template v-if="sensor">
      <!-- ========== 第一行：基本信息 + 实时数据 ========== -->
      <div class="detail-row">
        <!-- 基本信息卡片 -->
        <div class="iot-card detail-info-card">
          <div class="iot-card__header">
            <span class="section-title">{{ ls.t('sensorDetail.basicInfo') }}</span>
            <div v-if="isStaff" class="info-edit-btns">
              <template v-if="!isEditing">
                <el-button size="small" @click="startEdit">编辑</el-button>
              </template>
              <template v-else>
                <el-button size="small" type="primary" :loading="saving" @click="saveEdit">保存</el-button>
                <el-button size="small" @click="cancelEdit">取消</el-button>
              </template>
            </div>
          </div>
          <div class="iot-card__body">
            <div class="info-grid">
              <div class="info-item">
                <span class="info-item__label">{{ ls.t('sensorDetail.sensorId') }}</span>
                <span class="info-item__value mono">{{ sensor.sensor_id }}</span>
              </div>
              <div class="info-item">
                <span class="info-item__label">{{ ls.t('sensorDetail.sensorType') }}</span>
                <span class="info-item__value">{{ sensor.sensor_type_info?.name || '--' }}</span>
              </div>
              <div class="info-item">
                <span class="info-item__label">{{ ls.t('common.location') }}</span>
                <span v-if="!isEditing" class="info-item__value">{{ sensor.location || ls.t('common.unset') }}</span>
                <el-input v-else v-model="editForm.location" size="small" placeholder="未设置" clearable />
              </div>
              <div class="info-item">
                <span class="info-item__label">{{ ls.t('common.description') }}</span>
                <span v-if="!isEditing" class="info-item__value">{{ sensor.description || ls.t('common.none') }}</span>
                <el-input v-else v-model="editForm.description" size="small" placeholder="无" clearable />
              </div>
              <div class="info-item info-item--full">
                <span class="info-item__label">名称</span>
                <span v-if="!isEditing" class="info-item__value">{{ sensor.name }}</span>
                <el-input v-else v-model="editForm.name" size="small" />
              </div>
              <div class="info-item">
                <span class="info-item__label">{{ ls.t('sensorDetail.mqttDataTopic') }}</span>
                <span class="info-item__value mono">{{ sensor.mqtt_topic_data || '--' }}</span>
              </div>
              <div class="info-item">
                <span class="info-item__label">{{ ls.t('sensorDetail.mqttControlTopic') }}</span>
                <span class="info-item__value mono">{{ sensor.mqtt_topic_control || '--' }}</span>
              </div>
              <div class="info-item">
                <span class="info-item__label">{{ ls.t('sensorDetail.lastSeen') }}</span>
                <span class="info-item__value">{{ sensor.last_seen ? formatTime(sensor.last_seen) : ls.t('common.never') }}</span>
              </div>
              <div class="info-item">
                <span class="info-item__label">{{ ls.t('sensorDetail.createdAt') }}</span>
                <span class="info-item__value">{{ formatTime(sensor.created_at) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 实时数据 + 命令控制卡片 -->
        <div class="detail-side">
          <!-- 最新数据值 -->
          <div class="iot-card">
            <div class="iot-card__header">
              <span class="section-title">{{ ls.t('sensorDetail.latestData') }}</span>
              <span v-if="sensor.latest_data" class="iot-text-secondary" style="font-size: 12px;">
                {{ formatTime(sensor.latest_data.timestamp) }}
              </span>
            </div>
            <div class="iot-card__body">
              <div v-if="dataFields.length" class="realtime-values">
                <div v-for="field in dataFields" :key="field" class="realtime-item">
                  <div class="iot-data-label">{{ field }}</div>
                  <div class="iot-data-value">{{ latestValue(field) ?? '--' }}</div>
                </div>
              </div>
              <div v-else class="empty-hint">{{ ls.t('sensorDetail.noDataFields') }}</div>
            </div>
          </div>

          <!-- 命令控制（仅工作人员可见） -->
          <div v-if="isStaff" class="iot-card">
            <div class="iot-card__header">
              <span class="section-title">{{ ls.t('sensorDetail.commandControl') }}</span>
            </div>
            <div class="iot-card__body">
              <CommandPanel
                :commands="sensor.sensor_type_info?.commands || {}"
                :device-id="sensor.sensor_id"
                :send-fn="sendSensorCommand"
                @command-sent="onCommandSent"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- ========== 第二行：数据记录表格 ========== -->
      <div class="iot-card iot-mt-lg">
        <div class="iot-card__header">
          <span class="section-title">{{ ls.t('sensorDetail.dataRecords') }} (SensorData)</span>
          <div class="toolbar">
            <el-radio-group v-model="dataHours" size="small" @change="fetchDataRecords">
              <el-radio-button :value="1">{{ ls.t('common.hour1') }}</el-radio-button>
              <el-radio-button :value="6">{{ ls.t('common.hour6') }}</el-radio-button>
              <el-radio-button :value="24">{{ ls.t('common.hour24') }}</el-radio-button>
              <el-radio-button :value="168">{{ ls.t('common.day7') }}</el-radio-button>
            </el-radio-group>
            <el-button :icon="Refresh" size="small" @click="fetchDataRecords">{{ ls.t('common.refresh') }}</el-button>
          </div>
        </div>
        <div class="iot-card__body" style="padding-top: 0;">
          <el-table :data="dataRecords" v-loading="dataLoading" size="small" stripe max-height="420">
            <el-table-column label="#" type="index" width="50" />
            <el-table-column :label="ls.t('sensorDetail.collectTime')" width="180">
              <template #default="{ row }">{{ formatTime(row.timestamp) }}</template>
            </el-table-column>
            <el-table-column v-for="field in dataFields" :key="field" :label="field" min-width="110">
              <template #default="{ row }">
                {{ formatField(row.data?.[field]) }}
              </template>
            </el-table-column>
            <el-table-column :label="ls.t('sensorDetail.rawJson')" min-width="220">
              <template #default="{ row }">
                <span class="raw-json">{{ JSON.stringify(row.data) }}</span>
              </template>
            </el-table-column>
            <el-table-column :label="ls.t('sensorDetail.receivedAt')" width="180">
              <template #default="{ row }">{{ formatTime(row.received_at) }}</template>
            </el-table-column>
          </el-table>
          <div class="table-footer">
            {{ `${ls.t('common.total')} ${dataRecords.length} ${ls.t('common.records')}` }}
          </div>
        </div>
      </div>

      <!-- ========== 第三行：状态记录表格 ========== -->
      <div class="iot-card iot-mt-lg">
        <div class="iot-card__header">
          <span class="section-title">{{ `${ls.t('sensorDetail.statusRecords')} (SensorStatusCollection)` }}</span>
          <el-button :icon="Refresh" size="small" @click="fetchStatusRecords">{{ ls.t('common.refresh') }}</el-button>
        </div>
        <div class="iot-card__body" style="padding-top: 0;">
          <el-table :data="statusRecords" v-loading="statusLoading" size="small" stripe max-height="350">
            <el-table-column label="#" type="index" width="50" />
            <el-table-column :label="ls.t('sensorDetail.time')" width="180">
              <template #default="{ row }">{{ formatTime(row.timestamp) }}</template>
            </el-table-column>
            <el-table-column :label="ls.t('sensorDetail.event')" width="140">
              <template #default="{ row }">
                <el-tag size="small" :type="eventTagType(row.event_name)">
                  {{ row.event_name || '--' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column v-for="field in statusFields" :key="field" :label="field" min-width="110">
              <template #default="{ row }">
                {{ formatField(row.data?.[field]) }}
              </template>
            </el-table-column>
            <el-table-column :label="ls.t('sensorDetail.rawJson')" min-width="220">
              <template #default="{ row }">
                <span class="raw-json">{{ JSON.stringify(row.data) }}</span>
              </template>
            </el-table-column>
            <el-table-column :label="ls.t('sensorDetail.receivedAt')" width="180">
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
import { getSensor, getSensorData, getSensorStatus, sendSensorCommand, patchSensor } from '@/api/sensors'
import { useWebSocket, buildWsUrl } from '@/composables/useWebSocket'

const ls = useLocaleStore()
const route = useRoute()
const userStore = useUserStore()
const isStaff = computed(() => userStore.userInfo?.is_staff === true)
const router = useRouter()

// ==================== 传感器详情 ====================
const sensor = ref(null)
const pageLoading = ref(false)

// ==================== 内联编辑 ====================
const isEditing = ref(false)
const saving = ref(false)
const editForm = ref({ name: '', description: '', location: '' })

function startEdit() {
  editForm.value = {
    name: sensor.value.name || '',
    description: sensor.value.description || '',
    location: sensor.value.location || '',
  }
  isEditing.value = true
}

function cancelEdit() {
  isEditing.value = false
}

async function saveEdit() {
  saving.value = true
  try {
    const updated = await patchSensor(sensor.value.sensor_id, {
      name: editForm.value.name,
      description: editForm.value.description,
      location: editForm.value.location,
    })
    sensor.value.name = updated.name ?? editForm.value.name
    sensor.value.description = updated.description ?? editForm.value.description
    sensor.value.location = updated.location ?? editForm.value.location
    isEditing.value = false
    ElMessage.success('已保存')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const dataFields = computed(() => {
  return sensor.value?.sensor_type_info?.data_fields || []
})

const statusFields = computed(() => {
  return sensor.value?.sensor_type_info?.config_parameters || []
})

function latestValue(field) {
  const val = sensor.value?.latest_data?.data?.[field]
  if (val === undefined || val === null) return null
  if (typeof val === 'number') return Number(val.toFixed(2))
  return val
}

async function fetchSensorDetail() {
  const deviceId = route.params.sensorId
  if (!deviceId) return
  pageLoading.value = true
  try {
    sensor.value = await getSensor(deviceId)
  } catch {
    ElMessage.error(ls.t('sensorDetail.fetchFailed'))
    sensor.value = null
  } finally {
    pageLoading.value = false
  }
}

// ==================== 数据记录 ====================
const dataHours = ref(1)
const dataRecords = ref([])
const dataLoading = ref(false)

async function fetchDataRecords() {
  if (!sensor.value) return
  dataLoading.value = true
  try {
    const res = await getSensorData(sensor.value.sensor_id, { hours: dataHours.value, limit: 500 })
    dataRecords.value = Array.isArray(res) ? res : (res.results || [])
  } catch {
    dataRecords.value = []
  } finally {
    dataLoading.value = false
  }
}

// ==================== 状态记录 ====================
const statusRecords = ref([])
const statusLoading = ref(false)

async function fetchStatusRecords() {
  if (!sensor.value) return
  statusLoading.value = true
  try {
    const res = await getSensorStatus(sensor.value.sensor_id, { limit: 100 })
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

function formatField(val) {
  if (val === undefined || val === null) return '--'
  if (typeof val === 'number') return val.toFixed(2)
  if (typeof val === 'boolean') return val ? ls.t('common.yes') : ls.t('common.no')
  return String(val)
}

function eventTagType(name) {
  if (!name) return 'info'
  if (name.includes('online') || name.includes('enable')) return 'success'
  if (name.includes('offline') || name.includes('disable')) return 'danger'
  return 'info'
}

function onCommandSent() {
  ElMessage.success(ls.t('common.commandSent'))
  // 命令效果由设备响应的 status 上报触发，WS 会推过来；不再轮询拉详情
}

// ==================== WebSocket 实时推送 ====================
// 收到一条 sensor.data：刷新最新值 + 在数据表顶部插入一行
function onSensorData(data) {
  if (!sensor.value || data?.sensor_id !== sensor.value.sensor_id) return
  const tsIso = data.timestamp ? new Date(data.timestamp * 1000).toISOString() : null
  const receivedIso = data.received_at ? new Date(data.received_at * 1000).toISOString() : tsIso
  sensor.value.latest_data = {
    data: data.data,
    timestamp: tsIso,
    received_at: receivedIso,
  }
  // 顶部插入；只保留最近 500 条避免无限增长
  dataRecords.value = [
    { data: data.data, timestamp: tsIso, received_at: receivedIso },
    ...dataRecords.value,
  ].slice(0, 500)
  // 刚收到数据意味着在线
  sensor.value.is_online = true
  sensor.value.last_seen = tsIso
}

// 收到一条 sensor.status：同步在线状态 + 在状态表顶部插入一行
function onSensorStatus(data) {
  if (!sensor.value || data?.sensor_id !== sensor.value.sensor_id) return
  const tsIso = data.timestamp ? new Date(data.timestamp * 1000).toISOString() : null
  const receivedIso = data.received_at ? new Date(data.received_at * 1000).toISOString() : tsIso
  sensor.value.is_online = !!data.is_online
  sensor.value.last_seen = data.last_seen
    ? new Date(data.last_seen * 1000).toISOString()
    : sensor.value.last_seen
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

// 在 setup 顶层创建 WS（autoStart:false），onScopeDispose 注册的 stop 才能在
// 组件卸载时被正确触发。拿到 sensor_id 后再手动 start()。
const ws = useWebSocket(
  () => {
    const sid = sensor.value?.sensor_id
    return sid ? buildWsUrl(`/ws/sensors/${encodeURIComponent(sid)}/`) : ''
  },
  {
    'sensor.data': onSensorData,
    'sensor.status': onSensorStatus,
  },
  { autoStart: false },
)

// ==================== 初始化 ====================
onMounted(async () => {
  await fetchSensorDetail()
  if (sensor.value) {
    fetchDataRecords()
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

.info-item--full {
  grid-column: 1 / -1;
}

.info-edit-btns {
  display: flex;
  gap: 6px;
}

/* 实时数据大字 */
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

/* 工具栏 */
.toolbar {
  display: flex;
  align-items: center;
  gap: var(--iot-spacing-sm);
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
