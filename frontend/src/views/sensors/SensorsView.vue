<template>
  <div class="sensors-view">
    <div class="iot-page-header">
      <div>
        <h1 class="iot-page-title">{{ ls.t('sensors.title') }}</h1>
        <p class="iot-page-subtitle">{{ ls.t('sensors.subtitle') }}</p>
      </div>
    </div>

    <!-- ==================== 传感器类型管理 ==================== -->
    <div class="iot-card iot-mb-lg">
      <div class="iot-card__header">
        <span class="section-title">{{ ls.t('sensors.typeManagement') }}</span>
        <el-button v-if="isStaff" type="primary" :icon="Plus" @click="openSensorTypeDialog(null)">
          {{ ls.t('sensors.addType') }}
        </el-button>
      </div>
      <div class="iot-card__body">
        <el-table :data="sensorTypes" v-loading="sensorTypesLoading" stripe>
          <el-table-column prop="SensorType_id" :label="ls.t('common.typeId')" width="160" />
          <el-table-column prop="name" :label="ls.t('common.name')" width="180" />
          <el-table-column :label="ls.t('sensors.dataFields')" min-width="200">
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
          <el-table-column :label="ls.t('common.cmdCount')" width="80" align="center">
            <template #default="{ row }">
              {{ row.commands ? Object.keys(row.commands).length : 0 }}
            </template>
          </el-table-column>
          <el-table-column :label="ls.t('sensors.relatedSensors')" width="100" align="center">
            <template #default="{ row }">
              <el-tag size="small" type="info">{{ row.sensor_count || 0 }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column v-if="isStaff" :label="ls.t('common.operations')" width="160" align="center" fixed="right">
            <template #default="{ row }">
              <el-button text type="primary" size="small" @click="openSensorTypeDialog(row)">
                {{ ls.t('common.edit') }}
              </el-button>
              <el-popconfirm
                :title="ls.t('sensors.deleteTypeConfirm')"
                :confirm-button-text="ls.t('common.delete')"
                :cancel-button-text="ls.t('common.cancel')"
                @confirm="handleDeleteSensorType(row.id)"
              >
                <template #reference>
                  <el-button text type="danger" size="small">{{ ls.t('common.delete') }}</el-button>
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
        <el-select v-model="filterType" :placeholder="ls.t('sensors.filterType')" style="width: 200px" clearable @change="fetchSensors">
          <el-option :label="ls.t('common.allTypes')" value="" />
          <el-option
            v-for="t in sensorTypes"
            :key="t.id"
            :label="t.name"
            :value="t.id"
          />
        </el-select>
        <el-select v-model="filterOnline" :placeholder="ls.t('sensors.filterStatus')" style="width: 140px" clearable @change="fetchSensors">
          <el-option :label="ls.t('common.all')" value="" />
          <el-option :label="ls.t('common.online')" value="true" />
          <el-option :label="ls.t('common.offline')" value="false" />
        </el-select>
        <el-input
          v-model="searchText"
          :placeholder="ls.t('sensors.searchPlaceholder')"
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
        <el-button v-if="isStaff && sensors.length" type="primary" :icon="Plus" @click="openAddDialog">{{ ls.t('sensors.addSensor') }}</el-button>
      </div>
    </div>

    <!-- 卡片网格 -->
    <div v-loading="loading">
      <draggable
        v-if="sensors.length"
        v-model="sensors"
        :item-key="'sensor_id'"
        :disabled="!isStaff || hasActiveFilter"
        :animation="200"
        ghost-class="drag-ghost"
        handle=".sensor-drag-handle, .iot-card"
        class="iot-grid iot-grid--cards"
        @end="handleReorderEnd"
      >
        <template #item="{ element: s }">
          <SensorCard
            :sensor="s"
            @click="goDetail(s)"
            @delete="handleDeleteSensor"
          />
        </template>
      </draggable>
      <div v-if="!sensors.length" class="iot-card empty-card">
        <el-empty :description="loading ? ls.t('common.loading') : ls.t('sensors.noSensors')">
          <el-button v-if="isStaff" type="primary" :icon="Plus" @click="openAddDialog">{{ ls.t('sensors.addSensor') }}</el-button>
        </el-empty>
      </div>
    </div>

    <!-- 传感器类型编辑弹窗 -->
    <el-dialog
      v-model="sensorTypeDialogVisible"
      :title="sensorTypeForm.id ? ls.t('sensors.editTypeTitle') : ls.t('sensors.addTypeTitle')"
      width="600px"
      destroy-on-close
    >
      <el-form :model="sensorTypeForm" label-width="100px" :rules="sensorTypeRules" ref="sensorTypeFormRef">
        <el-form-item :label="ls.t('sensors.typeIdLabel')" prop="SensorType_id">
          <el-input v-model="sensorTypeForm.SensorType_id" :placeholder="ls.t('sensors.typeIdPlaceholder')" />
        </el-form-item>
        <el-form-item :label="ls.t('common.name')" prop="name">
          <el-input v-model="sensorTypeForm.name" :placeholder="ls.t('sensors.namePlaceholder')" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="sensorTypeForm.description" type="textarea" :rows="2" :placeholder="ls.t('sensors.descPlaceholder')" />
        </el-form-item>
        <el-form-item :label="ls.t('sensors.dataFields')">
          <el-select
            v-model="sensorTypeForm.data_fields"
            multiple
            filterable
            allow-create
            default-first-option
            :placeholder="ls.t('sensors.dataFieldsPlaceholder')"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item :label="ls.t('sensors.configParamsLabel')">
          <el-select
            v-model="sensorTypeForm.config_parameters"
            multiple
            filterable
            allow-create
            default-first-option
            :placeholder="ls.t('sensors.configParamsPlaceholder')"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item :label="ls.t('sensors.commandsLabel')">
          <div class="commands-editor">
            <el-input
              v-model="sensorTypeForm.commands_json"
              type="textarea"
              :rows="6"
              :placeholder="ls.t('sensors.commandsPlaceholder')"
            />
            <div v-if="sensorTypeCmdError" class="cmd-error">{{ sensorTypeCmdError }}</div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="sensorTypeDialogVisible = false">{{ ls.t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="sensorTypeSaving" @click="handleSaveSensorType">
          保存
        </el-button>
      </template>
    </el-dialog>

    <!-- 添加传感器弹窗 -->
    <el-dialog v-model="addDialogVisible" :title="ls.t('sensors.addDialogTitle')" width="500px" destroy-on-close>
      <el-form :model="addForm" label-width="100px" :rules="addRules" ref="addFormRef">
        <el-form-item :label="ls.t('sensors.sensorIdLabel')" prop="sensor_id">
          <el-input v-model="addForm.sensor_id" :placeholder="ls.t('sensors.sensorIdPlaceholder')" />
        </el-form-item>
        <el-form-item :label="ls.t('common.name')" prop="name">
          <el-input v-model="addForm.name" :placeholder="ls.t('sensors.sensorNamePlaceholder')" />
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
          <el-input v-model="addForm.location" :placeholder="ls.t('sensors.locationPlaceholder')" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="addForm.description" type="textarea" :rows="2" :placeholder="ls.t('common.optional')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialogVisible = false">{{ ls.t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="addSaving" @click="handleAddSensor">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useLocaleStore } from '@/stores/locale'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh } from '@element-plus/icons-vue'
import { getSensors, createSensor, deleteSensor, getSensorTypes, createSensorType, updateSensorType, deleteSensorType, reorderSensors } from '@/api/sensors'
import SensorCard from '@/components/sensors/SensorCard.vue'
import draggable from 'vuedraggable'

const router = useRouter()
const userStore = useUserStore()
const ls = useLocaleStore()
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
    ElMessage.error(ls.t('sensors.fetchListFailed'))
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
    ElMessage.error(ls.t('sensors.fetchTypesFailed'))
  } finally {
    sensorTypesLoading.value = false
  }
}

// ==================== 传感器类型管理 ====================
const sensorTypeDialogVisible = ref(false)
const sensorTypeSaving = ref(false)
const sensorTypeFormRef = ref(null)
const sensorTypeCmdError = ref('')

const sensorTypeRules = computed(() => ({
  SensorType_id: [{ required: true, message: ls.t('sensors.typeIdRequired'), trigger: 'blur' }],
  name: [{ required: true, message: ls.t('sensors.nameRequired'), trigger: 'blur' }],
}))

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
    sensorTypeCmdError.value = ls.t('common.jsonError')
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
      ElMessage.success(ls.t('sensors.typeUpdated'))
    } else {
      await createSensorType(payload)
      ElMessage.success(ls.t('sensors.typeCreated'))
    }
    sensorTypeDialogVisible.value = false
    fetchSensorTypeList()
  } catch (err) {
    const detail = err.response?.data
    const msg = typeof detail === 'object' ? Object.values(detail).flat().join('；') : ls.t('common.saveFailed')
    ElMessage.error(msg)
  } finally {
    sensorTypeSaving.value = false
  }
}

