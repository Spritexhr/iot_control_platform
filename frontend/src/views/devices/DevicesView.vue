<template>
  <div class="devices-view">
    <div class="iot-page-header">
      <div>
        <h1 class="iot-page-title">设备管理</h1>
        <p class="iot-page-subtitle">查看和控制所有执行器设备</p>
      </div>
    </div>

    <!-- ==================== 设备类型管理 ==================== -->
    <div class="iot-card iot-mb-lg">
      <div class="iot-card__header">
        <span class="section-title">设备类型管理</span>
        <el-button v-if="isStaff" type="primary" :icon="Plus" @click="openDeviceTypeDialog(null)">
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
          <el-table-column v-if="isStaff" label="操作" width="160" align="center" fixed="right">
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

    <!-- 筛选栏 -->
    <div class="iot-card iot-mb-lg">
      <div class="filter-bar">
        <el-select v-model="filterType" placeholder="设备类型" style="width: 200px" clearable @change="fetchDevices">
          <el-option label="全部类型" value="" />
          <el-option
            v-for="t in deviceTypes"
            :key="t.id"
            :label="t.name"
            :value="t.id"
          />
        </el-select>
        <el-select v-model="filterOnline" placeholder="在线状态" style="width: 140px" clearable @change="fetchDevices">
          <el-option label="全部" value="" />
          <el-option label="在线" value="true" />
          <el-option label="离线" value="false" />
        </el-select>
        <el-input
          v-model="searchText"
          placeholder="搜索设备名称或ID"
          style="width: 260px"
          clearable
          @clear="fetchDevices"
          @keyup.enter="fetchDevices"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button :icon="Refresh" circle @click="fetchDevices" />
        <el-button v-if="isStaff && devices.length" type="primary" :icon="Plus" @click="openAddDialog">添加设备</el-button>
      </div>
    </div>

    <!-- 卡片网格 / 空状态 -->
    <div v-loading="loading">
      <div v-if="devices.length" class="iot-grid iot-grid--cards">
        <DeviceCard
          v-for="d in devices"
          :key="d.device_id"
          :device="d"
          @click="goDetail(d)"
          @delete="handleDeleteDevice"
        />
      </div>
      <div v-else class="iot-card empty-card">
        <el-empty :description="loading ? '加载中...' : '暂无设备'">
          <el-button v-if="isStaff" type="primary" :icon="Plus" @click="openAddDialog">添加设备</el-button>
        </el-empty>
      </div>
    </div>

    <!-- 设备类型编辑弹窗 -->
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

    <!-- 添加设备弹窗 -->
    <el-dialog v-model="addDialogVisible" title="添加设备" width="500px" destroy-on-close>
      <el-form :model="addForm" label-width="100px" :rules="addRules" ref="addFormRef">
        <el-form-item label="设备 ID" prop="device_id">
          <el-input v-model="addForm.device_id" placeholder="如: LED-WEMOS-001" />
        </el-form-item>
        <el-form-item label="名称" prop="name">
          <el-input v-model="addForm.name" placeholder="如: LED灯-001" />
        </el-form-item>
        <el-form-item label="设备类型" prop="device_type">
          <el-select v-model="addForm.device_type" placeholder="选择类型" style="width: 100%">
            <el-option
              v-for="t in deviceTypes"
              :key="t.id"
              :label="t.name"
              :value="t.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="位置">
          <el-input v-model="addForm.location" placeholder="如: 实验室A（选填）" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="addForm.description" type="textarea" :rows="2" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="addSaving" @click="handleAddDevice">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh } from '@element-plus/icons-vue'
import { getDevices, createDevice, deleteDevice, getDeviceTypes, createDeviceType, updateDeviceType, deleteDeviceType } from '@/api/devices'
import DeviceCard from '@/components/devices/DeviceCard.vue'

const router = useRouter()
const userStore = useUserStore()
const isStaff = computed(() => userStore.userInfo?.is_staff === true)

// ==================== 筛选 ====================
const filterType = ref('')
const filterOnline = ref('')
const searchText = ref('')

// ==================== 数据 ====================
const devices = ref([])
const deviceTypes = ref([])
const loading = ref(false)
const deviceTypesLoading = ref(false)

async function fetchDevices() {
  loading.value = true
  try {
    const params = {}
    if (filterType.value) params.device_type = filterType.value
    if (filterOnline.value) params.online = filterOnline.value
    if (searchText.value) params.search = searchText.value
    const data = await getDevices(params)
    devices.value = data.results || data
  } catch {
    ElMessage.error('获取设备列表失败')
  } finally {
    loading.value = false
  }
}

async function fetchDeviceTypeList() {
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

// ==================== 设备类型管理 ====================
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
    fetchDeviceTypeList()
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
    fetchDeviceTypeList()
  } catch {
    ElMessage.error('删除失败，可能有关联的设备')
  }
}

// ==================== 跳转详情 ====================
function goDetail(device) {
  router.push({ name: 'DeviceDetail', params: { deviceId: device.device_id } })
}

// ==================== 删除设备 ====================
async function handleDeleteDevice(device) {
  try {
    await ElMessageBox.confirm(
      `确定要删除设备「${device.name}」吗？相关数据也将被清除，此操作不可恢复。`,
      '删除确认',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  try {
    await deleteDevice(device.device_id)
    ElMessage.success('设备已删除')
    fetchDevices()
  } catch {
    ElMessage.error('删除失败，请重试')
  }
}

// ==================== 添加设备 ====================
const addDialogVisible = ref(false)
const addSaving = ref(false)
const addFormRef = ref(null)
const addForm = ref({
  device_id: '',
  name: '',
  device_type: null,
  location: '',
  description: '',
})

const addRules = {
  device_id: [{ required: true, message: '请输入设备 ID', trigger: 'blur' }],
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  device_type: [{ required: true, message: '请选择设备类型', trigger: 'change' }],
}

function openAddDialog() {
  addForm.value = { device_id: '', name: '', device_type: null, location: '', description: '' }
  addDialogVisible.value = true
}

async function handleAddDevice() {
  const formEl = addFormRef.value
  if (formEl) {
    const valid = await formEl.validate().catch(() => false)
    if (!valid) return
  }
  addSaving.value = true
  try {
    await createDevice(addForm.value)
    ElMessage.success('设备添加成功')
    addDialogVisible.value = false
    fetchDevices()
  } catch (err) {
    const detail = err.response?.data
    const msg = typeof detail === 'object' ? Object.values(detail).flat().join('；') : '添加失败'
    ElMessage.error(msg)
  } finally {
    addSaving.value = false
  }
}

// ==================== 初始化 ====================
onMounted(() => {
  fetchDevices()
  fetchDeviceTypeList()
})
</script>

<style scoped>
.section-title {
  font-weight: 600;
  font-size: var(--iot-font-size-md);
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

.filter-bar {
  display: flex;
  align-items: center;
  gap: var(--iot-spacing-md);
  padding: var(--iot-spacing-md) var(--iot-spacing-lg);
  flex-wrap: wrap;
}

.empty-card {
  padding: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
