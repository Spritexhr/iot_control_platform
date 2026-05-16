<template>
  <div class="eb-config">
    <header class="eb-config__header">
      <div>
        <h1>EB 大屏 · 配置面板</h1>
        <p class="eb-config__sub">从主模型导入传感器/设备到大屏，编辑显示参数</p>
      </div>
      <div class="eb-config__actions">
        <el-button @click="$router.push('/plugins/eb_plant')">返回大屏</el-button>
        <el-button type="primary" @click="reload">刷新</el-button>
      </div>
    </header>

    <el-tabs v-model="activeTab" class="eb-config__tabs">
      <!-- ============ 传感器绑定 ============ -->
      <el-tab-pane label="传感器" name="sensors">
        <div class="eb-config__panel">
          <section class="eb-config__col">
            <div class="eb-config__col-head">
              <h3>主模型可选传感器</h3>
              <el-button
                size="small"
                type="primary"
                :disabled="selectedSensorIds.length === 0"
                @click="onImportSensors"
              >
                导入选中 ({{ selectedSensorIds.length }})
              </el-button>
            </div>
            <p class="eb-config__hint">
              多字段传感器（如温压一体）可导入后在右侧表格"添加字段"为每个 data_key 各创建一行。
            </p>
            <el-table
              :data="availableSensors"
              size="small"
              max-height="500"
              @selection-change="(rows) => (selectedSensorIds = rows.map((r) => r.id))"
            >
              <el-table-column type="selection" width="40" :selectable="canSelectSensor" />
              <el-table-column prop="sensor_id" label="ID" min-width="140" />
              <el-table-column prop="name" label="名称" min-width="180" show-overflow-tooltip />
              <el-table-column prop="sensor_type" label="类型" min-width="140" />
              <el-table-column label="字段" min-width="180">
                <template #default="{ row }">
                  <el-tag
                    v-for="f in row.data_fields"
                    :key="f"
                    size="small"
                    class="eb-config__tag"
                    :type="(row.bound_data_keys || []).includes(f) ? 'success' : ''"
                  >
                    {{ f }}{{ (row.bound_data_keys || []).includes(f) ? ' ✓' : '' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="状态" width="120">
                <template #default="{ row }">
                  <el-tag v-if="isFullyBound(row)" size="small" type="info">已全部绑定</el-tag>
                  <el-tag v-else-if="(row.bound_data_keys || []).length" size="small" type="warning">部分绑定</el-tag>
                  <span v-else class="eb-config__muted">未绑定</span>
                </template>
              </el-table-column>
            </el-table>
            <p v-if="availableSensors.length === 0" class="eb-config__empty-hint">
              主模型中暂无可选传感器，请先到 <el-link type="primary" @click="$router.push('/sensors')">传感器管理</el-link> 创建。
            </p>
          </section>

          <section class="eb-config__col">
            <div class="eb-config__col-head">
              <h3>已导入大屏 ({{ store.sensorBindings.length }})</h3>
            </div>
            <el-table :data="store.sensorBindings" size="small" max-height="500">
              <el-table-column label="ID" min-width="120">
                <template #default="{ row }">{{ row.sensor_id }}</template>
              </el-table-column>
              <el-table-column label="位号" min-width="140">
                <template #default="{ row }">
                  <el-input v-model="row.tag" size="small" @change="(v) => savePatch(row.id, { tag: v })" />
                </template>
              </el-table-column>
              <el-table-column label="区域" min-width="110">
                <template #default="{ row }">
                  <el-input v-model="row.area" size="small" @change="(v) => savePatch(row.id, { area: v })" />
                </template>
              </el-table-column>
              <el-table-column label="data_key" min-width="130">
                <template #default="{ row }">
                  <el-tag v-if="row.data_key" size="small" type="info">{{ row.data_key }}</el-tag>
                  <span v-else class="eb-config__muted">—</span>
                </template>
              </el-table-column>
              <el-table-column label="单位" min-width="90">
                <template #default="{ row }">
                  <el-input v-model="row.unit" size="small" @change="(v) => savePatch(row.id, { unit: v })" />
                </template>
              </el-table-column>
              <el-table-column label="高阈" min-width="110">
                <template #default="{ row }">
                  <el-input-number
                    v-model="row.hi_threshold"
                    size="small"
                    controls-position="right"
                    :precision="2"
                    @change="(v) => savePatch(row.id, { hi_threshold: v })"
                  />
                </template>
              </el-table-column>
              <el-table-column label="低阈" min-width="110">
                <template #default="{ row }">
                  <el-input-number
                    v-model="row.lo_threshold"
                    size="small"
                    controls-position="right"
                    :precision="2"
                    @change="(v) => savePatch(row.id, { lo_threshold: v })"
                  />
                </template>
              </el-table-column>
              <el-table-column label="严重度" min-width="110">
                <template #default="{ row }">
                  <el-select v-model="row.severity" size="small" @change="(v) => savePatch(row.id, { severity: v })">
                    <el-option v-for="lv in ['low', 'mid', 'high', 'critical']" :key="lv" :label="lv" :value="lv" />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column label="显示" width="70" align="center">
                <template #default="{ row }">
                  <el-switch v-model="row.is_visible" size="small" @change="(v) => savePatch(row.id, { is_visible: v })" />
                </template>
              </el-table-column>
              <el-table-column label="操作" width="160" align="center">
                <template #default="{ row }">
                  <el-button
                    size="small"
                    type="primary"
                    link
                    :disabled="!hasUnusedField(row)"
                    @click="onAddSiblingField(row)"
                  >
                    +字段
                  </el-button>
                  <el-button size="small" type="danger" link @click="onRemoveSensor(row.id)">移除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </section>
        </div>
      </el-tab-pane>

      <!-- ============ 设备绑定 ============ -->
      <el-tab-pane label="设备" name="devices">
        <div class="eb-config__panel">
          <section class="eb-config__col">
            <div class="eb-config__col-head">
              <h3>主模型可选设备</h3>
              <el-button
                size="small"
                type="primary"
                :disabled="selectedDeviceIds.length === 0"
                @click="onImportDevices"
              >
                导入选中 ({{ selectedDeviceIds.length }})
              </el-button>
            </div>
            <el-table
              :data="availableDevices"
              size="small"
              max-height="500"
              @selection-change="(rows) => (selectedDeviceIds = rows.map((r) => r.id))"
            >
              <el-table-column type="selection" width="40" />
              <el-table-column prop="device_id" label="ID" min-width="140" />
              <el-table-column prop="name" label="名称" min-width="180" show-overflow-tooltip />
              <el-table-column prop="device_type" label="类型" min-width="140" />
              <el-table-column label="命令" min-width="180">
                <template #default="{ row }">
                  <el-tag v-for="c in row.commands" :key="c" size="small" class="eb-config__tag">{{ c }}</el-tag>
                </template>
              </el-table-column>
            </el-table>
          </section>

          <section class="eb-config__col">
            <div class="eb-config__col-head">
              <h3>已导入大屏 ({{ store.deviceBindings.length }})</h3>
            </div>
            <el-table :data="store.deviceBindings" size="small" max-height="500">
              <el-table-column label="ID" min-width="140">
                <template #default="{ row }">{{ row.device_id }}</template>
              </el-table-column>
              <el-table-column label="位号" min-width="160">
                <template #default="{ row }">
                  <el-input v-model="row.tag" size="small" @change="(v) => savePatchDevice(row.id, { tag: v })" />
                </template>
              </el-table-column>
              <el-table-column label="区域" min-width="140">
                <template #default="{ row }">
                  <el-input v-model="row.area" size="small" @change="(v) => savePatchDevice(row.id, { area: v })" />
                </template>
              </el-table-column>
              <el-table-column label="显示" width="80" align="center">
                <template #default="{ row }">
                  <el-switch v-model="row.is_visible" size="small" @change="(v) => savePatchDevice(row.id, { is_visible: v })" />
                </template>
              </el-table-column>
              <el-table-column label="操作" width="80" align="center">
                <template #default="{ row }">
                  <el-button size="small" type="danger" link @click="onRemoveDevice(row.id)">移除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </section>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { useEBPlantConfigStore } from '@/stores/ebPlantConfig'

const store = useEBPlantConfigStore()

const activeTab = ref('sensors')
const selectedSensorIds = ref([])
const selectedDeviceIds = ref([])

// 传感器允许多字段绑定，所以"可选传感器"列表始终展示全部主模型传感器，
// 通过 bound_data_keys 区分"未绑定/部分绑定/已全部绑定"。
const availableSensors = computed(() => store.bindableSensors)
const availableDevices = computed(() =>
  store.bindableDevices.filter((d) => !d.already_bound),
)

function isFullyBound(sensor) {
  const fields = sensor.data_fields || []
  const bound = sensor.bound_data_keys || []
  if (!fields.length) {
    // 没有字段定义的传感器，存在任意一条 binding 就视为绑定
    return bound.length > 0
  }
  return fields.every((f) => bound.includes(f))
}

function canSelectSensor(sensor) {
  // 只允许"完全没绑定过"的传感器走批量导入（默认空 data_key 一条），
  // 已存在 binding 的请走"+字段"按钮，避免空 key 与已选字段冲突。
  return !(sensor.bound_data_keys || []).length
}

function hasUnusedField(row) {
  const fields = row.data_fields || []
  if (fields.length <= 1) return false
  const used = store.sensorBindings
    .filter((b) => b.sensor_id === row.sensor_id)
    .map((b) => b.data_key)
    .filter((k) => !!k)
  return fields.some((f) => !used.includes(f))
}

async function reload() {
  try {
    await store.loadAll()
  } catch (e) {
    ElMessage.error('加载失败: ' + (e?.message || e))
  }
}

onMounted(reload)

async function onImportSensors() {
  try {
    const { created } = await store.importSensors(selectedSensorIds.value)
    ElMessage.success(`已导入 ${selectedSensorIds.value.length} 个传感器，新增 ${created} 条点位`)
    selectedSensorIds.value = []
  } catch (e) {
    ElMessage.error('导入失败: ' + (e?.message || e))
  }
}

async function onImportDevices() {
  try {
    await store.importDevices(selectedDeviceIds.value)
    ElMessage.success(`已导入 ${selectedDeviceIds.value.length} 个设备`)
    selectedDeviceIds.value = []
  } catch (e) {
    ElMessage.error('导入失败: ' + (e?.message || e))
  }
}

async function savePatch(id, patch) {
  try {
    await store.patchSensorBinding(id, patch)
  } catch (e) {
    ElMessage.error('保存失败: ' + (e?.message || e))
  }
}

async function onAddSiblingField(row) {
  const used = store.sensorBindings
    .filter((b) => b.sensor_id === row.sensor_id)
    .map((b) => b.data_key)
  const candidates = (row.data_fields || []).filter((f) => !used.includes(f))
  if (!candidates.length) {
    ElMessage.info('该传感器的所有字段都已绑定')
    return
  }
  try {
    const { value: picked } = await ElMessageBox.prompt(
      `为 ${row.sensor_id} 添加另一个 data_key`,
      '追加字段',
      {
        confirmButtonText: '添加',
        cancelButtonText: '取消',
        inputType: 'text',
        inputValue: candidates[0],
        inputValidator: (v) => candidates.includes(v) || `请选择以下字段之一: ${candidates.join(', ')}`,
      },
    )
    await store.addSensorFieldBinding({
      sensor: row.sensor,
      data_key: picked,
      tag: `${row.tag || row.sensor_id}-${picked}`,
      area: row.area,
      severity: row.severity,
    })
    ElMessage.success(`已添加 ${row.sensor_id}::${picked}`)
  } catch (e) {
    if (e === 'cancel' || e === 'close') return
    ElMessage.error('添加失败: ' + (e?.response?.data?.detail || e?.message || e))
  }
}

async function savePatchDevice(id, patch) {
  try {
    await store.patchDeviceBinding(id, patch)
  } catch (e) {
    ElMessage.error('保存失败: ' + (e?.message || e))
  }
}

async function onRemoveSensor(id) {
  try {
    await store.removeSensorBinding(id)
    ElMessage.success('已移除')
  } catch (e) {
    ElMessage.error('移除失败: ' + (e?.message || e))
  }
}

async function onRemoveDevice(id) {
  try {
    await store.removeDeviceBinding(id)
    ElMessage.success('已移除')
  } catch (e) {
    ElMessage.error('移除失败: ' + (e?.message || e))
  }
}
</script>

<style scoped lang="scss">
.eb-config {
  padding: 20px 24px;
  min-height: calc(100vh - 64px);
}

.eb-config__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;

  h1 { margin: 0; font-size: 20px; }
  .eb-config__sub { margin: 4px 0 0; font-size: 12px; color: #888; }
}

.eb-config__tabs {
  background: #ffffff;
  padding: 12px 16px;
  border-radius: 6px;
}

.eb-config__panel {
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.eb-config__col {
  min-width: 0;
  background: #fafafa;
  border: 1px solid #ececec;
  border-radius: 8px;
  padding: 16px 18px 18px;
  overflow: hidden;

  :deep(.el-table) {
    border-radius: 6px;
  }

  :deep(.el-table__inner-wrapper) {
    border-radius: 6px;
    overflow: hidden;
  }
}

.eb-config__col-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;

  h3 { margin: 0; font-size: 14px; font-weight: 600; }
}

.eb-config__tag {
  margin-right: 4px;
}

.eb-config__empty-hint {
  margin-top: 12px;
  font-size: 12px;
  color: #888;
}

.eb-config__hint {
  margin: 0 0 8px;
  font-size: 12px;
  color: #888;
}

.eb-config__muted {
  font-size: 12px;
  color: #aaa;
}
</style>
