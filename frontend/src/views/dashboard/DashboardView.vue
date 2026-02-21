<template>
  <div class="dashboard-view" v-loading="loading">
    <div class="iot-page-header">
      <div>
        <h1 class="iot-page-title">仪表盘</h1>
        <p class="iot-page-subtitle">平台运行状态一览</p>
      </div>
      <el-button :icon="Refresh" @click="fetchStats" :loading="loading">刷新</el-button>
    </div>

    <!-- ========== 统计卡片 ========== -->
    <div class="iot-grid iot-grid--stats iot-mb-lg">
      <div class="stat-card iot-card" @click="router.push('/sensors')">
        <div class="stat-card__body">
          <div class="stat-card__icon stat-card__icon--primary">
            <el-icon :size="24"><Cpu /></el-icon>
          </div>
          <div class="stat-card__content">
            <div class="iot-data-label">传感器</div>
            <div class="iot-data-value">{{ stats.sensor_total }}</div>
            <div class="stat-card__sub">
              <span class="stat-online">{{ stats.sensor_online }} 在线</span>
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
            <div class="iot-data-label">设备</div>
            <div class="iot-data-value">{{ stats.device_total }}</div>
            <div class="stat-card__sub">
              <span class="stat-online">{{ stats.device_online }} 在线</span>
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
            <div class="iot-data-label">自动化规则</div>
            <div class="iot-data-value">{{ stats.rule_total }}</div>
            <div class="stat-card__sub">
              <span class="stat-online">共 {{ stats.rule_total }} 条</span>
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
            <div class="iot-data-label">24h 数据量</div>
            <div class="iot-data-value">{{ stats.sensor_data_24h + stats.device_data_24h }}</div>
            <div class="stat-card__sub">
              传感器 {{ stats.sensor_data_24h }} + 设备 {{ stats.device_data_24h }}
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
          <span class="section-title">传感器最新数据</span>
          <el-button text size="small" type="primary" @click="router.push('/sensors')">查看全部 →</el-button>
        </div>
        <div class="iot-card__body" style="padding-top: 0;">
          <el-table :data="stats.recent_sensors" size="small" stripe max-height="380">
            <el-table-column label="状态" width="60" align="center">
              <template #default="{ row }">
                <span
                  class="iot-status-dot"
                  :class="row.is_online ? 'iot-status-dot--online' : 'iot-status-dot--offline'"
                ></span>
              </template>
            </el-table-column>
            <el-table-column prop="name" label="名称" min-width="130">
              <template #default="{ row }">
                <span class="clickable-name" @click="router.push(`/sensors/${row.sensor_id}`)">
                  {{ row.name }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="type_name" label="类型" width="130" />
            <el-table-column label="最新数据" min-width="200">
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
            <el-table-column label="更新时间" width="160">
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
          <span class="section-title">设备状态</span>
          <el-button text size="small" type="primary" @click="router.push('/devices')">查看全部 →</el-button>
        </div>
        <div class="iot-card__body" style="padding-top: 0;">
          <el-table :data="stats.recent_devices" size="small" stripe max-height="380">
            <el-table-column label="状态" width="60" align="center">
              <template #default="{ row }">
                <span
                  class="iot-status-dot"
                  :class="row.is_online ? 'iot-status-dot--online' : 'iot-status-dot--offline'"
                ></span>
              </template>
            </el-table-column>
            <el-table-column prop="name" label="名称" min-width="130">
              <template #default="{ row }">
                <span class="clickable-name" @click="router.push(`/devices/${row.device_id}`)">
                  {{ row.name }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="type_name" label="类型" width="130" />
            <el-table-column label="最新状态" min-width="200">
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
            <el-table-column label="更新时间" width="160">
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
        <span class="section-title">自动化规则</span>
        <el-button text size="small" type="primary" @click="router.push('/automation')">管理规则 →</el-button>
      </div>
      <div class="iot-card__body" style="padding-top: 0;">
        <el-table :data="stats.recent_rules" size="small" stripe>
          <el-table-column prop="name" label="规则名称" min-width="200">
            <template #default="{ row }">
              <span class="clickable-name" @click="router.push(`/automation/${row.id}`)">
                {{ row.name }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="script_id" label="脚本 ID" width="180">
            <template #default="{ row }">
              <code v-if="row.script_id" class="script-id-tag">{{ row.script_id }}</code>
              <span v-else class="iot-text-secondary">--</span>
            </template>
          </el-table-column>
          <el-table-column label="更新时间" width="170">
            <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
          </el-table-column>
        </el-table>
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

const router = useRouter()
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
    ElMessage.error('获取仪表盘数据失败')
  } finally {
    loading.value = false
  }
}

function formatVal(val) {
  if (val === null || val === undefined) return '--'
  if (typeof val === 'boolean') return val ? '开' : '关'
  if (typeof val === 'number') return Number(val.toFixed(2))
  return String(val)
}

function timeAgo(dateStr) {
  if (!dateStr) return '--'
  const now = new Date()
  const past = new Date(dateStr)
  const diff = Math.floor((now - past) / 1000)
  if (diff < 5) return '刚刚'
  if (diff < 60) return `${diff}秒前`
  if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`
  return `${Math.floor(diff / 86400)}天前`
}

function isFresh(dateStr) {
  if (!dateStr) return false
  return (new Date() - new Date(dateStr)) < 300000
}

function formatTime(str) {
  if (!str) return '--'
  const d = new Date(str)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

onMounted(() => {
  fetchStats()
})
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

.stat-card__icon--primary { background: linear-gradient(135deg, #1A73E8, #4A90E2); }
.stat-card__icon--success { background: linear-gradient(135deg, #00BFA5, #33CCBB); }
.stat-card__icon--warning { background: linear-gradient(135deg, #FF9800, #FFB74D); }
.stat-card__icon--info    { background: linear-gradient(135deg, #607D8B, #90A4AE); }

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
  border-radius: 3px;
  color: var(--iot-color-primary);
}

@media (max-width: 1024px) {
  .dashboard-content {
    grid-template-columns: 1fr;
  }
}
</style>
