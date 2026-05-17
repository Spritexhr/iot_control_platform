<template>
  <div class="dashboard-view" v-loading="loading">
    <div class="iot-page-header">
      <div>
        <h1 class="iot-page-title">{{ ls.t('dashboard.title') }}</h1>
        <p class="iot-page-subtitle">{{ ls.t('dashboard.subtitle') }}</p>
      </div>
      <el-button :icon="Refresh" @click="fetchStats" :loading="loading">
        {{ ls.t('dashboard.refresh') }}
      </el-button>
    </div>

    <!-- ========== 统计卡片 ========== -->
    <div class="iot-grid iot-grid--stats iot-mb-lg">
      <div class="stat-card iot-card" @click="router.push('/sensors')">
        <div class="stat-card__body">
          <div class="stat-card__icon stat-card__icon--primary">
            <el-icon :size="24"><Cpu /></el-icon>
          </div>
          <div class="stat-card__content">
            <div class="iot-data-label">{{ ls.t('dashboard.sensors') }}</div>
            <div class="iot-data-value">{{ stats.sensor_total }}</div>
            <div class="stat-card__sub">
              <span class="stat-online">{{ stats.sensor_online }} {{ ls.t('dashboard.online') }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="stat-card iot-card" @click="router.push('/devices')">
        <div class="stat-card__body">
          <div class="stat-card__icon stat-card__icon--success">
            <el-icon :size="24"><Monitor /></el-icon>
          </div>
          <div class="stat-card__content">
            <div class="iot-data-label">{{ ls.t('dashboard.devices') }}</div>
            <div class="iot-data-value">{{ stats.device_total }}</div>
            <div class="stat-card__sub">
              <span class="stat-online">{{ stats.device_online }} {{ ls.t('dashboard.online') }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="stat-card iot-card" @click="router.push('/automation')">
        <div class="stat-card__body">
          <div class="stat-card__icon stat-card__icon--warning">
            <el-icon :size="24"><SetUp /></el-icon>
          </div>
          <div class="stat-card__content">
            <div class="iot-data-label">{{ ls.t('dashboard.automation') }}</div>
            <div class="iot-data-value">{{ stats.rule_total }}</div>
            <div class="stat-card__sub">
              <span class="stat-online">{{ ls.t('dashboard.totalRules') }} {{ stats.rule_total }} {{ ls.t('dashboard.rulesUnit') }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="stat-card iot-card">
        <div class="stat-card__body">
          <div class="stat-card__icon stat-card__icon--info">
            <el-icon :size="24"><DataLine /></el-icon>
          </div>
          <div class="stat-card__content">
            <div class="iot-data-label">{{ ls.t('dashboard.data24h') }}</div>
            <div class="iot-data-value">{{ stats.sensor_data_24h + stats.device_data_24h }}</div>
            <div class="stat-card__sub">
              {{ ls.t('dashboard.sensors') }} {{ stats.sensor_data_24h }} + {{ ls.t('dashboard.devices') }} {{ stats.device_data_24h }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ========== 传感器实时数据 + 设备状态 ========== -->
    <div class="dashboard-content iot-mb-lg">
      <!-- 传感器最新数据 -->
      <div class="iot-card">
        <div class="iot-card__header">
          <span class="section-title">{{ ls.t('dashboard.recentSensors') }}</span>
          <el-button text size="small" type="primary" @click="router.push('/sensors')">
            {{ ls.t('dashboard.viewAll') }}
          </el-button>
        </div>
        <div class="iot-card__body" style="padding-top: 0;">
          <el-table :data="stats.recent_sensors" size="small" stripe max-height="380">
            <el-table-column :label="ls.t('dashboard.status')" width="60" align="center">
              <template #default="{ row }">
                <span
                  class="iot-status-dot"
                  :class="row.is_online ? 'iot-status-dot--online' : 'iot-status-dot--offline'"
                ></span>
              </template>
            </el-table-column>
            <el-table-column prop="name" :label="ls.t('dashboard.name')" min-width="130">
              <template #default="{ row }">
                <span class="clickable-name" @click="router.push(`/sensors/${row.sensor_id}`)">{{ row.name }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="type_name" :label="ls.t('dashboard.type')" width="130" />
            <el-table-column :label="ls.t('dashboard.latestData')" min-width="200">
              <template #default="{ row }">
                <span v-if="row.latest_data" class="data-inline">
                  <span v-for="(val, key) in row.latest_data" :key="key" class="data-kv">
                    <span class="data-key">{{ key }}:</span>
                    <span class="data-val">{{ formatVal(val) }}</span>
                  </span>
                </span>
                <span v-else class="iot-text-secondary">--</span>
              </template>
            </el-table-column>
            <el-table-column :label="ls.t('dashboard.updatedAt')" width="160">
              <template #default="{ row }">
                <span :class="{ 'time-fresh': isFresh(row.latest_time) }">
                  {{ row.latest_time ? timeAgo(row.latest_time) : '--' }}
                </span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- 设备状态 -->
      <div class="iot-card">
        <div class="iot-card__header">
          <span class="section-title">{{ ls.t('dashboard.deviceStatus') }}</span>
          <el-button text size="small" type="primary" @click="router.push('/devices')">
            {{ ls.t('dashboard.viewAll') }}
          </el-button>
        </div>
        <div class="iot-card__body" style="padding-top: 0;">
          <el-table :data="stats.recent_devices" size="small" stripe max-height="380">
            <el-table-column :label="ls.t('dashboard.status')" width="60" align="center">
              <template #default="{ row }">
                <span
                  class="iot-status-dot"
                  :class="row.is_online ? 'iot-status-dot--online' : 'iot-status-dot--offline'"
                ></span>
              </template>
            </el-table-column>
            <el-table-column prop="name" :label="ls.t('dashboard.name')" min-width="130">
              <template #default="{ row }">
                <span class="clickable-name" @click="router.push(`/devices/${row.device_id}`)">{{ row.name }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="type_name" :label="ls.t('dashboard.type')" width="130" />
            <el-table-column :label="ls.t('dashboard.latestStatus')" min-width="200">
              <template #default="{ row }">
                <span v-if="row.latest_data" class="data-inline">
                  <span v-for="(val, key) in row.latest_data" :key="key" class="data-kv">
                    <span class="data-key">{{ key }}:</span>
                    <span class="data-val">{{ formatVal(val) }}</span>
                  </span>
                </span>
                <span v-else class="iot-text-secondary">--</span>
              </template>
            </el-table-column>
            <el-table-column :label="ls.t('dashboard.updatedAt')" width="160">
              <template #default="{ row }">
                <span :class="{ 'time-fresh': isFresh(row.latest_time) }">
                  {{ row.latest_time ? timeAgo(row.latest_time) : '--' }}
                </span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </div>

    <!-- ========== 自动化规则 ========== -->
    <div class="iot-card">
      <div class="iot-card__header">
        <span class="section-title">{{ ls.t('dashboard.automationRules') }}</span>
        <el-button text size="small" type="primary" @click="router.push('/automation')">
          {{ ls.t('dashboard.manageRules') }}
        </el-button>
      </div>
      <div class="iot-card__body" style="padding-top: 0;">
        <el-table v-if="stats.recent_rules && stats.recent_rules.length" :data="stats.recent_rules" size="small" stripe>
          <el-table-column prop="name" :label="ls.t('dashboard.ruleName')" min-width="200">
            <template #default="{ row }">
              <span class="clickable-name" @click="router.push(`/automation/${row.id}`)">{{ row.name }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="script_id" :label="ls.t('dashboard.scriptId')" width="180">
            <template #default="{ row }">
              <code v-if="row.script_id" class="script-id-tag">{{ row.script_id }}</code>
              <span v-else class="iot-text-secondary">--</span>
            </template>
          </el-table-column>
          <el-table-column :label="ls.t('dashboard.updatedAt')" width="170">
            <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
          </el-table-column>
        </el-table>
        <el-empty v-else :description="ls.t('dashboard.noRules')" :image-size="80">
          <el-button type="primary" size="small" @click="router.push('/automation')">
            {{ ls.t('dashboard.createRule') }}
          </el-button>
        </el-empty>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Cpu, Monitor, SetUp, DataLine, Refresh } from '@element-plus/icons-vue'
import { getDashboardStats } from '@/api/system'
import { useLocaleStore } from '@/stores/locale'
import { useWebSocket, buildWsUrl } from '@/composables/useWebSocket'

const router = useRouter()
const ls = useLocaleStore()
const loading = ref(false)

const stats = reactive({
  sensor_total: 0,
  sensor_online: 0,
  device_total: 0,
  device_online: 0,
  rule_total: 0,
  sensor_data_24h: 0,
  device_data_24h: 0,
  recent_sensors: [],
  recent_devices: [],
  recent_rules: [],
})

async function fetchStats() {
  loading.value = true
  try {
    const data = await getDashboardStats()
    Object.assign(stats, data)
  } catch {
    ElMessage.error(ls.t('dashboard.fetchError'))
  } finally {
    loading.value = false
  }
}

function formatVal(val) {
  if (val === null || val === undefined) return '--'
  if (typeof val === 'boolean') return val ? ls.t('dashboard.on') : ls.t('dashboard.off')
  if (typeof val === 'number') return Number(val.toFixed(2))
  return String(val)
}

function timeAgo(dateStr) {
  if (!dateStr) return '--'
  const now = new Date()
  const past = new Date(dateStr)
  const diff = Math.floor((now - past) / 1000)
  if (diff < 5) return ls.t('dashboard.justNow')
  if (diff < 60) return `${diff}${ls.t('dashboard.secondsAgo')}`
  if (diff < 3600) return `${Math.floor(diff / 60)}${ls.t('dashboard.minutesAgo')}`
  if (diff < 86400) return `${Math.floor(diff / 3600)}${ls.t('dashboard.hoursAgo')}`
  return `${Math.floor(diff / 86400)}${ls.t('dashboard.daysAgo')}`
}

function isFresh(dateStr) {
  if (!dateStr) return false
  return (new Date() - new Date(dateStr)) < 300000
}

// ==================== 实时推送 ====================
// 订阅传感器/设备两条 channel，patch 对应表格
function onSensorData(data) {
  if (!data || !data.sensor_id) return
  const row = stats.recent_sensors?.find(r => r.sensor_id === data.sensor_id)
  if (!row) return
  row.latest_data = data.data
  if (data.timestamp) row.latest_time = new Date(data.timestamp * 1000).toISOString()
  row.is_online = true
}

function onSensorStatus(data) {
  if (!data || !data.sensor_id) return
  const row = stats.recent_sensors?.find(r => r.sensor_id === data.sensor_id)
  if (!row) return
  const before = row.is_online
  row.is_online = !!data.is_online
  if (data.last_seen) row.latest_time = new Date(data.last_seen * 1000).toISOString()
  if (before !== row.is_online) {
    stats.sensor_online += row.is_online ? 1 : -1
  }
}

function onDeviceStatus(data) {
  if (!data || !data.device_id) return
  const row = stats.recent_devices?.find(r => r.device_id === data.device_id)
  if (!row) return
  const before = row.is_online
  row.latest_data = data.status
  if (data.timestamp) row.latest_time = new Date(data.timestamp * 1000).toISOString()
  row.is_online = !!data.is_online
  if (data.last_seen) row.latest_time = new Date(data.last_seen * 1000).toISOString()
  if (before !== row.is_online) {
    stats.device_online += row.is_online ? 1 : -1
  }
}

useWebSocket(
  () => buildWsUrl('/ws/sensors/'),
  {
    'sensor.data': onSensorData,
    'sensor.status': onSensorStatus,
  },
)

useWebSocket(
  () => buildWsUrl('/ws/devices/'),
  { 'device.status': onDeviceStatus },
)

function formatTime(str) {
  if (!str) return '--'
  const d = new Date(str)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

onMounted(() => { fetchStats() })
</script>

<style scoped>
/* 统计卡片 */
.stat-card {
  cursor: pointer;
  transition: transform var(--iot-transition-fast), box-shadow var(--iot-transition-fast);
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--iot-shadow-md);
}

.stat-card__body {
  display: flex;
  align-items: center;
  gap: var(--iot-spacing-md);
  padding: var(--iot-spacing-lg);
}

.stat-card__icon {
  width: 48px;
  height: 48px;
  border-radius: var(--iot-radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #fff;
}

/* 图标颜色使用 CSS 变量，随主题切换 */
.stat-card__icon--primary {
  background: linear-gradient(135deg, var(--iot-color-primary), var(--iot-color-primary-light));
}
.stat-card__icon--success {
  background: linear-gradient(135deg, var(--iot-color-success), var(--iot-color-success-light));
}
.stat-card__icon--warning {
  background: linear-gradient(135deg, var(--iot-color-warning), var(--iot-color-warning-light));
}
.stat-card__icon--info {
  background: linear-gradient(135deg, #8B7B6B, #A09080);
}

html.theme-classic .stat-card__icon--info {
  background: linear-gradient(135deg, #607D8B, #90A4AE);
}

.stat-card__sub {
  font-size: var(--iot-font-size-xs);
  color: var(--iot-text-secondary);
  margin-top: 2px;
}

.stat-online {
  color: var(--iot-color-success);
  font-weight: 500;
}

/* 内容区两列 */
.dashboard-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--iot-spacing-md);
}

.section-title {
  font-weight: 600;
  font-size: var(--iot-font-size-md);
}

/* 表格内数据 */
.clickable-name {
  color: var(--iot-text-primary);
  font-weight: 500;
  cursor: pointer;
  transition: color var(--iot-transition-fast);
}

.clickable-name:hover {
  color: var(--iot-color-primary);
}

.data-inline {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 12px;
}

.data-kv {
  display: inline-flex;
  gap: 2px;
}

.data-key {
  color: var(--iot-text-secondary);
}

.data-val {
  color: var(--iot-text-primary);
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}

.time-fresh {
  color: var(--iot-color-success);
  font-weight: 500;
}

.script-id-tag {
  font-family: 'Courier New', monospace;
  font-size: 11px;
  background: var(--iot-bg-page);
  padding: 2px 6px;
  border-radius: 4px;
  color: var(--iot-color-primary);
  border: 1px solid var(--iot-border-color-light);
}

@media (max-width: 1024px) {
  .dashboard-content { grid-template-columns: 1fr; }
}

@media (max-width: 768px) {
  .iot-page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--iot-spacing-sm);
  }

  .iot-page-subtitle { display: none; }

  .stat-card__body { padding: var(--iot-spacing-md); }

  .stat-card__icon {
    width: 40px;
    height: 40px;
  }

  .iot-data-value { font-size: var(--iot-font-size-lg); }
}

@media (max-width: 480px) {
  .stat-card__sub { font-size: 10px; }
  .section-title { font-size: var(--iot-font-size-sm); }
}
</style>
