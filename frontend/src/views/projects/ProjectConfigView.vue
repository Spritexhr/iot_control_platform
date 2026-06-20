<template>
  <div class="pc">
    <div class="iot-page-header">
      <div>
        <h1 class="iot-page-title">配置：{{ project?.name || '' }}</h1>
        <p class="iot-page-subtitle">代号 {{ project?.code }} · 分区 / 成员 / 视图管理</p>
      </div>
      <el-button :icon="ArrowLeft" @click="$router.push(`/projects/${projectId}`)">返回工作台</el-button>
    </div>

    <el-tabs v-model="tab" class="pc__tabs">
      <!-- ============ 分区 ============ -->
      <el-tab-pane label="分区管理" name="sections">
        <div class="pc__row">
          <el-input v-model="newSectionName" placeholder="新分区名，如 反应工段 / 客厅" style="width: 260px" />
          <el-button type="primary" @click="addSection">新建分区</el-button>
        </div>
        <el-table :data="sections" size="small" border style="margin-top: 12px">
          <el-table-column type="index" label="#" width="50" />
          <el-table-column prop="name" label="分区名" />
          <el-table-column label="操作" width="220">
            <template #default="{ row, $index }">
              <el-button size="small" :disabled="$index === 0" @click="moveSection($index, -1)">上移</el-button>
              <el-button size="small" :disabled="$index === sections.length - 1" @click="moveSection($index, 1)">下移</el-button>
              <el-button size="small" type="danger" plain @click="removeSection(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <p class="pc__hint">删除分区不会删除其下成员，只会把它们移到「未分组」。</p>
      </el-tab-pane>

      <!-- ============ 传感器成员 ============ -->
      <el-tab-pane label="传感器成员" name="sensors">
        <div class="pc__row">
          <el-select v-model="pickSensorIds" multiple filterable placeholder="选择要导入的传感器" style="flex: 1">
            <el-option
              v-for="s in bindableSensors"
              :key="s.id"
              :label="`${s.sensor_id} · ${s.name}`"
              :value="s.id"
            />
          </el-select>
          <el-button type="primary" :disabled="!pickSensorIds.length" @click="importSensors">导入选中</el-button>
        </div>
        <el-table :data="sensorMembers" size="small" border style="margin-top: 12px">
          <el-table-column prop="tag" label="位号" width="120">
            <template #default="{ row }">
              <el-input v-model="row.tag" size="small" @change="patchSensor(row, { tag: row.tag })" />
            </template>
          </el-table-column>
          <el-table-column prop="point_id" label="点位ID" width="160" />
          <el-table-column label="分区" width="150">
            <template #default="{ row }">
              <el-select v-model="row.section" size="small" clearable placeholder="未分组" @change="patchSensor(row, { section: row.section })">
                <el-option v-for="sec in sections" :key="sec.id" :label="sec.name" :value="sec.id" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column prop="unit" label="单位" width="90">
            <template #default="{ row }">
              <el-input v-model="row.unit" size="small" @change="patchSensor(row, { unit: row.unit })" />
            </template>
          </el-table-column>
          <el-table-column label="高/低阈值" width="200">
            <template #default="{ row }">
              <el-input-number v-model="row.hi_threshold" size="small" controls-position="right" :value-on-clear="null" style="width: 92px" @change="patchSensor(row, { hi_threshold: row.hi_threshold })" />
              <el-input-number v-model="row.lo_threshold" size="small" controls-position="right" :value-on-clear="null" style="width: 92px" @change="patchSensor(row, { lo_threshold: row.lo_threshold })" />
            </template>
          </el-table-column>
          <el-table-column label="严重度" width="110">
            <template #default="{ row }">
              <el-select v-model="row.severity" size="small" @change="patchSensor(row, { severity: row.severity })">
                <el-option v-for="lv in SEVERITIES" :key="lv" :label="lv" :value="lv" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="显示" width="70">
            <template #default="{ row }">
              <el-switch v-model="row.is_visible" size="small" @change="patchSensor(row, { is_visible: row.is_visible })" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="80">
            <template #default="{ row }">
              <el-button size="small" type="danger" plain @click="removeSensor(row)">删</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- ============ 设备成员 ============ -->
      <el-tab-pane label="设备成员" name="devices">
        <div class="pc__row">
          <el-select v-model="pickDeviceIds" multiple filterable placeholder="选择要导入的设备" style="flex: 1">
            <el-option
              v-for="d in bindableDevices"
              :key="d.id"
              :label="`${d.device_id} · ${d.name}`"
              :value="d.id"
            />
          </el-select>
          <el-button type="primary" :disabled="!pickDeviceIds.length" @click="importDevices">导入选中</el-button>
        </div>
        <el-table :data="deviceMembers" size="small" border style="margin-top: 12px">
          <el-table-column prop="tag" label="位号" width="140">
            <template #default="{ row }">
              <el-input v-model="row.tag" size="small" @change="patchDevice(row, { tag: row.tag })" />
            </template>
          </el-table-column>
          <el-table-column prop="device_id" label="设备ID" width="160" />
          <el-table-column label="分区" width="180">
            <template #default="{ row }">
              <el-select v-model="row.section" size="small" clearable placeholder="未分组" @change="patchDevice(row, { section: row.section })">
                <el-option v-for="sec in sections" :key="sec.id" :label="sec.name" :value="sec.id" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="显示" width="80">
            <template #default="{ row }">
              <el-switch v-model="row.is_visible" size="small" @change="patchDevice(row, { is_visible: row.is_visible })" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="80">
            <template #default="{ row }">
              <el-button size="small" type="danger" plain @click="removeDevice(row)">删</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- ============ 视图 ============ -->
      <el-tab-pane label="视图管理" name="views">
        <div class="pc__row">
          <el-input v-model="newView.name" placeholder="视图名" style="width: 200px" />
          <el-select v-model="newView.view_type" style="width: 160px">
            <el-option label="卡片大屏" value="card" />
            <el-option label="流程图（阶段2）" value="diagram" />
            <el-option label="时序趋势（阶段3）" value="timeseries" />
          </el-select>
          <el-checkbox v-model="newView.is_default">设为默认</el-checkbox>
          <el-button type="primary" @click="addView">新建视图</el-button>
        </div>
        <el-table :data="views" size="small" border style="margin-top: 12px">
          <el-table-column prop="name" label="视图名" />
          <el-table-column prop="view_type" label="类型" width="140">
            <template #default="{ row }">{{ VIEW_TYPE_LABELS[row.view_type] || row.view_type }}</template>
          </el-table-column>
          <el-table-column label="默认" width="90">
            <template #default="{ row }">
              <el-switch v-model="row.is_default" size="small" @change="patchView(row, { is_default: row.is_default })" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="80">
            <template #default="{ row }">
              <el-button size="small" type="danger" plain @click="removeView(row)">删</el-button>
            </template>
          </el-table-column>
        </el-table>
        <p class="pc__hint">未建任何视图时，工作台默认显示一个「卡片大屏」。</p>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'

