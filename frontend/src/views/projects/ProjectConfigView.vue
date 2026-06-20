<template>
  <div class="pc">
    <div class="iot-page-header">
      <div>
        <h1 class="iot-page-title">项目配置：{{ project?.name || '' }}</h1>
        <p class="iot-page-subtitle">唯一代号 {{ project?.code }} · 统一配置分区、数据源及视图</p>
      </div>
      <el-button :icon="ArrowLeft" class="pc__back-btn" @click="$router.push(`/projects/${projectId}`)">返回工作台</el-button>
    </div>

    <el-tabs v-model="tab" class="pc__tabs segmented-tabs">
      <!-- ============ 分区 ============ -->
      <el-tab-pane name="sections">
        <template #label>
          <span class="tab-label-custom">
            <el-icon><Folder /></el-icon>
            <span>分区管理</span>
          </span>
        </template>
        <div class="pc-panel">
          <div class="pc__row">
            <span class="pc__row-title">新建分区：</span>
            <el-input v-model="newSectionName" placeholder="如 反应工段 / 客厅" style="width: 260px" />
            <el-button type="primary" @click="addSection">新建分区</el-button>
          </div>
          <el-table :data="sections" size="default" border style="margin-top: 12px">
            <el-table-column type="index" label="#" width="60" align="center" />
            <el-table-column prop="name" label="分区名" />
            <el-table-column label="操作" width="220" align="center">
              <template #default="{ row, $index }">
                <el-button size="small" :disabled="$index === 0" @click="moveSection($index, -1)">上移</el-button>
                <el-button size="small" :disabled="$index === sections.length - 1" @click="moveSection($index, 1)">下移</el-button>
                <el-button size="small" type="danger" plain @click="removeSection(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <p class="pc__hint">提示：删除分区不会删除其下挂载的成员，它们会被自动归置到「未分组」中。</p>
        </div>
      </el-tab-pane>

      <!-- ============ 传感器成员 ============ -->
      <el-tab-pane name="sensors">
        <template #label>
          <span class="tab-label-custom">
            <el-icon><Cpu /></el-icon>
            <span>传感器成员</span>
          </span>
        </template>
        <div class="pc-panel">
          <div class="pc__row">
            <span class="pc__row-title">绑定数据源：</span>
            <el-select v-model="pickSensorIds" multiple filterable placeholder="选择要导入的传感器" style="flex: 1; max-width: 450px;">
              <el-option
                v-for="s in bindableSensors"
                :key="s.id"
                :label="`${s.sensor_id} · ${s.name}`"
                :value="s.id"
              />
            </el-select>
            <el-button type="primary" :disabled="!pickSensorIds.length" @click="importSensors">导入选中</el-button>
          </div>
          <el-table :data="sensorMembers" size="default" border style="margin-top: 12px">
            <el-table-column prop="tag" label="位号 (Tag)" width="150">
              <template #default="{ row }">
                <el-input v-model="row.tag" size="small" @change="patchSensor(row, { tag: row.tag })" />
              </template>
            </el-table-column>
            <el-table-column prop="point_id" label="点位ID" width="160" />
            <el-table-column label="所属分区" width="160">
              <template #default="{ row }">
                <el-select v-model="row.section" size="small" clearable placeholder="未分组" @change="patchSensor(row, { section: row.section })">
                  <el-option v-for="sec in sections" :key="sec.id" :label="sec.name" :value="sec.id" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column prop="unit" label="单位" width="100">
              <template #default="{ row }">
                <el-input v-model="row.unit" size="small" @change="patchSensor(row, { unit: row.unit })" />
              </template>
            </el-table-column>
            <el-table-column label="超限阈值 (低 / 高)" width="230" align="center">
              <template #default="{ row }">
                <div class="threshold-inputs">
                  <el-input-number v-model="row.lo_threshold" size="small" controls-position="right" :value-on-clear="null" style="width: 90px" placeholder="低" @change="patchSensor(row, { lo_threshold: row.lo_threshold })" />
                  <span class="threshold-sep">/</span>
                  <el-input-number v-model="row.hi_threshold" size="small" controls-position="right" :value-on-clear="null" style="width: 90px" placeholder="高" @change="patchSensor(row, { hi_threshold: row.hi_threshold })" />
                </div>
              </template>
            </el-table-column>
            <el-table-column label="严重度" width="150" align="center">
              <template #default="{ row }">
                <el-select v-model="row.severity" size="small" :class="'severity-select--' + row.severity" @change="patchSensor(row, { severity: row.severity })">
                  <el-option v-for="lv in SEVERITIES" :key="lv" :label="severityLabel(lv)" :value="lv">
                    <span class="severity-badge-option" :class="'severity-badge--' + lv">{{ severityLabel(lv) }}</span>
                  </el-option>
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="显示" width="80" align="center">
              <template #default="{ row }">
                <el-switch v-model="row.is_visible" size="small" @change="patchSensor(row, { is_visible: row.is_visible })" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80" align="center">
              <template #default="{ row }">
                <el-button size="small" type="danger" plain @click="removeSensor(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <!-- ============ 设备成员 ============ -->
      <el-tab-pane name="devices">
        <template #label>
          <span class="tab-label-custom">
            <el-icon><Connection /></el-icon>
            <span>设备成员</span>
          </span>
        </template>
        <div class="pc-panel">
          <div class="pc__row">
            <span class="pc__row-title">绑定设备源：</span>
            <el-select v-model="pickDeviceIds" multiple filterable placeholder="选择要导入的设备" style="flex: 1; max-width: 450px;">
              <el-option
                v-for="d in bindableDevices"
                :key="d.id"
                :label="`${d.device_id} · ${d.name}`"
                :value="d.id"
              />
            </el-select>
            <el-button type="primary" :disabled="!pickDeviceIds.length" @click="importDevices">导入选中</el-button>
          </div>
          <el-table :data="deviceMembers" size="default" border style="margin-top: 12px">
            <el-table-column prop="tag" label="位号 (Tag)" width="180">
              <template #default="{ row }">
                <el-input v-model="row.tag" size="small" @change="patchDevice(row, { tag: row.tag })" />
              </template>
            </el-table-column>
            <el-table-column prop="device_id" label="设备ID" width="220" />
            <el-table-column label="所属分区" width="220">
              <template #default="{ row }">
                <el-select v-model="row.section" size="small" clearable placeholder="未分组" @change="patchDevice(row, { section: row.section })">
                  <el-option v-for="sec in sections" :key="sec.id" :label="sec.name" :value="sec.id" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="工作台显示" width="120" align="center">
              <template #default="{ row }">
                <el-switch v-model="row.is_visible" size="small" @change="patchDevice(row, { is_visible: row.is_visible })" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" align="center">
              <template #default="{ row }">
                <el-button size="small" type="danger" plain @click="removeDevice(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <!-- ============ 视图 ============ -->
      <el-tab-pane name="views">
        <template #label>
          <span class="tab-label-custom">
            <el-icon><Monitor /></el-icon>
            <span>视图管理</span>
          </span>
        </template>
        <div class="pc-panel">
          <div class="pc__row">
            <span class="pc__row-title">新建视图：</span>
            <el-input v-model="newView.name" placeholder="如 一期总览" style="width: 200px" />
            <el-select v-model="newView.view_type" style="width: 160px">
              <el-option label="卡片大屏" value="card" />
              <el-option label="工艺流程图" value="diagram" />
              <el-option label="时序趋势图" value="timeseries" />
            </el-select>
            <el-checkbox v-model="newView.is_default">设为默认视图</el-checkbox>
            <el-button type="primary" @click="addView">创建视图</el-button>
          </div>
          <el-table :data="views" size="default" border style="margin-top: 12px">
            <el-table-column prop="name" label="视图名称" />
            <el-table-column prop="view_type" label="视图类型" width="180" align="center">
              <template #default="{ row }">
                <el-tag size="small" effect="plain">{{ VIEW_TYPE_LABELS[row.view_type] || row.view_type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="设为默认" width="120" align="center">
              <template #default="{ row }">
                <el-switch v-model="row.is_default" size="small" @change="patchView(row, { is_default: row.is_default })" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120" align="center">
              <template #default="{ row }">
                <el-button size="small" type="danger" plain @click="removeView(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <p class="pc__hint">提示：当未创建任何视图时，工作台会自动加载一个基础的「卡片大屏」展示点位。</p>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  ArrowLeft,
  Folder,
  Cpu,
  Connection,
  Monitor
} from '@element-plus/icons-vue'

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
const SEVERITY_LABELS = { low: '低严重度', mid: '中严重度', high: '高严重度', critical: '紧急严重度' }
function severityLabel(lv) { return SEVERITY_LABELS[lv] || lv }

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
  animation: iot-fade-in 0.4s ease forwards;
}

