<template>
  <div class="pc">
    <div class="iot-page-header">
      <div>
        <h1 class="iot-page-title">项目配置：{{ project?.name || '' }}</h1>
        <p class="iot-page-subtitle">唯一代号 {{ project?.code }} · 房间(分区)隔离：每个房间各自管理传感器 / 设备 / 视图</p>
      </div>
      <el-button :icon="ArrowLeft" class="pc__back-btn" @click="$router.push(`/projects/${projectId}`)">返回工作台</el-button>
    </div>

    <div class="pc-body">
      <!-- ============ 左：房间列表 ============ -->
      <aside class="pc-rooms">
        <div class="pc-rooms__head">
          <span class="pc-rooms__title"><el-icon><House /></el-icon> 房间（分区）</span>
        </div>
        <div class="pc-rooms__add">
          <el-input v-model="newSectionName" placeholder="新房间名" size="small" @keyup.enter="addSection" />
          <el-button type="primary" size="small" :icon="Plus" @click="addSection" />
        </div>
        <ul v-if="sections.length" class="pc-rooms__list">
          <li
            v-for="(sec, idx) in sections"
            :key="sec.id"
            class="pc-room"
            :class="{ 'is-active': sec.id === activeSectionId }"
            @click="activeSectionId = sec.id"
          >
            <div class="pc-room__main">
              <span class="pc-room__name">{{ sec.name }}</span>
              <span class="pc-room__stat">{{ roomStat(sec.id) }}</span>
            </div>
            <el-dropdown trigger="click" @command="(c) => onRoomCommand(c, sec, idx)">
              <el-icon class="pc-room__more" @click.stop><MoreFilled /></el-icon>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="rename" :icon="EditPen">重命名</el-dropdown-item>
                  <el-dropdown-item command="up" :icon="Top" :disabled="idx === 0">上移</el-dropdown-item>
                  <el-dropdown-item command="down" :icon="Bottom" :disabled="idx === sections.length - 1">下移</el-dropdown-item>
                  <el-dropdown-item command="delete" :icon="Delete" divided style="color: var(--iot-color-danger)">删除房间</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </li>
        </ul>
        <el-empty v-else :image-size="60" description="先新建一个房间" />
      </aside>

      <!-- ============ 右：房间详情 ============ -->
      <section v-if="activeSection" class="pc-detail">
        <el-tabs v-model="tab" class="pc__tabs segmented-tabs">
          <!-- ===== 传感器 ===== -->
          <el-tab-pane name="sensors">
            <template #label>
              <span class="tab-label-custom"><el-icon><Cpu /></el-icon><span>传感器</span></span>
            </template>
            <div class="pc-panel">
              <div class="pc__row">
                <span class="pc__row-title">加入「{{ activeSection.name }}」：</span>
                <el-select v-model="pickSensorIds" multiple filterable placeholder="选择要导入到本房间的传感器" style="flex: 1; max-width: 450px;">
                  <el-option v-for="s in bindableSensors" :key="s.id" :label="`${s.sensor_id} · ${s.name}`" :value="s.id" />
                </el-select>
                <el-button type="primary" :disabled="!pickSensorIds.length" @click="importSensors">导入选中</el-button>
              </div>
              <el-table :data="sectionSensors" size="default" border style="margin-top: 12px">
                <el-table-column prop="tag" label="位号 (Tag)" width="150">
                  <template #default="{ row }">
                    <el-input v-model="row.tag" size="small" @change="patchSensor(row, { tag: row.tag })" />
                  </template>
                </el-table-column>
                <el-table-column prop="point_id" label="点位ID" width="160" />
                <el-table-column label="所属房间" width="160">
                  <template #default="{ row }">
                    <el-select v-model="row.section" size="small" @change="moveSensor(row)">
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
                <template #empty>本房间暂无传感器，从上方导入。</template>
              </el-table>
            </div>
          </el-tab-pane>

          <!-- ===== 设备 ===== -->
          <el-tab-pane name="devices">
            <template #label>
              <span class="tab-label-custom"><el-icon><Connection /></el-icon><span>设备</span></span>
            </template>
            <div class="pc-panel">
              <div class="pc__row">
                <span class="pc__row-title">加入「{{ activeSection.name }}」：</span>
                <el-select v-model="pickDeviceIds" multiple filterable placeholder="选择要导入到本房间的设备" style="flex: 1; max-width: 450px;">
                  <el-option v-for="d in bindableDevices" :key="d.id" :label="`${d.device_id} · ${d.name}`" :value="d.id" />
                </el-select>
                <el-button type="primary" :disabled="!pickDeviceIds.length" @click="importDevices">导入选中</el-button>
              </div>
              <el-table :data="sectionDevices" size="default" border style="margin-top: 12px">
                <el-table-column prop="tag" label="位号 (Tag)" width="180">
                  <template #default="{ row }">
                    <el-input v-model="row.tag" size="small" @change="patchDevice(row, { tag: row.tag })" />
                  </template>
                </el-table-column>
                <el-table-column prop="device_id" label="设备ID" width="220" />
                <el-table-column label="所属房间" width="220">
                  <template #default="{ row }">
                    <el-select v-model="row.section" size="small" @change="moveDevice(row)">
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
                <template #empty>本房间暂无设备，从上方导入。</template>
              </el-table>
            </div>
          </el-tab-pane>

          <!-- ===== 视图 ===== -->
          <el-tab-pane name="views">
            <template #label>
              <span class="tab-label-custom"><el-icon><Monitor /></el-icon><span>视图</span></span>
            </template>
            <div class="pc-panel">
              <div class="pc__row">
                <span class="pc__row-title">新建视图（属于「{{ activeSection.name }}」）：</span>
                <el-input v-model="newView.name" placeholder="如 一期总览" style="width: 200px" />
                <el-select v-model="newView.view_type" style="width: 160px">
                  <el-option label="卡片大屏" value="card" />
                  <el-option label="工艺流程图" value="diagram" />
                  <el-option label="时序趋势图" value="timeseries" />
                  <el-option label="自动化控制" value="control" />
                </el-select>
                <el-checkbox v-model="newView.is_default">设为默认视图</el-checkbox>
                <el-button type="primary" @click="addView">创建视图</el-button>
              </div>
              <el-table :data="sectionViews" size="default" border style="margin-top: 12px">
                <el-table-column prop="name" label="视图名称">
                  <template #default="{ row }">
                    <el-input v-model="row.name" size="small" @change="patchView(row, { name: row.name })" />
                  </template>
                </el-table-column>
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
                <template #empty>本房间暂无视图，工作台会自动渲染一个卡片大屏展示本房间点位。</template>
              </el-table>
              <p class="pc__hint">提示：视图只能展示本房间的传感器 / 设备；默认视图为进入房间时首先显示的视图。</p>
            </div>
          </el-tab-pane>
        </el-tabs>
      </section>

      <section v-else class="pc-detail pc-detail--empty">
        <el-empty description="请选择左侧房间，或在上方新建一个房间" />
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft, Cpu, Connection, Monitor,
  House, Plus, MoreFilled, EditPen, Top, Bottom, Delete,
} from '@element-plus/icons-vue'

