<template>
  <div class="automation-view">
    <div class="iot-page-header">
      <div>
        <h1 class="iot-page-title">{{ ls.t('automation.title') }}</h1>
        <p class="iot-page-subtitle">{{ ls.t('automation.subtitle') }}</p>
      </div>
      <el-button v-if="isSuperuser" type="primary" :icon="Plus" @click="openCreateDialog">{{ ls.t('automation.newRule') }}</el-button>
    </div>

    <!-- 筛选栏 -->
    <div class="iot-card iot-mb-lg">
      <div class="filter-bar">
        <el-input
          v-model="searchText"
          :placeholder="ls.t('automation.searchPlaceholder')"
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
              <template v-if="isStaff && rule.is_launched && rule.process_status === 'running'">
                <span class="poll-interval-label">{{ ls.t('automation.runningLabel').replace('{s}', rule.poll_interval || 30) }}</span>
                <el-button
                  type="danger"
                  size="small"
                  :icon="VideoPause"
                  :loading="launchLoading[rule.id]"
                  @click="handleStop(rule)"
                >
                  {{ ls.t('automation.stopPoll') }}
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
                <span class="poll-interval-unit">{{ ls.t('automation.seconds') }}</span>
                <el-button
                  type="warning"
                  size="small"
                  :icon="RefreshRight"
                  :loading="launchLoading[rule.id]"
                  @click="handleLaunch(rule)"
                >
                  {{ ls.t('automation.startPoll') }}
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
                {{ ls.t('automation.execute') }}
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
              <template #title>{{ ls.t('automation.errorStopped') }}</template>
              <span>{{ rule.error_message }}</span>
            </el-alert>
          </div>

          <div class="rule-card__footer">
            <div class="rule-card__meta">
              <span class="meta-item">
                <el-icon><Connection /></el-icon>
                {{ rule.device_count }} {{ ls.t('automation.relatedDevices') }}
              </span>
              <span class="meta-item">
                <el-icon><Clock /></el-icon>
                {{ formatTime(rule.updated_at) }}
              </span>
            </div>
            <el-button text size="small" type="primary" @click="goDetail(rule)">
              {{ ls.t('automation.viewDetail') }} →
            </el-button>
          </div>

          <!-- 执行结果 -->
          <div v-if="execResult[rule.id]" class="rule-card__result">
            <el-alert
              :title="execResult[rule.id].success ? ls.t('automation.execSuccess') : ls.t('automation.execFailed')"
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
        <el-empty :description="loading ? '加载中...' : ls.t('automation.noRules')" />
      </div>
    </div>

    <!-- 新建规则弹窗 -->
    <el-dialog v-model="createDialogVisible" :title="ls.t('automation.createDialogTitle')" width="600px" destroy-on-close>
      <el-form :model="createForm" label-width="100px" :rules="createRules" ref="createFormRef">
        <el-form-item :label="ls.t('automation.ruleName')" prop="name">
          <el-input v-model="createForm.name" :placeholder="ls.t('automation.ruleNamePlaceholder')" />
        </el-form-item>
        <el-form-item :label="ls.t('automation.scriptId')" prop="script_id">
          <el-input v-model="createForm.script_id" :placeholder="ls.t('automation.scriptIdPlaceholder')" />
        </el-form-item>
        <el-form-item :label="ls.t('common.description')">
          <el-input v-model="createForm.description" type="textarea" :rows="2" :placeholder="ls.t('automation.descPlaceholder')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">{{ ls.t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="createSaving" @click="handleCreate">{{ ls.t('automation.create') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useLocaleStore } from '@/stores/locale'
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

const ls = useLocaleStore()
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
  } catch {
    ElMessage.error(ls.t('automation.fetchFailed'))
  } finally {
    loading.value = false
  }
}

// ==================== 状态显示（从后端字段读取） ====================

function getStatusText(rule) {
  const statusMap = {
    idle: ls.t('automation.statusIdle'),
    running: ls.t('automation.statusRunning'),
    stopped_by_user: ls.t('automation.statusStopped'),
    error_stopped: ls.t('automation.statusError'),
  }
  return statusMap[rule.process_status] || ls.t('automation.statusIdle')
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

// ==================== 轮询控制（后端状态） ====================
const launchLoading = ref({})

async function handleLaunch(rule) {
  launchLoading.value[rule.id] = true
  try {
    const res = await launchAutomationRule(rule.id, rule.poll_interval)
    rule.is_launched = res.is_launched
    rule.process_status = res.process_status
    rule.poll_interval = res.poll_interval
    rule.error_message = ''
    ElMessage.success(`${rule.name} - ${ls.t('automation.launchSuccess')}`)
  } catch {
    ElMessage.error(ls.t('automation.launchFailed'))
  } finally {
    launchLoading.value[rule.id] = false
  }
}

async function handleStop(rule) {
  launchLoading.value[rule.id] = true
  try {
    const res = await stopAutomationRule(rule.id, 'user')
    rule.is_launched = res.is_launched
    rule.process_status = res.process_status
    rule.error_message = ''
    ElMessage.success(`${rule.name} - ${ls.t('automation.stopSuccess')}`)
  } catch {
    ElMessage.error(ls.t('automation.stopFailed'))
  } finally {
    launchLoading.value[rule.id] = false
  }
}

// ==================== 定期刷新状态 ====================
let statusRefreshTimer = null
function startStatusRefresh() {
  if (statusRefreshTimer) clearInterval(statusRefreshTimer)
  statusRefreshTimer = setInterval(async () => {
    try {
      const params = {}
      if (searchText.value) params.search = searchText.value
      const data = await getAutomationRules(params)
      const newRules = data.results || data
      // 仅更新状态，避免覆盖用户的输入
      newRules.forEach(newRule => {
        const oldRule = rules.value.find(r => r.id === newRule.id)
        if (oldRule) {
          oldRule.is_launched = newRule.is_launched
          oldRule.process_status = newRule.process_status
          oldRule.error_message = newRule.error_message
        }
      })
    } catch {
      // 忽略刷新错误
    }
  }, 5000)
}

function stopStatusRefresh() {
  if (statusRefreshTimer) {
    clearInterval(statusRefreshTimer)
    statusRefreshTimer = null
  }
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
      error: err.response?.data?.error || 'execution error',
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
      ls.t('automation.deleteConfirmMsg').replace('{name}', rule.name),
      ls.t('automation.deleteConfirmTitle'),
      { type: 'warning', confirmButtonText: ls.t('common.deleteConfirmOk'), cancelButtonText: ls.t('common.cancel') }
    )
  } catch {
    return
  }
  try {
    await deleteAutomationRule(rule.id)
    ElMessage.success(ls.t('automation.deleted'))
    fetchRules()
  } catch {
    ElMessage.error(ls.t('automation.deleteFailed'))
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

const createRules = computed(() => ({
  name: [{ required: true, message: ls.t('automation.ruleNameRequired'), trigger: 'blur' }],
  script_id: [
    { required: true, message: ls.t('automation.scriptIdRequired'), trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_]+$/, message: ls.t('automation.scriptIdPattern'), trigger: 'blur' },
  ],
}))

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
    ElMessage.success(ls.t('automation.ruleCreated'))
    fetchRules()
  } catch (err) {
    const detail = err.response?.data
    const msg = typeof detail === 'object' ? Object.values(detail).flat().join('；') : ls.t('automation.createFailed')
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
  startStatusRefresh()
})

onUnmounted(() => {
  stopStatusRefresh()
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