.pc__back-btn {
  border-radius: var(--iot-radius-base);
  border-color: var(--iot-border-color);
  color: var(--iot-text-secondary);

  &:hover {
    color: var(--iot-text-primary);
    background: var(--iot-border-color-lighter);
  }
}

.pc-panel {
  background: var(--iot-bg-card);
  border: 1px solid var(--iot-border-color-light);
  border-radius: var(--iot-radius-lg);
  padding: var(--iot-spacing-lg);
  box-shadow: var(--iot-shadow-sm);
  margin-top: -1px;
}

.pc__row {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--iot-border-color-lighter);
  padding: 12px var(--iot-spacing-md);
  border-radius: var(--iot-radius-base);
  margin-bottom: var(--iot-spacing-md);
  border: 1px solid var(--iot-border-color-light);
  flex-wrap: wrap;

  &-title {
    font-size: var(--iot-font-size-sm);
    font-weight: 600;
    color: var(--iot-text-regular);
  }
}

.pc__hint {
  margin-top: var(--iot-spacing-md);
  font-size: var(--iot-font-size-xs);
  color: var(--iot-text-secondary);
  background: var(--iot-color-primary-bg);
  padding: 8px 12px;
  border-radius: var(--iot-radius-sm);
  display: inline-block;
}

/* 阈值输入组 */
.threshold-inputs {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;

  .threshold-sep {
    color: var(--iot-text-placeholder);
    font-weight: bold;
  }
}

