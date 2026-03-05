<template>
  <div class="automation-detail-view" v-loading="pageLoading">
    <!-- 顶部 -->
    <div class="iot-page-header">
      <div class="header-left">
        <el-button text :icon="ArrowLeft" @click="router.push('/automation')">返回列表</el-button>
        <div v-if="rule" class="header-title-group">
          <div>
            <h1 class="iot-page-title">{{ rule.name }}</h1>
            <p class="iot-page-subtitle">
              <span v-if="rule.script_id" class="mono">{{ rule.script_id }}</span>
              <span v-else>未设置脚本 ID</span>
            </p>
          </div>
        </div>
      </div>
      <div v-if="rule" class="header-right">
        <el-button
          v-if="isStaff"
          type="success"
          :icon="VideoPlay"
          :loading="executing"
          :disabled="polling"
          @click="handleExecute"
        >
          执行测试
        </el-button>
        <el-button
          v-if="isSuperuser"
          type="primary"
          :icon="Check"
          :loading="saving"
          @click="handleSave"
        >
          保存
        </el-button>
      </div>
    </div>

    <template v-if="rule">
      <!-- ========== 第一行：基本信息 + 设备列表 ========== -->
      <div class="detail-row">
        <!-- 基本信息 -->
        <div class="iot-card">
          <div class="iot-card__header">
            <span class="section-title">基本信息</span>
          </div>
          <div class="iot-card__body">
            <el-form label-width="90px" size="default">
              <el-form-item label="规则名称">
                <el-input v-model="rule.name" placeholder="规则名称" :disabled="!isSuperuser" />
              </el-form-item>
              <el-form-item label="脚本 ID">
                <el-input v-model="rule.script_id" placeholder="唯一标识，如 temp_alert（选填）" :disabled="!isSuperuser" />
              </el-form-item>
              <el-form-item label="描述">
                <el-input v-model="rule.description" type="textarea" :rows="2" placeholder="规则的功能说明" :disabled="!isSuperuser" />
              </el-form-item>
            </el-form>
          </div>
        </div>

        <!-- 设备列表管理 -->
        <div class="iot-card">
          <div class="iot-card__header">
            <span class="section-title">关联设备 / 传感器</span>
            <el-button v-if="isSuperuser" type="primary" size="small" :icon="Plus" @click="addDeviceRow">添加</el-button>
          </div>
          <div class="iot-card__body">
            <div v-if="!rule.device_list || rule.device_list.length === 0" class="empty-hint">
              暂未关联设备，脚本中 sensors.get() / devices.get() 将返回 None
            </div>
            <div v-else class="device-list">
              <div v-for="(item, idx) in rule.device_list" :key="idx" class="device-row">
                <el-input
                  v-model="item.device_id"
                  placeholder="传感器/设备 ID"
                  size="small"
                  style="width: 180px"
                  :disabled="!isSuperuser"
                />
                <el-select v-model="item.device_type" size="small" style="width: 120px" placeholder="类型" :disabled="!isSuperuser">
                  <el-option label="Sensor" value="Sensor" />
                  <el-option label="Device" value="Device" />
                </el-select>
                <el-input
                  v-model="item.name"
                  placeholder="备注名称（选填）"
                  size="small"
                  style="flex: 1"
                  :disabled="!isSuperuser"
                />
                <el-button
                  v-if="isSuperuser"
                  text
                  type="danger"
                  size="small"
                  :icon="Delete"
                  @click="rule.device_list.splice(idx, 1)"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ========== 第二行：脚本编辑器 ========== -->
      <div class="iot-card iot-mt-lg">
        <div class="iot-card__header">
          <span class="section-title">自动化脚本</span>
          <div class="script-hints">
            <el-tag size="small" type="info">Python</el-tag>
            <el-tag size="small">需定义带 loop() 方法的类</el-tag>
          </div>
        </div>
        <div class="iot-card__body script-editor-body">
          <div class="script-toolbar">
            <el-button v-if="isSuperuser" size="small" @click="insertTemplate">插入模板</el-button>
            <span class="line-count">{{ scriptLineCount }} 行</span>
          </div>
          <textarea
            ref="scriptTextarea"
            v-model="rule.script"
            class="script-editor"
            spellcheck="false"
            :readonly="!isSuperuser"
            placeholder="# 在此编写自动化脚本...
