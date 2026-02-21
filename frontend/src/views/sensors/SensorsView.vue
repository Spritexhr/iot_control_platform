<template>
  <div class="sensors-view">
    <div class="iot-page-header">
      <div>
        <h1 class="iot-page-title">传感器管理</h1>
        <p class="iot-page-subtitle">查看和管理所有传感器设备</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openAddDialog">添加传感器</el-button>
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
        <el-empty :description="loading ? '加载中...' : '暂无传感器'" />
      </div>
    </div>

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
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh } from '@element-plus/icons-vue'
import { getSensors, createSensor, deleteSensor, getSensorTypes } from '@/api/sensors'
import SensorCard from '@/components/sensors/SensorCard.vue'

// ==================== 筛选 ====================
const filterType = ref('')
const filterOnline = ref('')
const searchText = ref('')

// ==================== 数据 ====================
const sensors = ref([])
const sensorTypes = ref([])
const loading = ref(false)

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
  try {
    const data = await getSensorTypes()
    sensorTypes.value = data.results || data
  } catch {
    // 静默
  }
}

// ==================== 跳转详情 ====================
const router = useRouter()

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