import {
  getProject,
  listProjectBindableSources,
  listSections, createSection, updateSection, deleteSection, reorderSections,
  listSensorMembers, createSensorMembers, updateSensorMember, deleteSensorMember,
  listDeviceMembers, createDeviceMembers, updateDeviceMember, deleteDeviceMember,
  listViews, createView, updateView, deleteView,
} from '@/api/projects'

const route = useRoute()
const projectId = Number(route.params.id)

const SEVERITIES = ['low', 'mid', 'high', 'critical']
const SEVERITY_LABELS = { low: '低严重度', mid: '中严重度', high: '高严重度', critical: '紧急严重度' }
function severityLabel(lv) { return SEVERITY_LABELS[lv] || lv }

const VIEW_TYPE_LABELS = { card: '卡片大屏', diagram: '流程图', timeseries: '时序趋势', control: '自动化控制' }

const tab = ref('sensors')
const project = ref(null)
const sections = ref([])
const activeSectionId = ref(null)
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

// ---------- 当前房间派生数据 ----------
const activeSection = computed(() => sections.value.find((s) => s.id === activeSectionId.value) || null)
const sectionSensors = computed(() => sensorMembers.value.filter((m) => m.section === activeSectionId.value))
const sectionDevices = computed(() => deviceMembers.value.filter((m) => m.section === activeSectionId.value))
const sectionViews = computed(() => views.value.filter((v) => v.section === activeSectionId.value))