async function handleDeleteSensorType(id) {
  try {
    await deleteSensorType(id)
    ElMessage.success(ls.t('common.deleteSuccess'))
    fetchSensorTypeList()
  } catch {
    ElMessage.error(ls.t('sensors.deleteTypeFailed'))
  }
}

// ==================== 拖拽排序 ====================
const hasActiveFilter = computed(() =>
  Boolean(filterType.value || filterOnline.value || searchText.value)
)

async function handleReorderEnd(evt) {
  // 顺序未变就不发请求
  if (evt && evt.oldIndex === evt.newIndex) return
  const order = sensors.value.map(s => s.sensor_id)
  try {
    await reorderSensors(order)
  } catch {
    ElMessage.error(ls.t('sensors.reorderFailed') || '排序保存失败')
    fetchSensors()
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
      ls.t('sensors.deleteConfirmMsg').replace('{name}', sensor.name),
      ls.t('common.deleteConfirmTitle'),
      { confirmButtonText: ls.t('common.deleteConfirmOk'), cancelButtonText: ls.t('common.cancel'), type: 'warning' }
    )
  } catch {
    return
  }
  try {
    await deleteSensor(sensor.sensor_id)
    ElMessage.success(ls.t('sensors.sensorDeleted'))
    fetchSensors()
  } catch {
    ElMessage.error(ls.t('common.deleteFailed'))
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

const addRules = computed(() => ({
  sensor_id: [{ required: true, message: ls.t('sensors.sensorIdRequired'), trigger: 'blur' }],
  name: [{ required: true, message: ls.t('sensors.sensorNameRequired'), trigger: 'blur' }],
  sensor_type: [{ required: true, message: ls.t('sensors.sensorTypeRequired'), trigger: 'change' }],
}))

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
    ElMessage.success(ls.t('sensors.sensorAdded'))
    addDialogVisible.value = false
    fetchSensors()
  } catch (err) {
    const detail = err.response?.data
    const msg = typeof detail === 'object' ? Object.values(detail).flat().join('；') : ls.t('common.addFailed')
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
  background-color: var(--iot-color-primary-bg) !important;
  border-color: transparent !important;
  color: var(--iot-color-primary-dark) !important;
}

html.dark .field-tag {
  color: var(--iot-color-primary-light) !important;
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

.drag-ghost {
  opacity: 0.4;
  background: var(--iot-color-fill-light, rgba(0, 0, 0, 0.04));
  border: 2px dashed var(--iot-color-primary, #d97757);
  border-radius: var(--iot-border-radius-md, 8px);
}
</style>