from engine import sensors, devices

class MyController:
    def __init__(self):
        pass

    def loop(self) -> bool:
        return False"
            @keydown="handleTabKey"
          ></textarea>
        </div>
      </div>

      <!-- ========== 第三行：轮询执行控制台（仅工作人员可见） ========== -->
      <div v-if="isStaff" class="iot-card iot-mt-lg">
        <div class="iot-card__header">
          <span class="section-title">执行控制台</span>
          <div class="poll-controls">
            <!-- 间隔配置 -->
            <span class="poll-label">轮询间隔</span>
            <el-input-number
              v-model="pollInterval"
              :min="1"
              :max="86400"
              :step="1"
              size="small"
              style="width: 130px"
              :disabled="polling"
            />
            <span class="poll-label">秒</span>

            <el-divider direction="vertical" />

            <!-- 单次执行 -->
            <el-button
              type="success"
              size="small"
              :icon="VideoPlay"
              :loading="executing"
              :disabled="polling"
              @click="handleExecute"
            >
              单次执行
            </el-button>

            <!-- 轮询启动/暂停 -->
            <el-button
              v-if="!polling"
              type="warning"
              size="small"
              :icon="RefreshRight"
              @click="startPolling"
            >
              启动轮询
            </el-button>
            <el-button
              v-else
              type="danger"
              size="small"
              :icon="VideoPause"
              @click="stopPolling"
            >
              停止轮询 ({{ pollCountdown }}s)
            </el-button>

            <el-divider direction="vertical" />

            <!-- 清屏 -->
            <el-button size="small" text @click="clearTerminal">清屏</el-button>
          </div>
        </div>
        <div class="iot-card__body terminal-body">
          <!-- 状态栏 -->
          <div class="terminal-status-bar">
            <div class="terminal-status-left">
              <span
                class="iot-status-dot"
                :class="polling ? 'iot-status-dot--online' : 'iot-status-dot--offline'"
              ></span>
              <span v-if="polling" class="terminal-status-text terminal-status-text--active">
                轮询运行中 · 已执行 {{ pollTotalRuns }} 次 · 成功 {{ pollSuccessCount }} 次
              </span>
              <span v-else class="terminal-status-text">
                {{ terminalLines.length ? `共 ${terminalLines.length} 条日志` : '等待执行...' }}
              </span>
            </div>
            <span v-if="pollTotalRuns > 0" class="terminal-status-right">
              成功率 {{ pollTotalRuns > 0 ? Math.round(pollSuccessCount / pollTotalRuns * 100) : 0 }}%
            </span>
          </div>
          <!-- 终端输出 -->
          <div ref="terminalRef" class="terminal">
            <div v-if="!terminalLines.length" class="terminal-empty">
              终端就绪，点击「单次执行」或「启动轮询」开始...
            </div>
            <div
              v-for="(line, idx) in terminalLines"
              :key="idx"
              class="terminal-line"
              :class="'terminal-line--' + line.type"
            >
              <span class="terminal-time">{{ line.time }}</span>
              <span class="terminal-badge" :class="'terminal-badge--' + line.type">
                {{ {success: 'OK', error: 'ERR', warn: 'WARN', info: 'INFO'}[line.type] || 'INFO' }}
              </span>
              <span class="terminal-msg">{{ line.message }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- ========== 脚本编写指南 ========== -->
      <div class="iot-card iot-mt-lg">
        <div class="iot-card__header">
          <span class="section-title">脚本编写指南</span>
        </div>
        <div class="iot-card__body guide-body">
          <div class="guide-section">
            <h4>基本结构</h4>
            <ul>
              <li><code>from engine import sensors, devices</code> — 导入引擎注入的传感器和设备对象</li>
              <li>定义一个带 <code>loop()</code> 方法的类，<code>__init__</code> 相当于 setup，<code>loop()</code> 相当于主循环</li>
              <li><code>loop()</code> 返回 <code>True</code> 表示执行成功，<code>False</code> 表示未满足条件</li>
            </ul>
          </div>
          <div class="guide-section">
            <h4>传感器 API</h4>
            <ul>
              <li><code>sensors.get('sensor_id')</code> — 获取传感器包装对象</li>
              <li><code>.current_state</code> — 最新 SensorData.data 字典</li>
            </ul>
          </div>
          <div class="guide-section">
            <h4>设备 API</h4>
            <ul>
              <li><code>devices.get('device_id')</code> — 获取设备包装对象</li>
              <li><code>.current_state</code> — 最新 DeviceData.data 字典</li>
              <li><code>.send_command('name', params)</code> — 发送控制命令</li>
            </ul>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import { ArrowLeft, VideoPlay, VideoPause, RefreshRight, Check, Plus, Delete } from '@element-plus/icons-vue'
import {
  getAutomationRule,
  updateAutomationRule,
  executeAutomationRule,
  launchAutomationRule,
  stopAutomationRule,
} from '@/api/automation'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const isSuperuser = computed(() => userStore.userInfo?.is_superuser === true)
const isStaff = computed(() => userStore.userInfo?.is_staff === true)

// ==================== 规则数据 ====================
const rule = ref(null)
const pageLoading = ref(false)

async function fetchRule() {
  const id = route.params.id
  if (!id) return
  pageLoading.value = true
  try {
    rule.value = await getAutomationRule(id)
    if (!rule.value.device_list) rule.value.device_list = []
    if (rule.value.is_launched && rule.value.process_status === 'running') {
      resumePolling()
    }
  } catch {
    ElMessage.error('获取规则详情失败')
    rule.value = null
  } finally {
    pageLoading.value = false
  }
}

// ==================== 保存 ====================
const saving = ref(false)

async function handleSave() {
  if (!rule.value) return
  saving.value = true
  try {
    await updateAutomationRule(rule.value.id, {
      name: rule.value.name,
      description: rule.value.description,
      script_id: rule.value.script_id,
      script: rule.value.script,
      device_list: rule.value.device_list,
      poll_interval: rule.value.poll_interval,
    })
    ElMessage.success('保存成功')
  } catch (err) {
    const detail = err.response?.data
    const msg = typeof detail === 'object' ? Object.values(detail).flat().join('；') : '保存失败'
    ElMessage.error(msg)
  } finally {
    saving.value = false
  }
}

// ==================== 终端 ====================
const terminalRef = ref(null)
const terminalLines = ref([])
const MAX_TERMINAL_LINES = 500

function nowStr() {
  const d = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function appendTerminal(type, message) {
  terminalLines.value.push({ type, message, time: nowStr() })
  if (terminalLines.value.length > MAX_TERMINAL_LINES) {
    terminalLines.value.splice(0, terminalLines.value.length - MAX_TERMINAL_LINES)
  }
  nextTick(() => {
    if (terminalRef.value) {
      terminalRef.value.scrollTop = terminalRef.value.scrollHeight
    }
  })
}

function logLevelToType(level) {
  if (level === 'WARNING' || level === 'CRITICAL') return 'warn'
  if (level === 'ERROR') return 'error'
  return 'info'
}

function clearTerminal() {
  terminalLines.value = []
  pollTotalRuns.value = 0
  pollSuccessCount.value = 0
}

// ==================== 单次执行 ====================
const executing = ref(false)

async function handleExecute() {
  if (!rule.value) return
  executing.value = true
  appendTerminal('info', '执行规则...')
  try {
    const res = await executeAutomationRule(rule.value.id)
    if (res.output) {
      res.output.trim().split('\n').forEach((line) => {
        appendTerminal('info', line)
      })
    }
    if (res.logs?.length) {
      res.logs.forEach((log) => appendTerminal(logLevelToType(log.level), log.message))
    }
    appendTerminal(res.success ? 'success' : 'error',
      `执行完成 → ${res.success ? '条件满足，已执行动作' : '条件未满足或执行失败'}`)
    return { success: res.success, fatalError: false }
  } catch (err) {
    const errData = err.response?.data
    if (errData?.output) {
      errData.output.trim().split('\n').forEach((line) => {
        appendTerminal('info', line)
      })
    }
    if (errData?.logs?.length) {
      errData.logs.forEach((log) => appendTerminal(logLevelToType(log.level), log.message))
    }
    appendTerminal('error', `执行异常: ${errData?.error || err.message || '未知错误'}`)
    return { success: false, fatalError: true }
  } finally {
    executing.value = false
  }
}

// ==================== 轮询执行（后端状态驱动） ====================
const polling = ref(false)
const pollInterval = computed({
  get: () => rule.value?.poll_interval || 30,
  set: (val) => { if (rule.value) rule.value.poll_interval = val },
})
const pollCountdown = ref(0)
const pollTotalRuns = ref(0)
const pollSuccessCount = ref(0)
let pollTimer = null
let countdownTimer = null

function resumePolling() {
  if (polling.value) return
  polling.value = true
  pollCountdown.value = 0
  appendTerminal('info', `▶ 轮询已恢复（后端状态为运行中），间隔 ${pollInterval.value} 秒`)
  runPollCycle()
}

async function startPolling() {
  if (polling.value) return
  try {
    const res = await launchAutomationRule(rule.value.id, pollInterval.value)
    rule.value.is_launched = res.is_launched
    rule.value.process_status = res.process_status
    rule.value.poll_interval = res.poll_interval
  } catch {
    ElMessage.error('启动轮询失败')
    return
  }
  polling.value = true
  pollCountdown.value = 0
  appendTerminal('info', `▶ 轮询已启动，间隔 ${pollInterval.value} 秒`)
  runPollCycle()
}

async function stopPolling() {
  polling.value = false
  if (pollTimer) { clearTimeout(pollTimer); pollTimer = null }
  if (countdownTimer) { clearInterval(countdownTimer); countdownTimer = null }
  try {
    const res = await stopAutomationRule(rule.value.id, 'user')
    rule.value.is_launched = res.is_launched
    rule.value.process_status = res.process_status
  } catch { /* ignore */ }
  appendTerminal('info', '⏹ 轮询已停止')
}

async function runPollCycle() {
  if (!polling.value) return
  pollTotalRuns.value++
  const runNo = pollTotalRuns.value
  appendTerminal('info', `── 第 ${runNo} 次执行 ──`)
  const result = await handleExecute()
  if (result.success) pollSuccessCount.value++
  if (result.fatalError) {
    polling.value = false
    if (pollTimer) { clearTimeout(pollTimer); pollTimer = null }
    if (countdownTimer) { clearInterval(countdownTimer); countdownTimer = null }
    const errorMsg = '执行异常导致轮询终止'
    try {
      const res = await stopAutomationRule(rule.value.id, 'error', errorMsg)
      rule.value.is_launched = res.is_launched
      rule.value.process_status = res.process_status
      rule.value.error_message = res.error_message
    } catch { /* ignore */ }
    appendTerminal('error', '轮询已终止（执行异常）')
    return
  }

  if (!polling.value) return

  pollCountdown.value = pollInterval.value
  if (countdownTimer) clearInterval(countdownTimer)
  countdownTimer = setInterval(() => {
    pollCountdown.value--
    if (pollCountdown.value <= 0) {
      clearInterval(countdownTimer)
      countdownTimer = null
    }
  }, 1000)

  pollTimer = setTimeout(() => {
    runPollCycle()
  }, pollInterval.value * 1000)
}

onUnmounted(() => {
  if (pollTimer) clearTimeout(pollTimer)
  if (countdownTimer) clearInterval(countdownTimer)
})

// ==================== 设备列表 ====================
function addDeviceRow() {
  if (!rule.value.device_list) rule.value.device_list = []
  rule.value.device_list.push({ device_id: '', device_type: 'Sensor', name: '' })
}

// ==================== 脚本编辑器辅助 ====================
const scriptTextarea = ref(null)

const scriptLineCount = computed(() => {
  if (!rule.value?.script) return 0
  return rule.value.script.split('\n').length
})

function insertTemplate() {
  const tpl = `from engine import sensors, devices

class MyController:
    SENSOR_ID = ''
    DEVICE_ID = ''

    def __init__(self):
        self.sensor = sensors.get(self.SENSOR_ID)
        self.device = devices.get(self.DEVICE_ID)

    def loop(self) -> bool:
        if not self.sensor or not self.device:
            return False
        state = self.sensor.current_state or {}
        # 在此编写判断逻辑
        # 例如: if state.get('temperature', 0) > 30:
        #           self.device.send_command('turn_on', {})
        #           return True
        return False
`
  rule.value.script = tpl
}

function handleTabKey(e) {
  if (e.key === 'Tab') {
    e.preventDefault()
    const ta = e.target
    const start = ta.selectionStart
    const end = ta.selectionEnd
    const val = ta.value
    ta.value = val.substring(0, start) + '    ' + val.substring(end)
    ta.selectionStart = ta.selectionEnd = start + 4
    rule.value.script = ta.value
  }
}

// ==================== 初始化 ====================
onMounted(() => {
  fetchRule()
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

.mono {
  font-family: 'Courier New', monospace;
  font-size: 12px;
}

.section-title {
  font-weight: 600;
  font-size: var(--iot-font-size-md);
}

/* 两列布局 */
.detail-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--iot-spacing-md);
  align-items: start;
}

/* 设备列表 */
.device-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.device-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 脚本编辑器 */
.script-editor-body {
  padding: 0 !important;
}

.script-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px var(--iot-spacing-lg);
  border-bottom: 1px solid var(--iot-border-color-lighter);
}

.line-count {
  font-size: var(--iot-font-size-xs);
  color: var(--iot-text-secondary);
}

.script-editor {
  width: 100%;
  min-height: 400px;
  padding: var(--iot-spacing-lg);
  border: none;
  outline: none;
  resize: vertical;
  font-family: 'Courier New', 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.6;
  tab-size: 4;
  background: var(--iot-bg-page);
  color: var(--iot-text-primary);
  border-radius: 0 0 var(--iot-radius-base) var(--iot-radius-base);
}

.script-editor::placeholder {
  color: var(--iot-text-secondary);
  opacity: 0.5;
}

.script-hints {
  display: flex;
  gap: 6px;
}

/* 轮询控制 */
.poll-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.poll-label {
  font-size: var(--iot-font-size-xs);
  color: var(--iot-text-secondary);
}

/* 终端区域 */
.terminal-body {
  padding: 0 !important;
}

.terminal-status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px var(--iot-spacing-lg);
  border-bottom: 1px solid var(--iot-border-color-lighter);
  background: var(--iot-bg-page);
}

