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
            <el-table
              :data="availableSensors"
              size="small"
              max-height="500"
              @selection-change="(rows) => (selectedSensorIds = rows.map((r) => r.id))"
            >
              <el-table-column type="selection" width="40" />
              <el-table-column prop="sensor_id" label="ID" width="120" />
              <el-table-column prop="name" label="名称" />
              <el-table-column prop="sensor_type" label="类型" width="120" />
              <el-table-column label="字段" width="180">
                <template #default="{ row }">
                  <el-tag v-for="f in row.data_fields" :key="f" size="small" class="eb-config__tag">{{ f }}</el-tag>
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
              <el-table-column label="ID" width="100">
                <template #default="{ row }">{{ row.sensor_id }}</template>
              </el-table-column>
              <el-table-column label="位号" width="110">
                <template #default="{ row }">
                  <el-input v-model="row.tag" size="small" @change="(v) => savePatch(row.id, { tag: v })" />
                </template>
              </el-table-column>
              <el-table-column label="区域" width="90">
                <template #default="{ row }">
                  <el-input v-model="row.area" size="small" @change="(v) => savePatch(row.id, { area: v })" />
                </template>
              </el-table-column>
              <el-table-column label="data_key" width="130">
                <template #default="{ row }">
                  <el-select
                    v-model="row.data_key"
                    size="small"
                    clearable
                    @change="(v) => savePatch(row.id, { data_key: v || '' })"
                  >
                    <el-option v-for="f in row.data_fields" :key="f" :label="f" :value="f" />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column label="单位" width="80">
                <template #default="{ row }">
                  <el-input v-model="row.unit" size="small" @change="(v) => savePatch(row.id, { unit: v })" />
                </template>
              </el-table-column>
              <el-table-column label="高阈" width="90">
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
              <el-table-column label="低阈" width="90">
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
              <el-table-column label="严重度" width="100">
                <template #default="{ row }">
                  <el-select v-model="row.severity" size="small" @change="(v) => savePatch(row.id, { severity: v })">
                    <el-option v-for="lv in ['low', 'mid', 'high', 'critical']" :key="lv" :label="lv" :value="lv" />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column label="显示" width="60">
                <template #default="{ row }">
                  <el-switch v-model="row.is_visible" size="small" @change="(v) => savePatch(row.id, { is_visible: v })" />
                </template>
              </el-table-column>
              <el-table-column label="" width="60">
                <template #default="{ row }">
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
              <el-table-column prop="device_id" label="ID" width="120" />
              <el-table-column prop="name" label="名称" />
              <el-table-column prop="device_type" label="类型" width="120" />
              <el-table-column label="命令" width="180">
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
              <el-table-column label="ID" width="100">
                <template #default="{ row }">{{ row.device_id }}</template>
              </el-table-column>
              <el-table-column label="位号" width="120">
                <template #default="{ row }">
                  <el-input v-model="row.tag" size="small" @change="(v) => savePatchDevice(row.id, { tag: v })" />
                </template>
              </el-table-column>
              <el-table-column label="区域" width="100">
                <template #default="{ row }">
                  <el-input v-model="row.area" size="small" @change="(v) => savePatchDevice(row.id, { area: v })" />
                </template>
              </el-table-column>
              <el-table-column label="显示" width="80">
                <template #default="{ row }">
                  <el-switch v-model="row.is_visible" size="small" @change="(v) => savePatchDevice(row.id, { is_visible: v })" />
                </template>
              </el-table-column>
              <el-table-column label="" width="80">
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
import { ElMessage } from 'element-plus'

import { useEBPlantConfigStore } from '@/stores/ebPlantConfig'

const store = useEBPlantConfigStore()

const activeTab = ref('sensors')
const selectedSensorIds = ref([])
const selectedDeviceIds = ref([])

const availableSensors = computed(() =>
  store.bindableSensors.filter((s) => !s.already_bound),
)
const availableDevices = computed(() =>
  store.bindableDevices.filter((d) => !d.already_bound),
)

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
    await store.importSensors(selectedSensorIds.value)
    ElMessage.success(`已导入 ${selectedSensorIds.value.length} 个传感器`)
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
  display: grid;
  grid-template-columns: 1fr 1.6fr;
  gap: 16px;
}

.eb-config__col-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;

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
</style>