import {
  getProject,
  listProjectBindableSources,
  listSections, createSection, deleteSection, reorderSections,
  listSensorMembers, createSensorMembers, updateSensorMember, deleteSensorMember,
  listDeviceMembers, createDeviceMembers, updateDeviceMember, deleteDeviceMember,
  listViews, createView, updateView, deleteView,
} from '@/api/projects'

const route = useRoute()
const projectId = Number(route.params.id)

const SEVERITIES = ['low', 'mid', 'high', 'critical']
const VIEW_TYPE_LABELS = { card: '卡片大屏', diagram: '流程图', timeseries: '时序趋势' }

const tab = ref('sections')
const project = ref(null)
const sections = ref([])
const sensorMembers = ref([])
const deviceMembers = ref([])
const views = ref([])
const bindableSensors = ref([])
const bindableDevices = ref([])

const newSectionName = ref('')
const pickSensorIds = ref([])
const pickDeviceIds = ref([])
const newView = ref({ name: '', view_type: 'card', is_default: false })

function unwrap(data) {
  return data?.results || data || []
}

async function loadMembers() {
  sensorMembers.value = unwrap(await listSensorMembers(projectId))
  deviceMembers.value = unwrap(await listDeviceMembers(projectId))
}
async function loadBindable() {
  const data = await listProjectBindableSources(projectId)
  bindableSensors.value = data.sensors || []
  bindableDevices.value = data.devices || []
}
async function loadSections() {
  sections.value = unwrap(await listSections(projectId))
}
async function loadViews() {
  views.value = unwrap(await listViews(projectId))
}

