<template>
  <div class="automation-view">
    <div class="iot-page-header">
      <div>
        <h1 class="iot-page-title">自动化规则</h1>
        <p class="iot-page-subtitle">管理设备自动化控制脚本</p>
      </div>
      <el-button v-if="isSuperuser" type="primary" :icon="Plus" @click="openCreateDialog">新建规则</el-button>
    </div>

    <!-- 筛选栏 -->
    <div class="iot-card iot-mb-lg">
      <div class="filter-bar">
        <el-input
          v-model="searchText"
          placeholder="搜索规则名称、脚本ID或描述"
          style="width: 300px"
          clearable
          @clear="fetchRules"
          @keyup.enter="fetchRules"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button :icon="Refresh" circle @click="fetchRules" />
      </div>
    </div>

    <!-- 规则列表 -->
    <div v-loading="loading">
      <div v-if="rules.length" class="rules-list">
        <div
          v-for="rule in rules"
          :key="rule.id"
          class="iot-card rule-card"
        >
          <div class="rule-card__header">
            <div class="rule-card__title-group">
              <div class="rule-card__name" @click="goDetail(rule)">{{ rule.name }}</div>
              <el-tag v-if="rule.script_id" size="small" type="info" class="rule-card__script-id">
                {{ rule.script_id }}
              </el-tag>
              <el-tag
                :type="getStatusTagType(rule)"
                size="small"
                class="rule-card__status"
              >
                {{ getStatusText(rule) }}
              </el-tag>
            </div>
            <div v-if="isStaff || isSuperuser" class="rule-card__actions">
              <template v-if="isStaff && rule.is_launched && localTimers[rule.id]">
                <span class="poll-interval-label">间隔 {{ rule.poll_interval || 30 }}s</span>
                <el-button
                  type="danger"
                  size="small"
                  :icon="VideoPause"
                  :loading="launchLoading[rule.id]"
                  @click="handleStop(rule)"
                >
                  停止轮询 ({{ countdowns[rule.id] ?? 0 }}s)
                </el-button>
              </template>
              <template v-else-if="isStaff">
                <el-input-number
                  v-model="rule.poll_interval"
                  :min="1"
                  :max="86400"
                  :step="1"
                  size="small"
                  controls-position="right"
                  class="poll-interval-input"
                />
                <span class="poll-interval-unit">秒</span>
                <el-button
                  type="warning"
                  size="small"
                  :icon="RefreshRight"
                  :loading="launchLoading[rule.id]"
                  @click="handleLaunch(rule)"
                >
                  启动轮询
                </el-button>
              </template>
              <el-button
                v-if="isStaff"
                type="success"
                size="small"
                plain
                :icon="VideoPlay"
                :loading="execLoading[rule.id]"
                @click="handleExecute(rule)"
              >
                执行
              </el-button>
              <el-button
                v-if="isSuperuser"
                text
                size="small"
                type="danger"
                :icon="Delete"
                @click="handleDelete(rule)"
              />
            </div>
          </div>

          <div v-if="rule.description" class="rule-card__desc">{{ rule.description }}</div>

          <!-- 错误信息 -->
          <div v-if="rule.process_status === 'error_stopped' && rule.error_message" class="rule-card__error">
            <el-alert type="error" :closable="false" show-icon>
              <template #title>报错终止</template>
              <span>{{ rule.error_message }}</span>
            </el-alert>
          </div>

          <div class="rule-card__footer">
            <div class="rule-card__meta">
              <span class="meta-item">
                <el-icon><Connection /></el-icon>
                {{ rule.device_count }} 个关联设备
              </span>
              <span class="meta-item">
                <el-icon><Clock /></el-icon>
                {{ formatTime(rule.updated_at) }}
              </span>
            </div>
            <el-button text size="small" type="primary" @click="goDetail(rule)">
              查看详情 →
            </el-button>
          </div>

          <!-- 执行结果 -->
          <div v-if="execResult[rule.id]" class="rule-card__result">
            <el-alert
              :title="execResult[rule.id].success ? '执行成功' : '执行失败'"
              :type="execResult[rule.id].success ? 'success' : 'error'"
              :closable="true"
              show-icon
              @close="execResult[rule.id] = null"
            >
              <pre v-if="execResult[rule.id].output" class="exec-output">{{ execResult[rule.id].output }}</pre>
              <span v-if="execResult[rule.id].error" class="exec-error">{{ execResult[rule.id].error }}</span>
            </el-alert>
          </div>
        </div>
      </div>
      <div v-else class="iot-card empty-card">
        <el-empty :description="loading ? '加载中...' : '暂无自动化规则'" />
      </div>
    </div>

    <!-- 新建规则弹窗 -->
    <el-dialog v-model="createDialogVisible" title="新建自动化规则" width="600px" destroy-on-close>
      <el-form :model="createForm" label-width="100px" :rules="createRules" ref="createFormRef">
        <el-form-item label="规则名称" prop="name">
          <el-input v-model="createForm.name" placeholder="如: 温度超标自动报警" />
        </el-form-item>
        <el-form-item label="脚本 ID" prop="script_id">
          <el-input v-model="createForm.script_id" placeholder="唯一标识，如: temp_alert" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="createForm.description" type="textarea" :rows="2" placeholder="规则的功能说明（选填）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="createSaving" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh, VideoPlay, VideoPause, Delete, Connection, Clock, RefreshRight } from '@element-plus/icons-vue'