/* 分段式 Tab 样式 */
.segmented-tabs {
  :deep(.el-tabs__header) {
    background: var(--iot-border-color-lighter);
    padding: 4px;
    border-radius: var(--iot-radius-lg) var(--iot-radius-lg) 0 0;
    display: inline-flex;
    margin-bottom: 0;
    border: 1px solid var(--iot-border-color-light);
    border-bottom: none;
  }

  :deep(.el-tabs__nav-wrap) {
    &::after {
      display: none !important;
    }
  }

  :deep(.el-tabs__active-bar) {
    display: none !important;
  }

  :deep(.el-tabs__nav) {
    gap: 4px;
  }

  :deep(.el-tabs__item) {
    height: 36px;
    line-height: 36px;
    padding: 0 20px !important;
    border-radius: var(--iot-radius-base) var(--iot-radius-base) 0 0;
    color: var(--iot-text-secondary) !important;
    font-weight: 500;
    transition: all var(--iot-transition-fast);
    font-size: var(--iot-font-size-sm);

    &:hover {
      color: var(--iot-text-primary) !important;
    }

    &.is-active {
      color: var(--iot-text-primary) !important;
      background: var(--iot-bg-card);
      border-left: 1px solid var(--iot-border-color-light);
      border-right: 1px solid var(--iot-border-color-light);
      border-top: 1px solid var(--iot-border-color-light);
      margin-bottom: -1px;
      position: relative;
      z-index: 2;
    }
  }
}

.tab-label-custom {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* 严重度下拉样式 */
.severity-badge-option {
  display: inline-block;
  padding: 1px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  line-height: 1.6;
}

.severity-badge--low { background: rgba(139, 123, 107, 0.1); color: var(--iot-text-secondary); }
.severity-badge--mid { background: var(--iot-color-success-bg); color: var(--iot-color-success); }
.severity-badge--high { background: var(--iot-color-warning-bg); color: var(--iot-color-warning); }
.severity-badge--critical { background: var(--iot-color-danger-bg); color: var(--iot-color-danger); }

/* select 容器根据严重度设置不同文字色 */
:deep(.severity-select--low .el-input__inner) { color: var(--iot-text-secondary); font-weight: 600; }
:deep(.severity-select--mid .el-input__inner) { color: var(--iot-color-success); font-weight: 600; }
:deep(.severity-select--high .el-input__inner) { color: var(--iot-color-warning); font-weight: 600; }
:deep(.severity-select--critical .el-input__inner) { color: var(--iot-color-danger); font-weight: 600; }
</style>

