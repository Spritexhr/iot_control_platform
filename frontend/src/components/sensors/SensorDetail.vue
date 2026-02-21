<template>
  <el-drawer
    :model-value="visible"
    size="520px"
    :show-close="true"
    :before-close="handleClose"
    @update:model-value="(val) => $emit('update:visible', val)"
  >
    <template #header="{ close }">
      <div class="drawer-header">
        <div class="drawer-header__left">
          <span
            class="iot-status-dot iot-status-dot--lg"
            :class="sensor?.is_online ? 'iot-status-dot--online' : 'iot-status-dot--offline'"
          ></span>
          <div>
            <div class="drawer-title">{{ sensor?.name }}</div>
            <div class="drawer-subtitle">{{ sensor?.sensor_id }}</div>
          </div>
        </div>
        <el-button text :icon="Close" @click="close" class="drawer-close-btn" />
      </div>
    </template>

    <el-tabs v-model="activeTab" v-if="sensor">
      <!-- ========== 实时数据 ========== -->
      <el-tab-pane label="实时数据" name="realtime">
        <div class="realtime-values">
          <div v-for="field in dataFields" :key="field" class="realtime-item">
            <div class="iot-data-label">{{ field }}</div>
            <div class="iot-data-value">
              {{ latestValue(field) ?? '--' }}
            </div>
          </div>
        </div>
        <div v-if="!dataFields.length" class="empty-hint">
          未定义数据字段
        </div>

        <!-- 最近数据列表 -->
        <div class="iot-mt-lg">
          <div class="sub-title">最近数据记录</div>
          <el-table :data="recentData" v-loading="dataLoading" size="small" max-height="320" stripe>
            <el-table-column label="时间" width="170">
              <template #default="{ row }">
                {{ formatTime(row.timestamp) }}
              </template>
            </el-table-column>
            <el-table-column label="数据内容" min-width="200">
              <template #default="{ row }">
                <div class="data-json">
                  <span v-for="(val, key) in row.data" :key="key" class="data-kv">
                    <span class="data-key">{{ key }}:</span>
                    <span class="data-val">{{ typeof val === 'number' ? val.toFixed(2) : val }}</span>
                  </span>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <!-- ========== 历史数据 ========== -->
      <el-tab-pane label="历史数据" name="history">
        <div class="history-toolbar">
          <el-radio-group v-model="historyHours" size="small" @change="fetchHistoryData">
            <el-radio-button :value="1">1小时</el-radio-button>
            <el-radio-button :value="6">6小时</el-radio-button>
            <el-radio-button :value="24">24小时</el-radio-button>
            <el-radio-button :value="168">7天</el-radio-button>
          </el-radio-group>
        </div>
        <el-table :data="historyData" v-loading="historyLoading" size="small" max-height="450" stripe>
          <el-table-column label="时间" width="170">
            <template #default="{ row }">
              {{ formatTime(row.timestamp) }}
            </template>
          </el-table-column>
          <el-table-column v-for="field in dataFields" :key="field" :label="field" min-width="100">
            <template #default="{ row }">
              {{ row.data?.[field] != null ? (typeof row.data[field] === 'number' ? row.data[field].toFixed(2) : row.data[field]) : '--' }}
            </template>
          </el-table-column>
        </el-table>
        <div v-if="historyData.length === 0 && !historyLoading" class="empty-hint">
          该时间范围内暂无数据
        </div>
      </el-tab-pane>

      <!-- ========== 状态记录 ========== -->
      <el-tab-pane label="状态记录" name="status">
        <el-table :data="statusRecords" v-loading="statusLoading" size="small" max-height="450" stripe>
          <el-table-column prop="event_name" label="事件" width="140">
            <template #default="{ row }">
              <el-tag size="small" :type="eventTagType(row.event_name)">
                {{ row.event_name || '未知' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="数据" min-width="200">
            <template #default="{ row }">
              <span class="iot-text-secondary" style="font-size: 12px;">
                {{ JSON.stringify(row.data) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="时间" width="170">
            <template #default="{ row }">
              {{ formatTime(row.timestamp) }}
            </template>
          </el-table-column>
        </el-table>
        <div v-if="statusRecords.length === 0 && !statusLoading" class="empty-hint">
          暂无状态记录
        </div>
      </el-tab-pane>

      <!-- ========== 设备信息 + 命令 ========== -->
      <el-tab-pane label="设备信息" name="info">
        <div class="info-section">
          <div class="info-row">
            <span class="info-label">传感器 ID</span>
            <span class="info-value mono">{{ sensor.sensor_id }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">传感器类型</span>
            <span class="info-value">{{ sensor.sensor_type_info?.name || '--' }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">位置</span>
            <span class="info-value">{{ sensor.location || '未设置' }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">MQTT 数据主题</span>
            <span class="info-value mono">{{ sensor.mqtt_topic_data || '--' }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">MQTT 控制主题</span>
            <span class="info-value mono">{{ sensor.mqtt_topic_control || '--' }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">最后上报</span>
            <span class="info-value">{{ sensor.last_seen ? formatTime(sensor.last_seen) : '从未' }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">创建时间</span>
            <span class="info-value">{{ formatTime(sensor.created_at) }}</span>
          </div>
        </div>

        <!-- 命令面板 -->
        <div class="iot-mt-lg">
          <div class="sub-title">命令控制</div>
          <CommandPanel
            :commands="sensor.sensor_type_info?.commands || {}"
            :device-id="sensor.sensor_id"
            :send-fn="sendSensorCommand"
            @command-sent="onCommandSent"
          />
        </div>
      </el-tab-pane>
    </el-tabs>
  </el-drawer>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Close } from '@element-plus/icons-vue'
import CommandPanel from '@/components/common/CommandPanel.vue'
import { getSensorData, getSensorStatus, sendSensorCommand } from '@/api/sensors'

const props = defineProps({
  visible: { type: Boolean, default: false },
  sensor: { type: Object, default: null },
})

const emit = defineEmits(['update:visible', 'refresh'])

function handleClose(done) {
  emit('update:visible', false)
  done()
}

const activeTab = ref('realtime')

// 实时/最近数据
const recentData = ref([])
const dataLoading = ref(false)

// 历史数据
const historyHours = ref(1)
const historyData = ref([])
const historyLoading = ref(false)

// 状态记录
const statusRecords = ref([])
const statusLoading = ref(false)

const dataFields = ref([])

watch(() => props.visible, async (val) => {
  if (val && props.sensor) {
    activeTab.value = 'realtime'
    dataFields.value = props.sensor.sensor_type_info?.data_fields || []
    fetchRecentData()
    fetchStatusRecords()
  }
})

watch(activeTab, (tab) => {
  if (tab === 'history' && historyData.value.length === 0) {
    fetchHistoryData()
  }
})

async function fetchRecentData() {
  if (!props.sensor) return
  dataLoading.value = true
  try {
    const data = await getSensorData(props.sensor.sensor_id, { hours: 1, limit: 30 })
    recentData.value = Array.isArray(data) ? data : (data.results || [])
  } catch {
    recentData.value = []
  } finally {
    dataLoading.value = false
  }
}

async function fetchHistoryData() {
  if (!props.sensor) return
  historyLoading.value = true
  try {
    const data = await getSensorData(props.sensor.sensor_id, { hours: historyHours.value, limit: 500 })
    historyData.value = Array.isArray(data) ? data : (data.results || [])
  } catch {
    historyData.value = []
  } finally {
    historyLoading.value = false
  }
}

async function fetchStatusRecords() {
  if (!props.sensor) return
  statusLoading.value = true
  try {
    const data = await getSensorStatus(props.sensor.sensor_id, { limit: 50 })
    statusRecords.value = Array.isArray(data) ? data : (data.results || [])
  } catch {
    statusRecords.value = []
  } finally {
    statusLoading.value = false
  }
}

function onCommandSent() {
  ElMessage.success('命令已发送')
  emit('refresh')
}

function formatTime(str) {
  if (!str) return '--'
  const d = new Date(str)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function eventTagType(name) {
  if (!name) return 'info'
  if (name.includes('online') || name.includes('enable')) return 'success'
  if (name.includes('offline') || name.includes('disable')) return 'danger'
  return 'info'
}
</script>

<style scoped>
.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.drawer-close-btn {
  font-size: 18px;
  color: var(--iot-text-secondary);
}

.drawer-header__left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.drawer-title {
  font-size: var(--iot-font-size-md);
  font-weight: 600;
  color: var(--iot-text-primary);
}

.drawer-subtitle {
  font-size: var(--iot-font-size-xs);
  color: var(--iot-text-secondary);
  font-family: 'Courier New', monospace;
}

/* 实时数据大字 */
.realtime-values {
  display: flex;
  flex-wrap: wrap;
  gap: var(--iot-spacing-lg);
  padding: var(--iot-spacing-md) 0;
}

.realtime-item {
  min-width: 100px;
}

.realtime-item .iot-data-value {
  font-size: var(--iot-font-size-data);
}

/* 数据 JSON 内联显示 */
.data-json {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.data-kv {
  font-size: 12px;
}

.data-key {
  color: var(--iot-text-secondary);
  margin-right: 2px;
}

.data-val {
  color: var(--iot-text-primary);
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}

/* 小标题 */
.sub-title {
  font-size: var(--iot-font-size-sm);
  font-weight: 600;
  color: var(--iot-text-primary);
  margin-bottom: var(--iot-spacing-sm);
  padding-bottom: 6px;
  border-bottom: 1px solid var(--iot-border-color-lighter);
}

/* 历史工具栏 */
.history-toolbar {
  margin-bottom: var(--iot-spacing-md);
}

/* 设备信息 */
.info-section {
  display: flex;
  flex-direction: column;
}

.info-row {
  display: flex;
  padding: 8px 0;
  border-bottom: 1px solid var(--iot-border-color-lighter);
}

.info-row:last-child {
  border-bottom: none;
}

.info-label {
  width: 120px;
  flex-shrink: 0;
  font-size: var(--iot-font-size-sm);
  color: var(--iot-text-secondary);
}

.info-value {
  color: var(--iot-text-primary);
  font-size: var(--iot-font-size-sm);
  word-break: break-all;
}

.info-value.mono {
  font-family: 'Courier New', monospace;
  font-size: 12px;
}

.empty-hint {
  text-align: center;
  color: var(--iot-text-secondary);
  padding: 24px;
  font-size: var(--iot-font-size-sm);
}
</style>
