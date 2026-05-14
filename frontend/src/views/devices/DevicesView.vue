<template>
  <div class="devices-view">
    <div class="iot-page-header">
      <div>
        <h1 class="iot-page-title">{{ ls.t('devices.title') }}</h1>
        <p class="iot-page-subtitle">{{ ls.t('devices.subtitle') }}</p>
      </div>
    </div>

    <!-- ==================== 设备类型管理 ==================== -->
    <div class="iot-card iot-mb-lg">
      <div class="iot-card__header">
        <span class="section-title">{{ ls.t('devices.typeManagement') }}</span>
        <el-button v-if="isStaff" type="primary" :icon="Plus" @click="openDeviceTypeDialog(null)">
          {{ ls.t('devices.addType') }}
        </el-button>
      </div>
      <div class="iot-card__body">
        <el-table :data="deviceTypes" v-loading="deviceTypesLoading" stripe>
          <el-table-column prop="DeviceType_id" :label="ls.t('common.typeId')" width="160" />
          <el-table-column prop="name" :label="ls.t('common.name')" width="180" />
          <el-table-column :label="ls.t('devices.configParams')" min-width="200">
            <template #default="{ row }">
              <el-tag
                v-for="field in (row.config_parameters || [])"
                :key="field"
                size="small"
                type="warning"
                class="field-tag"
              >
                {{ field }}
              </el-tag>
              <span v-if="!row.config_parameters || row.config_parameters.length === 0" class="iot-text-secondary">-</span>
            </template>
          </el-table-column>
          <el-table-column :label="ls.t('common.cmdCount')" width="80" align="center">
            <template #default="{ row }">
              {{ row.commands ? Object.keys(row.commands).length : 0 }}
            </template>
          </el-table-column>
          <el-table-column :label="ls.t('devices.relatedDevices')" width="100" align="center">
            <template #default="{ row }">
              <el-tag size="small" type="info">{{ row.device_count || 0 }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column v-if="isStaff" :label="ls.t('common.operations')" width="160" align="center" fixed="right">
            <template #default="{ row }">
              <el-button text type="primary" size="small" @click="openDeviceTypeDialog(row)">
                {{ ls.t('common.edit') }}
              </el-button>
              <el-popconfirm
                :title="ls.t('devices.deleteTypeConfirm')"
                :confirm-button-text="ls.t('common.delete')"
                :cancel-button-text="ls.t('common.cancel')"
                @confirm="handleDeleteDeviceType(row.id)"
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
        <el-select v-model="filterType" :placeholder="ls.t('devices.filterType')" style="width: 200px" clearable @change="fetchDevices">
          <el-option :label="ls.t('common.allTypes')" value="" />
          <el-option
            v-for="t in deviceTypes"
            :key="t.id"
            :label="t.name"
            :value="t.id"
          />
        </el-select>
        <el-select v-model="filterOnline" :placeholder="ls.t('devices.filterStatus')" style="width: 140px" clearable @change="fetchDevices">
          <el-option :label="ls.t('common.all')" value="" />
          <el-option :label="ls.t('common.online')" value="true" />
          <el-option :label="ls.t('common.offline')" value="false" />
        </el-select>
        <el-input
          v-model="searchText"
          :placeholder="ls.t('devices.searchPlaceholder')"
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
        <el-button v-if="isStaff && devices.length" type="primary" :icon="Plus" @click="openAddDialog">{{ ls.t('devices.addDevice') }}</el-button>
      </div>
    </div>

    <!-- 卡片网格 / 空状态 -->
    <div v-loading="loading">
      <draggable
        v-if="devices.length"
        v-model="devices"
        :item-key="'device_id'"
        :disabled="!isStaff || hasActiveFilter"
        :animation="200"
        ghost-class="drag-ghost"
        handle=".device-drag-handle, .iot-card"
        class="iot-grid iot-grid--cards"
        @end="handleReorderEnd"
      >
        <template #item="{ element: d }">
          <DeviceCard
            :device="d"
            @click="goDetail(d)"
            @delete="handleDeleteDevice"
          />
        </template>
      </draggable>
      <div v-if="!devices.length" class="iot-card empty-card">
        <el-empty :description="loading ? ls.t('common.loading') : ls.t('devices.noDevices')">
          <el-button v-if="isStaff" type="primary" :icon="Plus" @click="openAddDialog">{{ ls.t('devices.addDevice') }}</el-button>
        </el-empty>
      </div>
    </div>

    <!-- 设备类型编辑弹窗 -->
    <el-dialog
      v-model="deviceTypeDialogVisible"
      :title="deviceTypeForm.id ? ls.t('devices.editTypeTitle') : ls.t('devices.addTypeTitle')"
      width="600px"
      destroy-on-close
    >
      <el-form :model="deviceTypeForm" label-width="100px" :rules="deviceTypeRules" ref="deviceTypeFormRef">
        <el-form-item :label="ls.t('devices.typeIdLabel')" prop="DeviceType_id">
          <el-input v-model="deviceTypeForm.DeviceType_id" :placeholder="ls.t('devices.typeIdPlaceholder')" />
        </el-form-item>
        <el-form-item :label="ls.t('common.name')" prop="name">
          <el-input v-model="deviceTypeForm.name" :placeholder="ls.t('devices.namePlaceholder')" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="deviceTypeForm.description" type="textarea" :rows="2" :placeholder="ls.t('devices.descPlaceholder')" />
        </el-form-item>
        <el-form-item :label="ls.t('devices.configParamsLabel')">
          <el-select
            v-model="deviceTypeForm.config_parameters"
            multiple
            filterable
            allow-create
            default-first-option
            :placeholder="ls.t('devices.configParamsPlaceholder')"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item :label="ls.t('devices.commandsLabel')">
          <div class="commands-editor">
            <el-input
              v-model="deviceTypeForm.commands_json"
              type="textarea"
              :rows="6"
              :placeholder="ls.t('devices.commandsPlaceholder')"
            />
            <div v-if="deviceTypeCmdError" class="cmd-error">{{ deviceTypeCmdError }}</div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="deviceTypeDialogVisible = false">{{ ls.t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="deviceTypeSaving" @click="handleSaveDeviceType">
          保存
        </el-button>
      </template>
    </el-dialog>

    <!-- 添加设备弹窗 -->
    <el-dialog v-model="addDialogVisible" :title="ls.t('devices.addDialogTitle')" width="500px" destroy-on-close>
      <el-form :model="addForm" label-width="100px" :rules="addRules" ref="addFormRef">
        <el-form-item :label="ls.t('devices.deviceIdLabel')" prop="device_id">
          <el-input v-model="addForm.device_id" :placeholder="ls.t('devices.deviceIdPlaceholder')" />
        </el-form-item>
        <el-form-item :label="ls.t('common.name')" prop="name">
          <el-input v-model="addForm.name" :placeholder="ls.t('devices.deviceNamePlaceholder')" />
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
          <el-input v-model="addForm.location" :placeholder="ls.t('devices.locationPlaceholder')" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="addForm.description" type="textarea" :rows="2" :placeholder="ls.t('common.optional')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialogVisible = false">{{ ls.t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="addSaving" @click="handleAddDevice">保存</el-button>
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
import { getDevices, createDevice, deleteDevice, getDeviceTypes, createDeviceType, updateDeviceType, deleteDeviceType, reorderDevices } from '@/api/devices'
import draggable from 'vuedraggable'
import DeviceCard from '@/components/devices/DeviceCard.vue'

const router = useRouter()
const userStore = useUserStore()
const ls = useLocaleStore()
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
    ElMessage.error(ls.t('devices.fetchListFailed'))
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
    ElMessage.error(ls.t('devices.fetchTypesFailed'))
  } finally {
    deviceTypesLoading.value = false
  }
}

// ==================== 设备类型管理 ====================
const deviceTypeDialogVisible = ref(false)
const deviceTypeSaving = ref(false)
const deviceTypeFormRef = ref(null)
const deviceTypeCmdError = ref('')

const deviceTypeRules = computed(() => ({
  DeviceType_id: [{ required: true, message: ls.t('devices.typeIdRequired'), trigger: 'blur' }],
  name: [{ required: true, message: ls.t('devices.nameRequired'), trigger: 'blur' }],
}))

const emptyDeviceTypeForm = () => ({
  id: null,
  DeviceType_id: '',
  name: '',
  description: '',
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
    deviceTypeCmdError.value = ls.t('common.jsonError')
    return
  }

  const payload = {
    DeviceType_id: deviceTypeForm.value.DeviceType_id,
    name: deviceTypeForm.value.name,
    description: deviceTypeForm.value.description,
    config_parameters: deviceTypeForm.value.config_parameters,
    commands: commands,
  }

  deviceTypeSaving.value = true
  try {
    if (deviceTypeForm.value.id) {
      await updateDeviceType(deviceTypeForm.value.id, payload)
      ElMessage.success(ls.t('devices.typeUpdated'))
    } else {
      await createDeviceType(payload)
      ElMessage.success(ls.t('devices.typeCreated'))
    }
    deviceTypeDialogVisible.value = false
    fetchDeviceTypeList()
  } catch (err) {
    const detail = err.response?.data
    const msg = typeof detail === 'object' ? Object.values(detail).flat().join('；') : ls.t('common.saveFailed')
    ElMessage.error(msg)
  } finally {
    deviceTypeSaving.value = false
  }
}

async function handleDeleteDeviceType(id) {
  try {
    await deleteDeviceType(id)
    ElMessage.success(ls.t('common.deleteSuccess'))
    fetchDeviceTypeList()
  } catch {
    ElMessage.error(ls.t('devices.deleteTypeFailed'))
  }
}

// ==================== 拖拽排序 ====================
const hasActiveFilter = computed(() =>
  Boolean(filterType.value || filterOnline.value || searchText.value)
)

async function handleReorderEnd(evt) {
  if (evt && evt.oldIndex === evt.newIndex) return
  const order = devices.value.map(d => d.device_id)
  try {
    await reorderDevices(order)
  } catch {
    ElMessage.error(ls.t('devices.reorderFailed') || '排序保存失败')
    fetchDevices()
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
      ls.t('devices.deleteConfirmMsg').replace('{name}', device.name),
      ls.t('common.deleteConfirmTitle'),
      { confirmButtonText: ls.t('common.deleteConfirmOk'), cancelButtonText: ls.t('common.cancel'), type: 'warning' }
    )
  } catch {
    return
  }
  try {
    await deleteDevice(device.device_id)
    ElMessage.success(ls.t('devices.deviceDeleted'))
    fetchDevices()
  } catch {
    ElMessage.error(ls.t('common.deleteFailed'))
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

const addRules = computed(() => ({
  device_id: [{ required: true, message: ls.t('devices.deviceIdRequired'), trigger: 'blur' }],
  name: [{ required: true, message: ls.t('devices.deviceNameRequired'), trigger: 'blur' }],
  device_type: [{ required: true, message: ls.t('devices.deviceTypeRequired'), trigger: 'change' }],
}))

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
    ElMessage.success(ls.t('devices.deviceAdded'))
    addDialogVisible.value = false
    fetchDevices()
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

.drag-ghost {
  opacity: 0.4;
  background: var(--iot-color-fill-light, rgba(0, 0, 0, 0.04));
  border: 2px dashed var(--iot-color-primary, #d97757);
  border-radius: var(--iot-border-radius-md, 8px);
}
</style>
