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
              <div v-for="(item, idx) in rule.device_list" :key="idx" class="device-item">
                <!-- 主行：选择器 + 类型 + 备注名 + 删除 -->
                <div class="device-row">
                  <el-select
                    v-model="item.device_id"
                    filterable
                    clearable
                    :allow-create="!rule.project"
                    default-first-option
                    placeholder="搜索或输入 ID"
                    size="small"
                    style="width: 210px; flex-shrink: 0"
                    :disabled="!isSuperuser"
                  >
                    <template v-if="item.device_type === 'Sensor'">
                      <el-option
                        v-for="s in availableSources.sensors"
                        :key="s.id"
                        :label="`${s.id}`"
                        :value="s.id"
                      >
                        <span class="opt-id">{{ s.id }}</span>
                        <span class="opt-name">{{ s.name }}</span>
                      </el-option>
                    </template>
                    <template v-else>
                      <el-option
                        v-for="d in availableSources.devices"
                        :key="d.id"
                        :label="`${d.id}`"
                        :value="d.id"
                      >
                        <span class="opt-id">{{ d.id }}</span>
                        <span class="opt-name">{{ d.name }}</span>
                      </el-option>
                    </template>
                  </el-select>

                  <el-select
                    v-model="item.device_type"
                    size="small"
                    style="width: 105px; flex-shrink: 0"
                    :disabled="!isSuperuser"
                  >
                    <el-option label="Sensor" value="Sensor" />
                    <el-option label="Device" value="Device" />
                  </el-select>

                  <el-input
                    v-model="item.name"
                    placeholder="备注名（选填）"
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

                <!-- 字段 / 命令提示行 -->
                <div v-if="getSourceHint(item)" class="device-hint">
                  <template v-if="item.device_type === 'Sensor'">
                    <span class="hint-label">字段</span>
                    <span class="hint-values">{{ getSourceHint(item).data_fields.join('  ·  ') }}</span>
                  </template>
                  <template v-else>
                    <span class="hint-label">命令</span>
                    <span class="hint-values">{{ getSourceHint(item).commands.join('  ·  ') }}</span>
                  </template>
                </div>
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
            <el-tag size="small">类风格或 loop() 函数均可</el-tag>
          </div>
        </div>
        <div class="iot-card__body script-editor-body">
          <div class="script-toolbar">
            <el-button v-if="isSuperuser" size="small" @click="insertTemplate">插入模板</el-button>
            <span class="line-count">{{ scriptLineCount }} 行</span>
          </div>
          <Codemirror
            v-model="rule.script"
            :disabled="!isSuperuser"
            :extensions="cmExtensions"
            :style="{ minHeight: '400px', fontSize: '13px' }"
            class="script-codemirror"
          />
        </div>
      </div>

      <!-- ========== 第三行：轮询执行控制台（仅工作人员可见） ========== -->
      <div v-if="isStaff" class="iot-card iot-mt-lg">
        <div class="iot-card__header">
          <span class="section-title">执行控制台</span>
          <div class="poll-controls">
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
              停止轮询
            </el-button>

            <el-divider direction="vertical" />
            <el-button size="small" text @click="clearTerminal">清屏</el-button>
          </div>
        </div>
        <div class="iot-card__body terminal-body">
          <div class="terminal-status-bar">
            <div class="terminal-status-left">
              <span
                class="iot-status-dot"
                :class="polling ? 'iot-status-dot--online' : 'iot-status-dot--offline'"
              ></span>
              <span v-if="polling" class="terminal-status-text terminal-status-text--active">
                后台轮询服务已接管 (运行中)
              </span>
              <span v-else class="terminal-status-text">
                {{ terminalLines.length ? `共 ${terminalLines.length} 条日志` : '等待执行...' }}
              </span>
            </div>
          </div>
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
              <li><strong>类风格</strong>：定义带 <code>loop()</code> 方法的类，引擎每次调用时自动实例化并执行一次 <code>loop()</code></li>
              <li><strong>函数风格</strong>：直接定义顶层 <code>loop()</code> 函数，适合简单逻辑</li>
              <li><code>loop()</code> 返回 <code>True</code> 表示执行成功，<code>False</code> 表示条件未满足</li>
              <li>每次调用都是独立的，<code>loop()</code> 内的临时变量不会在轮询周期间保留</li>
            </ul>
          </div>
          <div class="guide-section">
            <h4>传感器 API</h4>
            <ul>
              <li><code>sensors.get('sensor_id')</code> — 获取传感器包装对象（未关联或不存在时返回 None）</li>
              <li><code>.current_state</code> — 最新 SensorData.data 字典（本次 loop 内缓存）</li>
              <li><code>.refresh()</code> — 从数据库重新读取最新状态</li>
              <li><code>.history('field', n=10)</code> — 最近 n 条字段值列表（升序，最新在最后）</li>
              <li><code>.average('field', minutes=5)</code> — 最近 N 分钟均值，无数据返回 None</li>
              <li><code>.is_online</code> — 是否在线（3 分钟内有数据）</li>
            </ul>
          </div>
          <div class="guide-section">
            <h4>设备 API</h4>
            <ul>
              <li><code>devices.get('device_id')</code> — 获取设备包装对象（未关联或不存在时返回 None）</li>
              <li><code>.current_state</code> — 最新 DeviceStatusCollection.data 字典</li>
              <li><code>.send_command('name', params)</code> — 普通发送；返回值仅表示 MQTT 发布是否成功，不等待设备确认</li>
              <li><code>.send_command_with_make_sure('name', params, timeout=3)</code> — 确认发送；等待设备回传 <code>check_code</code>，成功返回 <code>True</code>，超时或失败返回 <code>False</code></li>
              <li><code>.refresh()</code> — 重新读取设备最新状态</li>
              <li><code>.is_online</code> — 是否在线（3 分钟内有数据）</li>
            </ul>
          </div>
          <div class="guide-section">
            <h4>脚本示例</h4>
            <pre class="guide-code">from engine import sensors, devices