function roomStat(secId) {
  const sCount = sensorMembers.value.filter((m) => m.section === secId).length
  const dCount = deviceMembers.value.filter((m) => m.section === secId).length
  return `${sCount} 传感 · ${dCount} 设备`
}

// ---------- 加载 ----------
async function loadSections() {
  sections.value = unwrap(await listSections(projectId))
  if (!sections.value.some((s) => s.id === activeSectionId.value)) {
    activeSectionId.value = sections.value[0]?.id ?? null
  }
}
async function loadMembers() {
  sensorMembers.value = unwrap(await listSensorMembers(projectId))
  deviceMembers.value = unwrap(await listDeviceMembers(projectId))
}
async function loadViews() {
  views.value = unwrap(await listViews(projectId))
}
async function loadBindable() {
  if (!activeSectionId.value) {
    bindableSensors.value = []
    bindableDevices.value = []
    return
  }
  const data = await listProjectBindableSources(projectId, activeSectionId.value)
  bindableSensors.value = data.sensors || []
  bindableDevices.value = data.devices || []
}

async function init() {
  try {
    project.value = await getProject(projectId)
    await Promise.all([loadSections(), loadMembers(), loadViews()])
    await loadBindable()
  } catch (e) {
    console.error('[project-config] 加载失败', e)
  }
}
init()

// 切换房间时重置选择并刷新该房间的可导入清单
watch(activeSectionId, () => {
  pickSensorIds.value = []
  pickDeviceIds.value = []
  loadBindable()
})

// ---------- 房间（分区）管理 ----------
async function addSection() {
  const name = newSectionName.value.trim()
  if (!name) return
  try {
    const created = await createSection({ project: projectId, name, sort_order: sections.value.length })
    newSectionName.value = ''
    await loadSections()
    if (created?.id) activeSectionId.value = created.id
  } catch (e) {
    ElMessage.error('新建房间失败')
  }
}

function onRoomCommand(cmd, sec, idx) {
  if (cmd === 'rename') renameSection(sec)
  else if (cmd === 'up') moveSection(idx, -1)
  else if (cmd === 'down') moveSection(idx, 1)
  else if (cmd === 'delete') removeSection(sec)
}

async function renameSection(sec) {
  let value
  try {
    ({ value } = await ElMessageBox.prompt('请输入新的房间名', '重命名房间', {
      inputValue: sec.name,
      inputValidator: (v) => (v && v.trim() ? true : '名称不能为空'),
    }))
  } catch { return }
  try {
    await updateSection(sec.id, { name: value.trim() })
    await loadSections()
  } catch (e) {
    ElMessage.error('重命名失败')
  }
}

async function moveSection(index, dir) {
  const arr = [...sections.value]
  const j = index + dir
  if (j < 0 || j >= arr.length) return
  ;[arr[index], arr[j]] = [arr[j], arr[index]]
  sections.value = arr
  await reorderSections(arr.map((s) => s.id))
}

