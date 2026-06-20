<template>
  <div class="ts">
    <div class="ts__bar">
      <el-select v-model="selectedSource" placeholder="选择数据源" style="width: 240px" @change="onSourceChange">
        <el-option-group label="传感器">
          <el-option
            v-for="s in sourceOptions.sensors"
            :key="`sensor:${s.id}`"
            :label="`${s.name} (${s.id})`"
            :value="`sensor:${s.id}`"
          />
        </el-option-group>
        <el-option-group label="设备">
          <el-option
            v-for="d in sourceOptions.devices"
            :key="`device:${d.id}`"
            :label="`${d.name} (${d.id})`"
            :value="`device:${d.id}`"
          />
        </el-option-group>
      </el-select>

      <el-select
        v-model="selectedFields"
        multiple
        collapse-tags
        collapse-tags-tooltip
        placeholder="选择字段"
        style="width: 220px"
        :disabled="!availableFields.length"
      >
        <el-option v-for="f in availableFields" :key="f" :label="f" :value="f" />
      </el-select>

      <el-select v-model="quickRange" style="width: 120px" @change="onQuickRangeChange">
        <el-option label="近 1 小时" :value="1" />
        <el-option label="近 6 小时" :value="6" />
        <el-option label="近 24 小时" :value="24" />
        <el-option label="近 7 天" :value="168" />
        <el-option label="自定义" value="custom" />
      </el-select>

      <el-date-picker
        v-if="quickRange === 'custom'"
        v-model="customRange"
        type="datetimerange"
        range-separator="至"
        start-placeholder="开始"
        end-placeholder="结束"
        format="YYYY-MM-DD HH:mm"
        value-format="YYYY-MM-DDTHH:mm:ss"
        style="width: 340px"
      />

      <el-button :loading="loading" size="small" @click="fetchSeries">刷新</el-button>
      <el-button v-if="canEdit" size="small" type="primary" plain :loading="saving" @click="saveDefault">
        保存为默认
      </el-button>
    </div>

    <div v-loading="loading" class="ts__chart-wrap">
      <div v-if="!selectedSource" class="ts__empty">请选择一个数据源</div>
      <div v-else-if="!hasPoints && !loading" class="ts__empty">当前时间窗内无数据</div>
      <div v-show="hasPoints" ref="chartEl" class="ts__chart" />
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'

import { getProjectSeries, updateView } from '@/api/projects'
import { useProjectStore } from '@/stores/project'

const props = defineProps({
  view: { type: Object, required: true },     // ProjectView: { id, config:{source,fields,quickRange} }
  canEdit: { type: Boolean, default: false },
})
const emit = defineEmits(['saved'])

const store = useProjectStore()

const selectedSource = ref('')   // "sensor:ID" / "device:ID"
const selectedFields = ref([])
const quickRange = ref(24)
const customRange = ref([])
const seriesData = ref({ points: [], events: [], fields: [], count: 0, truncated: false })
const loading = ref(false)
const saving = ref(false)

const chartEl = ref(null)
let chartInstance = null

const hasPoints = computed(() => (seriesData.value.points || []).length > 0)
// 可选字段以 series 响应里的 fields 为准（设备字段来自 config_parameters，不在 layout 里）
const availableFields = computed(() => seriesData.value.fields || [])

// 数据源 = 本项目成员（按 sensor_id / device_id 去重）
const sourceOptions = computed(() => {
  const sensors = new Map()
  const devices = new Map()
  for (const sec of store.layout?.sections || []) {
    for (const s of sec.sensors || []) {
      if (s.sensor_id && !sensors.has(s.sensor_id)) sensors.set(s.sensor_id, { id: s.sensor_id, name: s.sensor_name || s.tag })
    }
    for (const d of sec.devices || []) {
      if (d.device_id && !devices.has(d.device_id)) devices.set(d.device_id, { id: d.device_id, name: d.device_name || d.tag })
    }
  }
  return { sensors: [...sensors.values()], devices: [...devices.values()] }
})

