<template>
  <div class="sensors-view">
    <div class="iot-page-header">
      <div>
        <h1 class="iot-page-title">传感器管理</h1>
        <p class="iot-page-subtitle">查看和管理所有传感器设备</p>
      </div>
    </div>

    <!-- ==================== 传感器类型管理 ==================== -->
    <div class="iot-card iot-mb-lg">
      <div class="iot-card__header">
        <span class="section-title">传感器类型管理</span>
        <el-button v-if="isStaff" type="primary" :icon="Plus" @click="openSensorTypeDialog(null)">
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
          <el-table-column v-if="isStaff" label="操作" width="160" align="center" fixed="right">
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

    <!-- 筛选栏 -->
    <div class="iot-card iot-mb-lg">
      <div class="filter-bar">
        <el-select v-model="filterType" placeholder="传感器类型" style="width: 200px" clearable @change="fetchSensors">
          <el-option label="全部类型" value="" />
          <el-option
            v-for="t in sensorTypes"
            :key="t.id"
            :label="t.name"
            :value="t.id"
          />
        </el-select>
        <el-select v-model="filterOnline" placeholder="在线状态" style="width: 140px" clearable @change="fetchSensors">
          <el-option label="全部" value="" />
          <el-option label="在线" value="true" />
          <el-option label="离线" value="false" />
        </el-select>
        <el-input
          v-model="searchText"
          placeholder="搜索传感器名称或ID"
          style="width: 260px"
          clearable
          @clear="fetchSensors"
          @keyup.enter="fetchSensors"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button :icon="Refresh" circle @click="fetchSensors" />
        <el-button v-if="isStaff && sensors.length" type="primary" :icon="Plus" @click="openAddDialog">添加传感器</el-button>
      </div>
    </div>

    <!-- 卡片网格 -->
    <div v-loading="loading">
      <div v-if="sensors.length" class="iot-grid iot-grid--cards">
        <SensorCard
          v-for="s in sensors"
          :key="s.sensor_id"
          :sensor="s"
          @click="goDetail(s)"
          @delete="handleDeleteSensor"
        />
      </div>
      <div v-else class="iot-card empty-card">
        <el-empty :description="loading ? '加载中...' : '暂无传感器'">
          <el-button v-if="isStaff" type="primary" :icon="Plus" @click="openAddDialog">添加传感器</el-button>
        </el-empty>
      </div>
    </div>

    <!-- 传感器类型编辑弹窗 -->
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

    <!-- 添加传感器弹窗 -->
    <el-dialog v-model="addDialogVisible" title="添加传感器" width="500px" destroy-on-close>
      <el-form :model="addForm" label-width="100px" :rules="addRules" ref="addFormRef">
        <el-form-item label="传感器 ID" prop="sensor_id">
          <el-input v-model="addForm.sensor_id" placeholder="如: DHT11-WEMOS-001" />
        </el-form-item>
        <el-form-item label="名称" prop="name">
          <el-input v-model="addForm.name" placeholder="如: 温湿度传感器-001" />
        </el-form-item>
        <el-form-item label="传感器类型" prop="sensor_type">
          <el-select v-model="addForm.sensor_type" placeholder="选择类型" style="width: 100%">
            <el-option
              v-for="t in sensorTypes"
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
        <el-button type="primary" :loading="addSaving" @click="handleAddSensor">保存</el-button>
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
import { getSensors, createSensor, deleteSensor, getSensorTypes, createSensorType, updateSensorType, deleteSensorType } from '@/api/sensors'
import SensorCard from '@/components/sensors/SensorCard.vue'

const router = useRouter()
const userStore = useUserStore()
const isStaff = computed(() => userStore.userInfo?.is_staff === true)

// ==================== 筛选 ====================
const filterType = ref('')
const filterOnline = ref('')
const searchText = ref('')

// ==================== 数据 ====================
const sensors = ref([])
const sensorTypes = ref([])
const loading = ref(false)
const sensorTypesLoading = ref(false)

async function fetchSensors() {
  loading.value = true
  try {
    const params = {}
    if (filterType.value) params.sensor_type = filterType.value
    if (filterOnline.value) params.online = filterOnline.value
    if (searchText.value) params.search = searchText.value
    const data = await getSensors(params)
    sensors.value = data.results || data
  } catch {
    ElMessage.error('获取传感器列表失败')
  } finally {
    loading.value = false
  }
}

async function fetchSensorTypeList() {
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

// ==================== 传感器类型管理 ====================
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
    fetchSensorTypeList()
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
    fetchSensorTypeList()
  } catch {
    ElMessage.error('删除失败，可能有关联的传感器')
  }
}

// ==================== 跳转详情 ====================
function goDetail(sensor) {
  router.push({ name: 'SensorDetail', params: { sensorId: sensor.sensor_id } })
}

// ==================== 删除传感器 ====================
async function handleDeleteSensor(sensor) {
  try {
    await ElMessageBox.confirm(
      `确定要删除传感器「${sensor.name}」吗？相关数据也将被清除，此操作不可恢复。`,
      '删除确认',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  try {
    await deleteSensor(sensor.sensor_id)
    ElMessage.success('传感器已删除')
    fetchSensors()
  } catch {
    ElMessage.error('删除失败，请重试')
  }
}

// ==================== 添加传感器 ====================
const addDialogVisible = ref(false)
const addSaving = ref(false)
const addFormRef = ref(null)
const addForm = ref({
  sensor_id: '',
  name: '',
  sensor_type: null,
  location: '',
  description: '',
})

const addRules = {
  sensor_id: [{ required: true, message: '请输入传感器 ID', trigger: 'blur' }],
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  sensor_type: [{ required: true, message: '请选择传感器类型', trigger: 'change' }],
}

function openAddDialog() {
  addForm.value = { sensor_id: '', name: '', sensor_type: null, location: '', description: '' }
  addDialogVisible.value = true
}

async function handleAddSensor() {
  const formEl = addFormRef.value
  if (formEl) {
    const valid = await formEl.validate().catch(() => false)
    if (!valid) return
  }
  addSaving.value = true
  try {
    await createSensor(addForm.value)
    ElMessage.success('传感器添加成功')
    addDialogVisible.value = false
    fetchSensors()
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
  fetchSensors()
  fetchSensorTypeList()
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