import {
  getAutomationRules,
  createAutomationRule,
  deleteAutomationRule,
  executeAutomationRule,
  launchAutomationRule,
  stopAutomationRule,
} from '@/api/automation'

const router = useRouter()
const userStore = useUserStore()
const isSuperuser = computed(() => userStore.userInfo?.is_superuser === true)
const isStaff = computed(() => userStore.userInfo?.is_staff === true)

// ==================== 筛选 ====================
const searchText = ref('')

// ==================== 数据 ====================
const rules = ref([])
const loading = ref(false)

async function fetchRules() {
  loading.value = true
  try {
    const params = {}
    if (searchText.value) params.search = searchText.value
    const data = await getAutomationRules(params)
    rules.value = data.results || data
    resumeLaunchedRules()
  } catch {
    ElMessage.error('获取规则列表失败')
  } finally {
    loading.value = false
  }
}

// ==================== 状态显示（从后端字段读取） ====================

function getStatusText(rule) {
  const statusMap = {
    idle: '未启动',
    running: '正在运行',
    stopped_by_user: '由用户停止',
    error_stopped: '报错终止',
  }
  return statusMap[rule.process_status] || '未启动'
}

function getStatusTagType(rule) {
  const typeMap = {
    idle: 'info',
    running: 'success',
    stopped_by_user: 'info',
    error_stopped: 'danger',
  }
  return typeMap[rule.process_status] || 'info'
}

// ==================== 轮询控制（后端状态 + 本地定时器） ====================
const localTimers = reactive({})
const countdowns = reactive({})
const launchLoading = ref({})
let countdownIntervals = {}

function resumeLaunchedRules() {
  rules.value.forEach((rule) => {
    if (rule.is_launched && rule.process_status === 'running' && !localTimers[rule.id]) {
      startLocalTimer(rule)
    }
  })
}

async function handleLaunch(rule) {
  launchLoading.value[rule.id] = true
  try {
    const res = await launchAutomationRule(rule.id, rule.poll_interval)
    rule.is_launched = res.is_launched
    rule.process_status = res.process_status
    rule.poll_interval = res.poll_interval
    rule.error_message = ''
    startLocalTimer(rule)
  } catch {
    ElMessage.error('启动轮询失败')
  } finally {
    launchLoading.value[rule.id] = false
  }
}

async function handleStop(rule) {
  clearLocalTimer(rule.id)
  launchLoading.value[rule.id] = true
  try {
    const res = await stopAutomationRule(rule.id, 'user')
    rule.is_launched = res.is_launched
    rule.process_status = res.process_status
    rule.error_message = ''
  } catch {
    ElMessage.error('停止轮询失败')
  } finally {
    launchLoading.value[rule.id] = false
  }
}

function startLocalTimer(rule) {
  if (localTimers[rule.id]) return
  countdowns[rule.id] = 0
  runPollCycle(rule)
}

async function runPollCycle(rule) {
  if (!localTimers[rule.id] && countdowns[rule.id] !== 0) return
  if (!rule.is_launched) return

  execLoading.value[rule.id] = true
  execResult.value[rule.id] = null
  try {
    const res = await executeAutomationRule(rule.id)
    execResult.value[rule.id] = res
  } catch (err) {
    const errorMsg = err.response?.data?.error || err.message || '执行异常'
    execResult.value[rule.id] = {
      success: false,
      error: errorMsg,
      output: err.response?.data?.output || '',
    }
    clearLocalTimer(rule.id)
    try {
      const res = await stopAutomationRule(rule.id, 'error', errorMsg)
      rule.is_launched = res.is_launched
      rule.process_status = res.process_status
      rule.error_message = res.error_message
    } catch { /* ignore */ }
    ElMessage.error(`规则「${rule.name}」执行异常，轮询已终止`)
    return
  } finally {
    execLoading.value[rule.id] = false
  }

  if (!rule.is_launched) return

  scheduleNext(rule)
}

function scheduleNext(rule) {
  const interval = rule.poll_interval || 30
  countdowns[rule.id] = interval

  if (countdownIntervals[rule.id]) clearInterval(countdownIntervals[rule.id])
  countdownIntervals[rule.id] = setInterval(() => {
    countdowns[rule.id]--
    if (countdowns[rule.id] <= 0) {
      clearInterval(countdownIntervals[rule.id])
      delete countdownIntervals[rule.id]
    }
  }, 1000)

  localTimers[rule.id] = setTimeout(() => {
    delete localTimers[rule.id]
    runPollCycle(rule)
  }, interval * 1000)
}