class TempAlert:
    def loop(self) -> bool:
        sensor = sensors.get('DHT11-001')
        fan = devices.get('fan_001')
        if not sensor or not fan:
            return False
        avg_temp = sensor.average('temperature', minutes=5)
        if avg_temp and avg_temp > 30:
            return fan.send_command_with_make_sure('turn_on', {}, timeout=3)
        return False</pre>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import { ArrowLeft, VideoPlay, VideoPause, RefreshRight, Check, Plus, Delete } from '@element-plus/icons-vue'
import { Codemirror } from 'vue-codemirror'
import { python } from '@codemirror/lang-python'
import { oneDark } from '@codemirror/theme-one-dark'
import {
  getAutomationRule,
  updateAutomationRule,
  executeAutomationRule,
  launchAutomationRule,
  stopAutomationRule,
  getAvailableSources,
} from '@/api/automation'
import { useWebSocket, buildWsUrl } from '@/composables/useWebSocket'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const isSuperuser = computed(() => userStore.userInfo?.is_superuser === true)
const isStaff = computed(() => userStore.userInfo?.is_staff === true)

// CodeMirror 扩展（Python 高亮 + 暗色主题）
const cmExtensions = [python(), oneDark]

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
  } catch {
    ElMessage.error('获取规则详情失败')
    rule.value = null
  } finally {
    pageLoading.value = false
  }
}

// ==================== 可用传感器/设备列表 ====================
const availableSources = ref({ sensors: [], devices: [] })

async function fetchAvailableSources() {
  try {
    const params = rule.value?.project && rule.value?.section
      ? { project: rule.value.project, section: rule.value.section }
      : {}
    availableSources.value = await getAvailableSources(params)
  } catch {
    // 加载失败不影响主功能，选择器降级为手动输入
  }
}

/** 根据 device_list 条目查找对应 source 信息（用于字段/命令提示） */
function getSourceHint(item) {
  if (!item.device_id) return null
  if (item.device_type === 'Sensor') {
    const s = availableSources.value.sensors.find((x) => x.id === item.device_id)
    return s?.data_fields?.length ? s : null
  } else {
    const d = availableSources.value.devices.find((x) => x.id === item.device_id)
    return d?.commands?.length ? d : null
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
    appendTerminal('error', `执行异常: ${errData?.detail || errData?.error || err.message || '未知错误'}`)
    return { success: false, fatalError: true }
  } finally {
    executing.value = false
  }
}

// ==================== 轮询执行（后端状态驱动） ====================
const polling = computed(() => rule.value?.is_launched && rule.value?.process_status === 'running')
const pollInterval = computed({
  get: () => rule.value?.poll_interval || 30,
  set: (val) => { if (rule.value) rule.value.poll_interval = val },
})

async function startPolling() {
  if (polling.value) return
  try {
    const res = await launchAutomationRule(rule.value.id, pollInterval.value)
    rule.value.is_launched = res.is_launched
    rule.value.process_status = res.process_status
    rule.value.poll_interval = res.poll_interval
    appendTerminal('info', `▶ 后台轮询已启动，间隔 ${pollInterval.value} 秒`)
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '启动轮询失败')
  }
}

async function stopPolling() {
  try {
    const res = await stopAutomationRule(rule.value.id, 'user')
    rule.value.is_launched = res.is_launched
    rule.value.process_status = res.process_status
    appendTerminal('info', '⏹ 后台轮询已停止')
  } catch {
    ElMessage.error('停止轮询失败')
  }
}

function onRuleEvent(data) {
  if (!rule.value || !data || data.id !== rule.value.id) return
  if (data.process_status === 'error_stopped' && rule.value.process_status === 'running') {
    appendTerminal('error', `后台轮询异常停止: ${data.error_message || '未知错误'}`)
  }
  rule.value.is_launched = data.is_launched
  rule.value.process_status = data.process_status
  rule.value.error_message = data.error_message
  if (data.poll_interval != null) rule.value.poll_interval = data.poll_interval
  if (data.last_run_time) rule.value.last_run_time = data.last_run_time
  if (data.updated_at) rule.value.updated_at = data.updated_at
}