.terminal-status-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.terminal-status-text {
  font-size: 11px;
  color: var(--iot-text-secondary);
}

.terminal-status-text--active {
  color: var(--iot-color-success);
  font-weight: 500;
}

.terminal-status-right {
  font-size: 11px;
  color: var(--iot-text-secondary);
}

.terminal {
  font-family: 'Courier New', 'Consolas', monospace;
  font-size: 12px;
  line-height: 1.7;
  background: #1e1e2e;
  color: #cdd6f4;
  padding: var(--iot-spacing-md);
  min-height: 200px;
  max-height: 420px;
  overflow-y: auto;
  border-radius: 0 0 var(--iot-radius-base) var(--iot-radius-base);
}

.terminal-empty {
  color: #6c7086;
  text-align: center;
  padding: 60px 0;
}

.terminal-line {
  display: flex;
  gap: 8px;
  padding: 1px 0;
}

.terminal-time {
  color: #6c7086;
  flex-shrink: 0;
}

.terminal-badge {
  flex-shrink: 0;
  font-size: 10px;
  font-weight: 700;
  padding: 0 5px;
  border-radius: 3px;
  line-height: 18px;
  text-align: center;
  min-width: 32px;
}

.terminal-badge--success {
  background: #a6e3a1;
  color: #1e1e2e;
}

.terminal-badge--error {
  background: #f38ba8;
  color: #1e1e2e;
}

.terminal-badge--info {
  background: #89b4fa;
  color: #1e1e2e;
}

.terminal-badge--warn {
  background: #f9e2af;
  color: #1e1e2e;
}

.terminal-msg {
  word-break: break-all;
}

.terminal-line--success .terminal-msg {
  color: #a6e3a1;
}

.terminal-line--error .terminal-msg {
  color: #f38ba8;
}

.terminal-line--warn .terminal-msg {
  color: #f9e2af;
}

/* 指南 */
.guide-body {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--iot-spacing-lg);
}

.guide-section h4 {
  font-size: var(--iot-font-size-sm);
  font-weight: 600;
  color: var(--iot-text-primary);
  margin: 0 0 8px;
}

.guide-section ul {
  margin: 0;
  padding-left: 18px;
  font-size: var(--iot-font-size-xs);
  color: var(--iot-text-secondary);
  line-height: 1.8;
}

.guide-section code {
  background: var(--iot-bg-page);
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 11px;
  color: var(--iot-color-primary);
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
}
</style>