function getRange() {
  if (quickRange.value === 'custom') {
    if (!customRange.value || customRange.value.length !== 2) return null
    return { start: customRange.value[0], end: customRange.value[1] }
  }
  const end = new Date()
  const start = new Date(end.getTime() - quickRange.value * 3600 * 1000)
  return { start: start.toISOString(), end: end.toISOString() }
}

function onSourceChange() {
  selectedFields.value = []
  fetchSeries()
}
function onQuickRangeChange() {
  if (quickRange.value !== 'custom') fetchSeries()
}

async function fetchSeries() {
  if (!selectedSource.value) return
  const range = getRange()
  if (!range) { ElMessage.warning('请选择有效时间范围'); return }
  const [kind, sourceId] = selectedSource.value.split(':')
  loading.value = true
  try {
    const res = await getProjectSeries(props.view.project ?? store.currentProjectId, {
      kind, sourceId, start: range.start, end: range.end,
    })
    seriesData.value = res
    // 首次/换源后默认选前 2 个字段
    if (!selectedFields.value.length) {
      selectedFields.value = (res.fields || []).slice(0, 2)
    }
    await nextTick()
    renderChart()
  } catch (e) {
    ElMessage.error('获取数据失败：' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

function coerceNumber(v) {
  if (v === null || v === undefined) return null
  if (typeof v === 'boolean') return v ? 1 : 0
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

function renderChart() {
  if (!chartEl.value) return
  if (!chartInstance) chartInstance = echarts.init(chartEl.value)
  const points = seriesData.value.points || []
  const events = seriesData.value.events || []
  const fields = selectedFields.value.length ? selectedFields.value : availableFields.value.slice(0, 2)

  const series = fields.map((field) => ({
    name: field,
    type: 'line',
    smooth: true,
    showSymbol: points.length < 200,
    connectNulls: false,
    sampling: 'lttb',
    data: points.map((p) => [p.t, coerceNumber(p.data?.[field])]),
  }))

  if (events.length && series.length) {
    series[0] = {
      ...series[0],
      markLine: {
        symbol: 'none',
        silent: true,
        lineStyle: { color: 'rgba(255, 159, 64, 0.6)', type: 'dashed' },
        data: events.slice(0, 50).map((e) => ({
          xAxis: e.t,
          label: { formatter: e.event || '', position: 'end', fontSize: 10 },
        })),
      },
    }
  }

  chartInstance.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: { data: fields, top: 0 },
    grid: { left: 50, right: 30, top: 40, bottom: 60 },
    xAxis: { type: 'time', axisLabel: { hideOverlap: true } },
    yAxis: { type: 'value', scale: true },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 24, bottom: 10 }],
    series,
  }, { notMerge: true })
}

function handleResize() { chartInstance?.resize() }

async function saveDefault() {
  saving.value = true
  try {
    const config = {
      source: selectedSource.value,
      fields: selectedFields.value,
      quickRange: quickRange.value,
    }
    await updateView(props.view.id, { config })
    emit('saved', { id: props.view.id, config })
    ElMessage.success('已保存为默认')
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
  // 从 config 恢复默认选择
  const cfg = props.view.config || {}
  if (cfg.source) {
    selectedSource.value = cfg.source
    if (Array.isArray(cfg.fields)) selectedFields.value = cfg.fields
    if (cfg.quickRange) quickRange.value = cfg.quickRange
    fetchSeries()
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
  chartInstance = null
})

watch(selectedFields, () => {
  if (selectedSource.value && hasPoints.value) renderChart()
})
</script>

<style scoped lang="scss">
.ts {
  display: flex;
  flex-direction: column;
  background: var(--iot-bg-card);
  border: 1px solid var(--iot-border-color-light);
  border-radius: var(--iot-radius-lg);
  box-shadow: var(--iot-shadow-sm);
  padding: var(--iot-spacing-md);
}

.ts__bar {
  display: flex;
  flex-wrap: wrap;
  gap: var(--iot-spacing-sm);
  align-items: center;
  margin-bottom: var(--iot-spacing-md);
}

.ts__chart-wrap {
  position: relative;
  min-height: 480px;
}

.ts__chart {
  width: 100%;
  height: 480px;
}

.ts__empty {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--iot-text-placeholder);
  font-size: var(--iot-font-size-base);
}
</style>