useWebSocket(
  () => buildWsUrl('/ws/automation/'),
  { 'automation.rule': onRuleEvent },
)

// ==================== 设备列表 ====================
function addDeviceRow() {
  if (!rule.value.device_list) rule.value.device_list = []
  rule.value.device_list.push({ device_id: '', device_type: 'Sensor', name: '' })
}

// ==================== 脚本编辑器辅助 ====================
const scriptLineCount = computed(() => {
  if (!rule.value?.script) return 0
  return rule.value.script.split('\n').length
})

/** 将 device_id 转成合法的 Python 变量名 */
function toVarName(deviceId) {
  return deviceId.replace(/[^a-zA-Z0-9]/g, '_').toLowerCase().replace(/^(\d)/, '_$1')
}

function insertTemplate() {
  const deviceList = rule.value?.device_list || []

  if (deviceList.length === 0) {
    rule.value.script = `from engine import sensors, devices

class MyController:
    def loop(self) -> bool:
        # sensor = sensors.get('your-sensor-id')
        # device = devices.get('your-device-id')
        # if not sensor or not device:
        #     return False
        # state = sensor.current_state or {}
        return False
`
    return
  }

  const varLines = []
  const varNames = []
  const hintLines = []

  for (const item of deviceList) {
    if (!item.device_id) continue
    const varName = toVarName(item.device_id)
    const label = item.name || item.device_id
    varNames.push(varName)

    if (item.device_type === 'Sensor') {
      varLines.push(`        ${varName} = sensors.get('${item.device_id}')  # ${label}`)
      const src = availableSources.value.sensors.find((s) => s.id === item.device_id)
      if (src?.data_fields?.length) {
        hintLines.push(`        # ${item.device_id} 可用字段: ${src.data_fields.join(', ')}`)
        hintLines.push(`        # state = ${varName}.current_state or {}`)
      }
    } else {
      varLines.push(`        ${varName} = devices.get('${item.device_id}')  # ${label}`)
      const src = availableSources.value.devices.find((d) => d.id === item.device_id)
      if (src?.commands?.length) {
        hintLines.push(`        # ${item.device_id} 可用命令: ${src.commands.join(', ')}`)
        hintLines.push(`        # ${varName}.send_command('${src.commands[0]}', {})`)
      }
    }
  }

  const guardLine = varNames.length
    ? `        if not ${varNames.join(' or not ')}:\n            return False\n`
    : ''

  const lines = [
    'from engine import sensors, devices',
    '',
    'class MyController:',
    '    def loop(self) -> bool:',
    ...varLines,
    guardLine,
    ...hintLines,
    '',
    '        return False',
    '',
  ]

  rule.value.script = lines.join('\n')
}

// ==================== 初始化 ====================
onMounted(async () => {
  await fetchRule()
  await fetchAvailableSources()
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
  gap: 10px;
}

.device-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.device-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 下拉选项内容 */
.opt-id {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  font-weight: 600;
  color: var(--iot-text-primary);
  margin-right: 8px;
}

.opt-name {
  font-size: 11px;
  color: var(--iot-text-secondary);
}

/* 字段/命令提示行 */
.device-hint {
  display: flex;
  align-items: baseline;
  gap: 6px;
  padding-left: 4px;
  font-size: 11px;
  color: var(--iot-text-secondary);
  line-height: 1.4;
}

.hint-label {
  flex-shrink: 0;
  font-weight: 600;
  color: var(--iot-color-primary);
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 3px;
  background: color-mix(in srgb, var(--iot-color-primary) 12%, transparent);
}

.hint-values {
  font-family: 'Courier New', monospace;
  font-size: 11px;
  color: var(--iot-text-secondary);
  word-break: break-all;
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

.script-hints {
  display: flex;
  gap: 6px;
}

/* CodeMirror 容器 */
.script-codemirror {
  border-radius: 0 0 var(--iot-radius-base) var(--iot-radius-base);
  overflow: hidden;
}

/* 强制 CodeMirror 编辑区铺满 */
:deep(.cm-editor) {
  min-height: 400px;
  font-family: 'Fira Code', 'Courier New', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.6;
}

:deep(.cm-scroller) {
  min-height: 400px;
  overflow: auto;
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

.terminal-badge--success { background: #a6e3a1; color: #1e1e2e; }
.terminal-badge--error   { background: #f38ba8; color: #1e1e2e; }
.terminal-badge--info    { background: #89b4fa; color: #1e1e2e; }
.terminal-badge--warn    { background: #f9e2af; color: #1e1e2e; }

.terminal-msg { word-break: break-all; }
.terminal-line--success .terminal-msg { color: #a6e3a1; }
.terminal-line--error   .terminal-msg { color: #f38ba8; }
.terminal-line--warn    .terminal-msg { color: #f9e2af; }

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

.guide-code {
  margin: 0;
  padding: 10px 12px;
  background: var(--iot-bg-page);
  border-radius: var(--iot-radius-base);
  font-family: 'Fira Code', 'Courier New', monospace;
  font-size: 11px;
  line-height: 1.6;
  color: var(--iot-text-primary);
  overflow-x: auto;
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