async function init() {
  try {
    project.value = await getProject(projectId)
    await Promise.all([loadSections(), loadMembers(), loadViews(), loadBindable()])
  } catch (e) {
    console.error('[project-config] 加载失败', e)
  }
}
init()

// ---------- 分区 ----------
async function addSection() {
  if (!newSectionName.value.trim()) return
  await createSection({ project: projectId, name: newSectionName.value.trim(), sort_order: sections.value.length })
  newSectionName.value = ''
  await loadSections()
}
async function moveSection(index, dir) {
  const arr = [...sections.value]
  const j = index + dir
  if (j < 0 || j >= arr.length) return
  ;[arr[index], arr[j]] = [arr[j], arr[index]]
  sections.value = arr
  await reorderSections(arr.map((s) => s.id))
}
async function removeSection(row) {
  try {
    await ElMessageBox.confirm(`删除分区「${row.name}」？其成员将移到未分组。`, '提示', { type: 'warning' })
  } catch { return }
  await deleteSection(row.id)
  await Promise.all([loadSections(), loadMembers()])
}

// ---------- 传感器成员 ----------
async function importSensors() {
  await createSensorMembers(projectId, pickSensorIds.value)
  pickSensorIds.value = []
  ElMessage.success('已导入')
  await Promise.all([loadMembers(), loadBindable()])
}
async function patchSensor(row, patch) {
  try { await updateSensorMember(row.id, patch) } catch { ElMessage.error('保存失败') }
}
async function removeSensor(row) {
  await deleteSensorMember(row.id)
  await Promise.all([loadMembers(), loadBindable()])
}

// ---------- 设备成员 ----------
async function importDevices() {
  await createDeviceMembers(projectId, pickDeviceIds.value)
  pickDeviceIds.value = []
  ElMessage.success('已导入')
  await Promise.all([loadMembers(), loadBindable()])
}
async function patchDevice(row, patch) {
  try { await updateDeviceMember(row.id, patch) } catch { ElMessage.error('保存失败') }
}
async function removeDevice(row) {
  await deleteDeviceMember(row.id)
  await Promise.all([loadMembers(), loadBindable()])
}

// ---------- 视图 ----------
async function addView() {
  if (!newView.value.name.trim()) { ElMessage.warning('请填写视图名'); return }
  await createView({ project: projectId, ...newView.value, sort_order: views.value.length })
  newView.value = { name: '', view_type: 'card', is_default: false }
  await loadViews()
}
async function patchView(row, patch) {
  try { await updateView(row.id, patch) } catch { ElMessage.error('保存失败') }
}
async function removeView(row) {
  await deleteView(row.id)
  await loadViews()
}
</script>

<style scoped lang="scss">
.pc {
  padding: 0;
}

.pc__row {
  display: flex;
  align-items: center;
  gap: var(--iot-spacing-sm);
  flex-wrap: wrap;
}

.pc__hint {
  margin-top: var(--iot-spacing-sm);
  font-size: var(--iot-font-size-xs);
  color: var(--iot-text-secondary);
}
</style>
