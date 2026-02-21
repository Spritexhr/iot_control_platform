<template>
  <div class="settings-view">
    <div class="iot-page-header">
      <div>
        <h1 class="iot-page-title">系统设置</h1>
        <p class="iot-page-subtitle">平台配置与状态监控</p>
      </div>
    </div>

    <!-- ==================== MQTT 连接状态 ==================== -->
    <div class="iot-card iot-mb-lg">
      <div class="iot-card__header">
        <span class="section-title">MQTT 连接状态</span>
        <el-button text :icon="Refresh" :loading="mqttLoading" @click="fetchMqttStatus">
          刷新
        </el-button>
      </div>
      <div class="iot-card__body">
        <div class="setting-item">
          <span class="setting-label">Broker 地址</span>
          <span class="setting-value">{{ mqttInfo.broker || '--' }}:{{ mqttInfo.port || '--' }}</span>
        </div>
        <div class="setting-item">
          <span class="setting-label">连接状态</span>
          <span
            class="iot-status-tag"
            :class="mqttInfo.is_connected ? 'iot-status-tag--online' : 'iot-status-tag--offline'"
          >
            <span
              class="iot-status-dot"
              :class="mqttInfo.is_connected ? 'iot-status-dot--online' : 'iot-status-dot--offline'"
            ></span>
            {{ mqttInfo.is_connected ? '已连接' : '未连接' }}
          </span>
        </div>
      </div>
    </div>

    <!-- ==================== 传感器类型管理 ==================== -->
    <div class="iot-card iot-mb-lg">
      <div class="iot-card__header">
        <span class="section-title">传感器类型管理</span>
        <el-button type="primary" :icon="Plus" @click="openSensorTypeDialog(null)">
          新增类型
        </el-button>
      </div>
      <div class="iot-card__body">
        <el-table :data="sensorTypes" v-loading="sensorTypesLoading" stripe>
          <el-table-column prop="SensorType_id" label="类型ID" width="160" />
          <el-table-column prop="name" label="名称" width="180" />
          <el-table-column label="数据字段" min-width="200">
            <template #default="{ row }">
              <el-tag
                v-for="field in (row.data_fields || [])"
                :key="field"
                size="small"
                class="field-tag"
              >
                {{ field }}
              </el-tag>
              <span v-if="!row.data_fields || row.data_fields.length === 0" class="iot-text-secondary">-</span>
            </template>
          </el-table-column>
          <el-table-column label="命令数" width="80" align="center">
            <template #default="{ row }">
              {{ row.commands ? Object.keys(row.commands).length : 0 }}
            </template>
          </el-table-column>
          <el-table-column label="关联传感器" width="100" align="center">
            <template #default="{ row }">
              <el-tag size="small" type="info">{{ row.sensor_count || 0 }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="160" align="center" fixed="right">
            <template #default="{ row }">
              <el-button text type="primary" size="small" @click="openSensorTypeDialog(row)">
                编辑
              </el-button>
              <el-popconfirm
                title="确定删除此传感器类型？"
                confirm-button-text="删除"
                cancel-button-text="取消"
                @confirm="handleDeleteSensorType(row.id)"
              >
                <template #reference>
                  <el-button text type="danger" size="small">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- ==================== 设备类型管理 ==================== -->
    <div class="iot-card iot-mb-lg">
      <div class="iot-card__header">
        <span class="section-title">设备类型管理</span>
        <el-button type="primary" :icon="Plus" @click="openDeviceTypeDialog(null)">
          新增类型
        </el-button>
      </div>
      <div class="iot-card__body">
        <el-table :data="deviceTypes" v-loading="deviceTypesLoading" stripe>
          <el-table-column prop="DeviceType_id" label="类型ID" width="160" />
          <el-table-column prop="name" label="名称" width="180" />
          <el-table-column label="状态字段" min-width="200">
            <template #default="{ row }">
              <el-tag
                v-for="field in (row.state_fields || [])"
                :key="field"
                size="small"
                type="warning"
                class="field-tag"
              >
                {{ field }}
              </el-tag>
              <span v-if="!row.state_fields || row.state_fields.length === 0" class="iot-text-secondary">-</span>
            </template>
          </el-table-column>
          <el-table-column label="命令数" width="80" align="center">
            <template #default="{ row }">
              {{ row.commands ? Object.keys(row.commands).length : 0 }}
            </template>
          </el-table-column>
          <el-table-column label="关联设备" width="100" align="center">
            <template #default="{ row }">
              <el-tag size="small" type="info">{{ row.device_count || 0 }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="160" align="center" fixed="right">
            <template #default="{ row }">
              <el-button text type="primary" size="small" @click="openDeviceTypeDialog(row)">
                编辑
              </el-button>
              <el-popconfirm
                title="确定删除此设备类型？"
                confirm-button-text="删除"
                cancel-button-text="取消"
                @confirm="handleDeleteDeviceType(row.id)"
              >
                <template #reference>
                  <el-button text type="danger" size="small">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- ==================== 传感器类型编辑弹窗 ==================== -->
    <el-dialog
      v-model="sensorTypeDialogVisible"
      :title="sensorTypeForm.id ? '编辑传感器类型' : '新增传感器类型'"
      width="600px"
      destroy-on-close
    >
      <el-form :model="sensorTypeForm" label-width="100px" :rules="sensorTypeRules" ref="sensorTypeFormRef">
        <el-form-item label="类型 ID" prop="SensorType_id">
          <el-input v-model="sensorTypeForm.SensorType_id" placeholder="如: DHT11-01" />
        </el-form-item>
        <el-form-item label="名称" prop="name">
          <el-input v-model="sensorTypeForm.name" placeholder="如: DHT11 温湿度传感器" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="sensorTypeForm.description" type="textarea" :rows="2" placeholder="类型描述（选填）" />
        </el-form-item>
        <el-form-item label="数据字段">
          <el-select
            v-model="sensorTypeForm.data_fields"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="输入字段名后回车添加，如 temperature"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="配置参数">
          <el-select
            v-model="sensorTypeForm.config_parameters"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="输入参数名后回车添加，如 samplingInterval"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="命令列表">
          <div class="commands-editor">
            <el-input
              v-model="sensorTypeForm.commands_json"
              type="textarea"
              :rows="6"
              placeholder='JSON 格式，如: {"turn_on": {"mqtt_message": {"command": "enable"}, "description": "启动", "params": []}}'
            />
            <div v-if="sensorTypeCmdError" class="cmd-error">{{ sensorTypeCmdError }}</div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="sensorTypeDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="sensorTypeSaving" @click="handleSaveSensorType">
          保存
        </el-button>
      </template>
    </el-dialog>

    <!-- ==================== 设备类型编辑弹窗 ==================== -->
    <el-dialog
      v-model="deviceTypeDialogVisible"
      :title="deviceTypeForm.id ? '编辑设备类型' : '新增设备类型'"
      width="600px"
      destroy-on-close
    >
      <el-form :model="deviceTypeForm" label-width="100px" :rules="deviceTypeRules" ref="deviceTypeFormRef">
        <el-form-item label="类型 ID" prop="DeviceType_id">
          <el-input v-model="deviceTypeForm.DeviceType_id" placeholder="如: LED-01" />
        </el-form-item>
        <el-form-item label="名称" prop="name">
          <el-input v-model="deviceTypeForm.name" placeholder="如: LED灯" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="deviceTypeForm.description" type="textarea" :rows="2" placeholder="类型描述（选填）" />
        </el-form-item>
        <el-form-item label="状态字段">
          <el-select
            v-model="deviceTypeForm.state_fields"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="输入字段名后回车添加，如 power_state"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="配置参数">
          <el-select
            v-model="deviceTypeForm.config_parameters"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="输入参数名后回车添加，如 heartbeat_interval"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="命令列表">
          <div class="commands-editor">
            <el-input
              v-model="deviceTypeForm.commands_json"
              type="textarea"
              :rows="6"
              placeholder='JSON 格式，如: {"turn_on": {"mqtt_message": {"command": "power_on"}, "description": "打开设备", "params": []}}'
            />
            <div v-if="deviceTypeCmdError" class="cmd-error">{{ deviceTypeCmdError }}</div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="deviceTypeDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="deviceTypeSaving" @click="handleSaveDeviceType">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { getMqttStatus } from '@/api/system'
import { getSensorTypes, createSensorType, updateSensorType, deleteSensorType } from '@/api/sensors'
import { getDeviceTypes, createDeviceType, updateDeviceType, deleteDeviceType } from '@/api/devices'

// ==================== MQTT 状态 ====================
const mqttInfo = ref({ broker: '', port: '', is_connected: false })
const mqttLoading = ref(false)

async function fetchMqttStatus() {
  mqttLoading.value = true
  try {
    const data = await getMqttStatus()
    mqttInfo.value = data
  } catch {
    mqttInfo.value = { broker: '--', port: '--', is_connected: false }
  } finally {
    mqttLoading.value = false
  }
}

// ==================== 传感器类型管理 ====================
const sensorTypes = ref([])
const sensorTypesLoading = ref(false)
const sensorTypeDialogVisible = ref(false)
const sensorTypeSaving = ref(false)
const sensorTypeFormRef = ref(null)
const sensorTypeCmdError = ref('')

const sensorTypeRules = {
  SensorType_id: [{ required: true, message: '请输入类型 ID', trigger: 'blur' }],
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
}

const emptySensorTypeForm = () => ({
  id: null,
  SensorType_id: '',
  name: '',
  description: '',
  data_fields: [],
  config_parameters: [],
  commands_json: '{}',
})

const sensorTypeForm = ref(emptySensorTypeForm())

async function fetchSensorTypes() {
  sensorTypesLoading.value = true
  try {
    const data = await getSensorTypes()
    sensorTypes.value = data.results || data
  } catch {
    ElMessage.error('获取传感器类型列表失败')
  } finally {
    sensorTypesLoading.value = false
  }
}

function openSensorTypeDialog(row) {
  sensorTypeCmdError.value = ''
  if (row) {
    sensorTypeForm.value = {
      id: row.id,
      SensorType_id: row.SensorType_id,
      name: row.name,
      description: row.description || '',
      data_fields: row.data_fields || [],
      config_parameters: row.config_parameters || [],
      commands_json: JSON.stringify(row.commands || {}, null, 2),
    }
  } else {
    sensorTypeForm.value = emptySensorTypeForm()
  }
  sensorTypeDialogVisible.value = true
}

async function handleSaveSensorType() {
  const formEl = sensorTypeFormRef.value
  if (formEl) {
    const valid = await formEl.validate().catch(() => false)
    if (!valid) return
  }

  let commands
  try {
    commands = JSON.parse(sensorTypeForm.value.commands_json)
    sensorTypeCmdError.value = ''
  } catch {
    sensorTypeCmdError.value = 'JSON 格式不正确，请检查'
    return
  }

  const payload = {
    SensorType_id: sensorTypeForm.value.SensorType_id,
    name: sensorTypeForm.value.name,
    description: sensorTypeForm.value.description,
    data_fields: sensorTypeForm.value.data_fields,
    config_parameters: sensorTypeForm.value.config_parameters,
    commands: commands,
  }

  sensorTypeSaving.value = true
  try {
    if (sensorTypeForm.value.id) {
      await updateSensorType(sensorTypeForm.value.id, payload)
      ElMessage.success('传感器类型更新成功')
    } else {
      await createSensorType(payload)
      ElMessage.success('传感器类型创建成功')
    }
    sensorTypeDialogVisible.value = false
    fetchSensorTypes()
  } catch (err) {
    const detail = err.response?.data
    const msg = typeof detail === 'object' ? Object.values(detail).flat().join('；') : '保存失败'
    ElMessage.error(msg)
  } finally {
    sensorTypeSaving.value = false
  }
}

async function handleDeleteSensorType(id) {
  try {
    await deleteSensorType(id)
    ElMessage.success('删除成功')
    fetchSensorTypes()
  } catch {
    ElMessage.error('删除失败，可能有关联的传感器')
  }
}

// ==================== 设备类型管理 ====================
const deviceTypes = ref([])
const deviceTypesLoading = ref(false)
const deviceTypeDialogVisible = ref(false)
const deviceTypeSaving = ref(false)
const deviceTypeFormRef = ref(null)
const deviceTypeCmdError = ref('')

const deviceTypeRules = {
  DeviceType_id: [{ required: true, message: '请输入类型 ID', trigger: 'blur' }],
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
}

const emptyDeviceTypeForm = () => ({
  id: null,
  DeviceType_id: '',
  name: '',
  description: '',
  state_fields: [],
  config_parameters: [],
  commands_json: '{}',
})

const deviceTypeForm = ref(emptyDeviceTypeForm())

async function fetchDeviceTypes() {
  deviceTypesLoading.value = true
  try {
    const data = await getDeviceTypes()
    deviceTypes.value = data.results || data
  } catch {
    ElMessage.error('获取设备类型列表失败')
  } finally {
    deviceTypesLoading.value = false
  }
}

function openDeviceTypeDialog(row) {
  deviceTypeCmdError.value = ''
  if (row) {
    deviceTypeForm.value = {
      id: row.id,
      DeviceType_id: row.DeviceType_id,
      name: row.name,
      description: row.description || '',
      state_fields: row.state_fields || [],
      config_parameters: row.config_parameters || [],
      commands_json: JSON.stringify(row.commands || {}, null, 2),
    }
  } else {
    deviceTypeForm.value = emptyDeviceTypeForm()
  }
  deviceTypeDialogVisible.value = true
}

async function handleSaveDeviceType() {
  const formEl = deviceTypeFormRef.value
  if (formEl) {
    const valid = await formEl.validate().catch(() => false)
    if (!valid) return
  }

  let commands
  try {
    commands = JSON.parse(deviceTypeForm.value.commands_json)
    deviceTypeCmdError.value = ''
  } catch {
    deviceTypeCmdError.value = 'JSON 格式不正确，请检查'
    return
  }

  const payload = {
    DeviceType_id: deviceTypeForm.value.DeviceType_id,
    name: deviceTypeForm.value.name,
    description: deviceTypeForm.value.description,
    state_fields: deviceTypeForm.value.state_fields,
    config_parameters: deviceTypeForm.value.config_parameters,
    commands: commands,
  }

  deviceTypeSaving.value = true
  try {
    if (deviceTypeForm.value.id) {
      await updateDeviceType(deviceTypeForm.value.id, payload)
      ElMessage.success('设备类型更新成功')
    } else {
      await createDeviceType(payload)
      ElMessage.success('设备类型创建成功')
    }
    deviceTypeDialogVisible.value = false
    fetchDeviceTypes()
  } catch (err) {
    const detail = err.response?.data
    const msg = typeof detail === 'object' ? Object.values(detail).flat().join('；') : '保存失败'
    ElMessage.error(msg)
  } finally {
    deviceTypeSaving.value = false
  }
}

async function handleDeleteDeviceType(id) {
  try {
    await deleteDeviceType(id)
    ElMessage.success('删除成功')
    fetchDeviceTypes()
  } catch {
    ElMessage.error('删除失败，可能有关联的设备')
  }
}

// ==================== 初始化 ====================
onMounted(() => {
  fetchMqttStatus()
  fetchSensorTypes()
  fetchDeviceTypes()
})
</script>

<style scoped>
.section-title {
  font-weight: 600;
  font-size: var(--iot-font-size-md);
}

.setting-item {
  display: flex;
  align-items: center;
  padding: var(--iot-spacing-sm) 0;
  border-bottom: 1px solid var(--iot-border-color-light);
}

.setting-item:last-child {
  border-bottom: none;
}

.setting-label {
  width: 140px;
  color: var(--iot-text-secondary);
  font-size: var(--iot-font-size-sm);
  flex-shrink: 0;
}

.setting-value {
  color: var(--iot-text-primary);
  font-family: 'Courier New', monospace;
}

.field-tag {
  margin: 2px 4px 2px 0;
}

.commands-editor {
  width: 100%;
}

.cmd-error {
  color: var(--iot-color-danger);
  font-size: var(--iot-font-size-xs);
  margin-top: 4px;
}
</style>
