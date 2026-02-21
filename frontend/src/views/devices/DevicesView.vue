<template>
  <div class="devices-view">
    <div class="iot-page-header">
      <div>
        <h1 class="iot-page-title">设备管理</h1>
        <p class="iot-page-subtitle">查看和控制所有执行器设备</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openAddDialog">添加设备</el-button>
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
      </div>
    </div>

    <!-- 卡片网格 -->
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
        <el-empty :description="loading ? '加载中...' : '暂无设备'" />
      </div>
    </div>

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
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh } from '@element-plus/icons-vue'
import { getDevices, createDevice, deleteDevice, getDeviceTypes } from '@/api/devices'
import DeviceCard from '@/components/devices/DeviceCard.vue'

// ==================== 筛选 ====================
const filterType = ref('')
const filterOnline = ref('')
const searchText = ref('')

// ==================== 数据 ====================
const devices = ref([])
const deviceTypes = ref([])
const loading = ref(false)

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
  try {
    const data = await getDeviceTypes()
    deviceTypes.value = data.results || data
  } catch {
    // 静默
  }
}

// ==================== 跳转详情 ====================
const router = useRouter()

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
