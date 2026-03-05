<template>
  <div class="sensor-detail-view" v-loading="pageLoading">
    <!-- 顶部：返回 + 标题 -->
    <div class="iot-page-header">
      <div class="header-left">
        <el-button text :icon="ArrowLeft" @click="router.push('/sensors')">返回列表</el-button>
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
          {{ sensor.is_online ? '在线' : '离线' }}
        </span>
      </div>
    </div>

    <template v-if="sensor">
      <!-- ========== 第一行：基本信息 + 实时数据 ========== -->
      <div class="detail-row">
        <!-- 基本信息卡片 -->
        <div class="iot-card detail-info-card">
          <div class="iot-card__header">
            <span class="section-title">基本信息</span>
          </div>
          <div class="iot-card__body">
            <div class="info-grid">
              <div class="info-item">
                <span class="info-item__label">传感器 ID</span>
                <span class="info-item__value mono">{{ sensor.sensor_id }}</span>
              </div>
              <div class="info-item">
                <span class="info-item__label">传感器类型</span>
                <span class="info-item__value">{{ sensor.sensor_type_info?.name || '--' }}</span>
              </div>
              <div class="info-item">
                <span class="info-item__label">位置</span>
                <span class="info-item__value">{{ sensor.location || '未设置' }}</span>
              </div>
              <div class="info-item">
                <span class="info-item__label">描述</span>
                <span class="info-item__value">{{ sensor.description || '无' }}</span>
              </div>
              <div class="info-item">
                <span class="info-item__label">MQTT 数据主题</span>
                <span class="info-item__value mono">{{ sensor.mqtt_topic_data || '--' }}</span>
              </div>
              <div class="info-item">
                <span class="info-item__label">MQTT 控制主题</span>
                <span class="info-item__value mono">{{ sensor.mqtt_topic_control || '--' }}</span>
              </div>
              <div class="info-item">
                <span class="info-item__label">最后上报时间</span>
                <span class="info-item__value">{{ sensor.last_seen ? formatTime(sensor.last_seen) : '从未' }}</span>
              </div>
              <div class="info-item">
                <span class="info-item__label">创建时间</span>
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
              <span class="section-title">最新数据</span>
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
              <div v-else class="empty-hint">未定义数据字段</div>
            </div>
          </div>

          <!-- 命令控制（仅工作人员可见） -->
          <div v-if="isStaff" class="iot-card">
            <div class="iot-card__header">
              <span class="section-title">命令控制</span>
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
          <span class="section-title">数据记录 (SensorData)</span>
          <div class="toolbar">
            <el-radio-group v-model="dataHours" size="small" @change="fetchDataRecords">
              <el-radio-button :value="1">1小时</el-radio-button>
              <el-radio-button :value="6">6小时</el-radio-button>
              <el-radio-button :value="24">24小时</el-radio-button>
              <el-radio-button :value="168">7天</el-radio-button>
            </el-radio-group>
            <el-button :icon="Refresh" size="small" @click="fetchDataRecords">刷新</el-button>
          </div>
        </div>
        <div class="iot-card__body" style="padding-top: 0;">
          <el-table :data="dataRecords" v-loading="dataLoading" size="small" stripe max-height="420">
            <el-table-column label="#" type="index" width="50" />
            <el-table-column label="采集时间" width="180">
              <template #default="{ row }">{{ formatTime(row.timestamp) }}</template>
            </el-table-column>
            <el-table-column v-for="field in dataFields" :key="field" :label="field" min-width="110">
              <template #default="{ row }">
                {{ formatField(row.data?.[field]) }}
              </template>
            </el-table-column>
            <el-table-column label="原始 JSON" min-width="220">
              <template #default="{ row }">
                <span class="raw-json">{{ JSON.stringify(row.data) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="接收时间" width="180">
              <template #default="{ row }">{{ formatTime(row.received_at) }}</template>
            </el-table-column>
          </el-table>
          <div class="table-footer">
            共 {{ dataRecords.length }} 条记录
          </div>
        </div>
      </div>

      <!-- ========== 第三行：状态记录表格 ========== -->
      <div class="iot-card iot-mt-lg">
        <div class="iot-card__header">
          <span class="section-title">状态记录 (SensorStatusCollection)</span>
          <el-button :icon="Refresh" size="small" @click="fetchStatusRecords">刷新</el-button>
        </div>
        <div class="iot-card__body" style="padding-top: 0;">
          <el-table :data="statusRecords" v-loading="statusLoading" size="small" stripe max-height="350">
            <el-table-column label="#" type="index" width="50" />
            <el-table-column label="事件" width="140">
              <template #default="{ row }">
                <el-tag size="small" :type="eventTagType(row.event_name)">
                  {{ row.event_name || '--' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="数据内容" min-width="280">
              <template #default="{ row }">
                <span class="raw-json">{{ JSON.stringify(row.data) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="时间" width="180">
              <template #default="{ row }">{{ formatTime(row.timestamp) }}</template>
            </el-table-column>
            <el-table-column label="接收时间" width="180">
              <template #default="{ row }">{{ formatTime(row.received_at) }}</template>
            </el-table-column>
          </el-table>
          <div class="table-footer">
            共 {{ statusRecords.length }} 条记录
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
import { getSensor, getSensorData, getSensorStatus, sendSensorCommand } from '@/api/sensors'

const route = useRoute()
const userStore = useUserStore()
const isStaff = computed(() => userStore.userInfo?.is_staff === true)
const router = useRouter()

// ==================== 传感器详情 ====================
const sensor = ref(null)
const pageLoading = ref(false)

const dataFields = computed(() => {
  return sensor.value?.sensor_type_info?.data_fields || []
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
    ElMessage.error('获取传感器详情失败')
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
  if (typeof val === 'boolean') return val ? '是' : '否'
  return String(val)
}

function eventTagType(name) {
  if (!name) return 'info'
  if (name.includes('online') || name.includes('enable')) return 'success'
  if (name.includes('offline') || name.includes('disable')) return 'danger'
  return 'info'
}

function onCommandSent() {
  ElMessage.success('命令已发送')
  setTimeout(fetchSensorDetail, 1000)
}

// ==================== 初始化 ====================
onMounted(async () => {
  await fetchSensorDetail()
  if (sensor.value) {
    fetchDataRecords()
    fetchStatusRecords()
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