function clearLocalTimer(ruleId) {
  if (localTimers[ruleId]) {
    clearTimeout(localTimers[ruleId])
    delete localTimers[ruleId]
  }
  if (countdownIntervals[ruleId]) {
    clearInterval(countdownIntervals[ruleId])
    delete countdownIntervals[ruleId]
  }
  countdowns[ruleId] = 0
}

function clearAllTimers() {
  Object.keys(localTimers).forEach((id) => clearLocalTimer(id))
}

// ==================== 手动执行 ====================
const execLoading = ref({})
const execResult = ref({})

async function handleExecute(rule) {
  execLoading.value[rule.id] = true
  execResult.value[rule.id] = null
  try {
    const res = await executeAutomationRule(rule.id)
    execResult.value[rule.id] = res
  } catch (err) {
    execResult.value[rule.id] = {
      success: false,
      error: err.response?.data?.error || '执行异常',
      output: err.response?.data?.output || '',
    }
  } finally {
    execLoading.value[rule.id] = false
  }
}

// ==================== 删除 ====================
async function handleDelete(rule) {
  try {
    await ElMessageBox.confirm(
      `确定要删除规则「${rule.name}」吗？此操作不可恢复。`,
      '确认删除',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  clearLocalTimer(rule.id)
  try {
    await deleteAutomationRule(rule.id)
    ElMessage.success('已删除')
    fetchRules()
  } catch {
    ElMessage.error('删除失败')
  }
}

// ==================== 跳转详情 ====================
function goDetail(rule) {
  router.push({ name: 'AutomationDetail', params: { id: rule.id } })
}

// ==================== 新建规则 ====================
const createDialogVisible = ref(false)
const createSaving = ref(false)
const createFormRef = ref(null)
const createForm = ref({
  name: '',
  script_id: '',
  description: '',
})

const createRules = {
  name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  script_id: [
    { required: true, message: '请输入脚本ID', trigger: 'blur' },
    { pattern: /^[a-zA-Z_][a-zA-Z0-9_]*$/, message: '仅支持字母、数字和下划线，且以字母或下划线开头', trigger: 'blur' },
  ],
}

function openCreateDialog() {
  createForm.value = { name: '', script_id: '', description: '' }
  createDialogVisible.value = true
}

async function handleCreate() {
  const formEl = createFormRef.value
  if (formEl) {
    const valid = await formEl.validate().catch(() => false)
    if (!valid) return
  }
  createSaving.value = true
  try {
    await createAutomationRule({
      ...createForm.value,
      script: '',
      device_list: [],
    })
    createDialogVisible.value = false
    ElMessage.success('规则已创建')
    fetchRules()
  } catch (err) {
    const detail = err.response?.data
    const msg = typeof detail === 'object' ? Object.values(detail).flat().join('；') : '创建失败'
    ElMessage.error(msg)
  } finally {
    createSaving.value = false
  }
}

// ==================== 工具函数 ====================
function formatTime(str) {
  if (!str) return '--'
  const d = new Date(str)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

// ==================== 初始化 / 清理 ====================
onMounted(() => {
  fetchRules()
})

onUnmounted(() => {
  clearAllTimers()
})
</script>

<style scoped>
.filter-bar {
  display: flex;
  align-items: center;
  gap: var(--iot-spacing-md);
  padding: var(--iot-spacing-md) var(--iot-spacing-lg);
  flex-wrap: wrap;
}

.rules-list {
  display: flex;
  flex-direction: column;
  gap: var(--iot-spacing-md);
}

.rule-card {
  padding: var(--iot-spacing-lg);
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: opacity var(--iot-transition-base);
}

.rule-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--iot-spacing-md);
  flex-wrap: wrap;
}

.rule-card__title-group {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.rule-card__name {
  font-size: var(--iot-font-size-md);
  font-weight: 600;
  color: var(--iot-text-primary);
  cursor: pointer;
  transition: color var(--iot-transition-fast);
}

.rule-card__name:hover {
  color: var(--iot-color-primary);
}

.rule-card__script-id {
  font-family: 'Courier New', monospace;
  font-size: 11px;
}

.rule-card__status {
  margin-left: 4px;
}

.rule-card__actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.poll-interval-input {
  width: 100px;
}

.poll-interval-unit {
  font-size: 12px;
  color: var(--iot-text-secondary);
  margin-right: 2px;
}

.poll-interval-label {
  font-size: 12px;
  color: var(--iot-text-secondary);
  white-space: nowrap;
}

.rule-card__desc {
  font-size: var(--iot-font-size-sm);
  color: var(--iot-text-secondary);
  line-height: 1.5;
}

.rule-card__error {
  margin-top: 2px;
}

.rule-card__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 8px;
  border-top: 1px solid var(--iot-border-color-lighter);
}

.rule-card__meta {
  display: flex;
  gap: var(--iot-spacing-lg);
}

.meta-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: var(--iot-font-size-xs);
  color: var(--iot-text-secondary);
}

.rule-card__result {
  margin-top: 4px;
}

.exec-output {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 4px 0 0;
  max-height: 120px;
  overflow-y: auto;
}

.exec-error {
  color: var(--iot-color-danger);
  font-size: 12px;
}

.empty-card {
  padding: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
