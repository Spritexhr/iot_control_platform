<template>
  <div class="device-detail-view" v-loading="pageLoading">
    <!-- 顶部：返回 + 标题 -->
    <div class="iot-page-header">
      <div class="header-left">
        <el-button text :icon="ArrowLeft" @click="router.push('/devices')">返回列表</el-button>
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
          {{ device.is_online ? '在线' : '离线' }}
        </span>
      </div>
    </div>

    <template v-if="device">
      <!-- ========== 第一行：基本信息 + 最新状态 + 命令控制 ========== -->
      <div class="detail-row">
        <!-- 基本信息卡片 -->
        <div class="iot-card detail-info-card">
          <div class="iot-card__header">
            <span class="section-title">基本信息</span>
          </div>
          <div class="iot-card__body">
            <div class="info-grid">
              <div class="info-item">
                <span class="info-item__label">设备 ID</span>
                <span class="info-item__value mono">{{ device.device_id }}</span>
              </div>
              <div class="info-item">
                <span class="info-item__label">设备类型</span>
                <span class="info-item__value">{{ device.device_type_info?.name || '--' }}</span>
              </div>
              <div class="info-item">
                <span class="info-item__label">位置</span>
                <span class="info-item__value">{{ device.location || '未设置' }}</span>
              </div>
              <div class="info-item">
                <span class="info-item__label">描述</span>
                <span class="info-item__value">{{ device.description || '无' }}</span>
              </div>
              <div class="info-item">
                <span class="info-item__label">MQTT 状态主题</span>
                <span class="info-item__value mono">{{ device.mqtt_topic_data || '--' }}</span>
              </div>
              <div class="info-item">
                <span class="info-item__label">MQTT 控制主题</span>
                <span class="info-item__value mono">{{ device.mqtt_topic_control || '--' }}</span>
              </div>
              <div class="info-item">
                <span class="info-item__label">最后上报时间</span>
                <span class="info-item__value">{{ device.last_seen ? formatTime(device.last_seen) : '从未' }}</span>
              </div>
              <div class="info-item">
                <span class="info-item__label">创建时间</span>
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
              <span class="section-title">最新状态</span>
              <span v-if="device.latest_data" class="iot-text-secondary" style="font-size: 12px;">
                {{ formatTime(device.latest_data.timestamp) }}
              </span>
            </div>
            <div class="iot-card__body">
              <div v-if="stateFields.length" class="realtime-values">
                <div v-for="field in stateFields" :key="field" class="realtime-item">
                  <div class="iot-data-label">{{ field }}</div>
                  <div class="iot-data-value">{{ formatState(latestValue(field)) }}</div>
                </div>
              </div>
              <div v-else class="empty-hint">未定义状态字段</div>
            </div>
          </div>

          <!-- 命令控制（仅工作人员可见） -->
          <div v-if="isStaff" class="iot-card">
            <div class="iot-card__header">
              <span class="section-title">命令控制</span>
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

      <!-- ========== 第二行：数据记录表格 ========== -->
      <div class="iot-card iot-mt-lg">
        <div class="iot-card__header">
          <span class="section-title">数据记录 (DeviceData)</span>
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
            <el-table-column label="时间" width="180">
              <template #default="{ row }">{{ formatTime(row.timestamp) }}</template>
            </el-table-column>
            <el-table-column v-for="field in stateFields" :key="field" :label="field" min-width="110">
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
import { getDevice, getDeviceData, sendDeviceCommand } from '@/api/devices'

const route = useRoute()
const userStore = useUserStore()
const isStaff = computed(() => userStore.userInfo?.is_staff === true)
const router = useRouter()

// ==================== 设备详情 ====================
const device = ref(null)
const pageLoading = ref(false)

const stateFields = computed(() => {
  return device.value?.device_type_info?.state_fields || []
})

function latestValue(field) {
  const val = device.value?.latest_data?.data?.[field]
  if (val === undefined || val === null) return null
  return val
}

function formatState(val) {
  if (val === null || val === undefined) return '--'
  if (typeof val === 'boolean') return val ? '开' : '关'
  if (typeof val === 'number') return Number(val.toFixed(2))
  return String(val)
}

async function fetchDeviceDetail() {
  const deviceId = route.params.deviceId
  if (!deviceId) return
  pageLoading.value = true
  try {
    device.value = await getDevice(deviceId)
  } catch {
    ElMessage.error('获取设备详情失败')
    device.value = null
  } finally {
    pageLoading.value = false
  }
}

// ==================== 数据记录 ====================
const dataHours = ref(1)
const dataRecords = ref([])
const dataLoading = ref(false)

async function fetchDataRecords() {
  if (!device.value) return
  dataLoading.value = true
  try {
    const res = await getDeviceData(device.value.device_id, { hours: dataHours.value, limit: 500 })
    dataRecords.value = Array.isArray(res) ? res : (res.results || [])
  } catch {
    dataRecords.value = []
  } finally {
    dataLoading.value = false
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
  if (typeof val === 'boolean') return val ? '开' : '关'
  if (typeof val === 'number') return val.toFixed(2)
  return String(val)
}

function onCommandSent() {
  ElMessage.success('命令已发送')
  setTimeout(fetchDeviceDetail, 1000)
}

// ==================== 初始化 ====================
onMounted(async () => {
  await fetchDeviceDetail()
  if (device.value) {
    fetchDataRecords()
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