async function removeSection(sec) {
  try {
    await ElMessageBox.confirm(
      `删除房间「${sec.name}」？将一并删除该房间下的传感器 / 设备成员与视图（不影响主模型传感器 / 设备）。`,
      '删除房间', { type: 'warning' },
    )
  } catch { return }
  try {
    await deleteSection(sec.id)
    if (activeSectionId.value === sec.id) activeSectionId.value = null
    await Promise.all([loadSections(), loadMembers(), loadViews()])
    await loadBindable()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

// ---------- 传感器成员 ----------
async function importSensors() {
  try {
    await createSensorMembers(projectId, pickSensorIds.value, activeSectionId.value)
    pickSensorIds.value = []
    ElMessage.success('已导入')
    await Promise.all([loadMembers(), loadBindable()])
  } catch (e) {
    ElMessage.error('导入失败')
  }
}
async function patchSensor(row, patch) {
  try { await updateSensorMember(row.id, patch) } catch { ElMessage.error('保存失败') }
}
async function moveSensor(row) {
  try {
    await updateSensorMember(row.id, { section: row.section })
    await Promise.all([loadMembers(), loadBindable()])
  } catch (e) {
    ElMessage.error('移动失败：该房间可能已存在同一传感器点位')
    await loadMembers()
  }
}
async function removeSensor(row) {
  try {
    await deleteSensorMember(row.id)
    await Promise.all([loadMembers(), loadBindable()])
  } catch (error) {
    await showMemberDeleteError(error, '传感器')
  }
}

// ---------- 设备成员 ----------
async function importDevices() {
  try {
    await createDeviceMembers(projectId, pickDeviceIds.value, activeSectionId.value)
    pickDeviceIds.value = []
    ElMessage.success('已导入')
    await Promise.all([loadMembers(), loadBindable()])
  } catch (e) {
    ElMessage.error('导入失败')
  }
}
async function patchDevice(row, patch) {
  try { await updateDeviceMember(row.id, patch) } catch { ElMessage.error('保存失败') }
}
async function moveDevice(row) {
  try {
    await updateDeviceMember(row.id, { section: row.section })
    await Promise.all([loadMembers(), loadBindable()])
  } catch (e) {
    ElMessage.error('移动失败：该房间可能已存在同一设备')
    await loadMembers()
  }
}
async function removeDevice(row) {
  try {
    await deleteDeviceMember(row.id)
    await Promise.all([loadMembers(), loadBindable()])
  } catch (error) {
    await showMemberDeleteError(error, '设备')
  }
}

async function showMemberDeleteError(error, resourceLabel) {
  const data = error.response?.data
  if (error.response?.status === 409) {
    const schemes = Array.isArray(data?.blockers) ? data.blockers : []
    const names = schemes.map((item) => {
      const state = item.is_enabled ? '运行中' : '已停用'
      return `「${item.name}」（${state}）`
    }).join('、')
    const message = names ? `${data.detail}\n占用方案：${names}` : data.detail
    await ElMessageBox.alert(message, `无法移除${resourceLabel}`, {
      type: 'warning',
      confirmButtonText: '知道了',
    })
    return
  }
  ElMessage.error(error.response?.data?.detail || `${resourceLabel}移除失败`)
}

// ---------- 视图 ----------
async function addView() {
  if (!newView.value.name.trim()) { ElMessage.warning('请填写视图名'); return }
  try {
    await createView({
      project: projectId,
      section: activeSectionId.value,
      ...newView.value,
      sort_order: sectionViews.value.length,
    })
    newView.value = { name: '', view_type: 'card', is_default: false }
    await loadViews()
  } catch (e) {
    ElMessage.error('创建视图失败')
  }
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

/* 主从两栏布局 */
.pc-body {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: var(--iot-spacing-lg);
  align-items: start;
}

/* 左：房间列表 */
.pc-rooms {
  background: var(--iot-bg-card);
  border: 1px solid var(--iot-border-color-light);
  border-radius: var(--iot-radius-lg);
  box-shadow: var(--iot-shadow-sm);
  padding: var(--iot-spacing-md);
  position: sticky;
  top: var(--iot-spacing-md);
}

.pc-rooms__head {
  margin-bottom: var(--iot-spacing-sm);
}

.pc-rooms__title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--iot-font-size-sm);
  font-weight: 600;
  color: var(--iot-text-primary);
}

.pc-rooms__add {
  display: flex;
  gap: 6px;
  margin-bottom: var(--iot-spacing-sm);
}

.pc-rooms__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.pc-room {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 10px;
  border-radius: var(--iot-radius-base);
  cursor: pointer;
  border: 1px solid transparent;
  transition: all var(--iot-transition-fast);

  &:hover {
    background: var(--iot-border-color-lighter);
  }

  &.is-active {
    background: var(--iot-color-primary-bg);
    border-color: var(--iot-color-primary-light);
  }

  &__main {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }

  &__name {
    font-size: var(--iot-font-size-sm);
    font-weight: 600;
    color: var(--iot-text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  &__stat {
    font-size: 11px;
    color: var(--iot-text-secondary);
  }

  &__more {
    color: var(--iot-text-secondary);
    flex-shrink: 0;

    &:hover {
      color: var(--iot-text-primary);
    }
  }
}

/* 右：详情 */
.pc-detail {
  min-width: 0;
}

.pc-detail--empty {
  background: var(--iot-bg-card);
  border: 1px dashed var(--iot-border-color);
  border-radius: var(--iot-radius-lg);
  padding: 60px 0;
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

@media screen and (max-width: 900px) {
  .pc-body {
    grid-template-columns: 1fr;
  }
  .pc-rooms {
    position: static;
  }
}
</style>
