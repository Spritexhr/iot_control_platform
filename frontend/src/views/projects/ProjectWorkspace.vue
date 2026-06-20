<template>
  <div class="pw">
    <div class="iot-page-header pw__header">
      <div class="pw__title">
        <el-button text :icon="ArrowLeft" @click="$router.push('/projects')">项目</el-button>
        <h1 class="iot-page-title pw__name">{{ project?.name || '加载中…' }}</h1>
        <span class="pw__code">{{ project?.code }}</span>
        <el-tag size="small" effect="plain" round>{{ sceneLabel }}</el-tag>
      </div>
      <div class="pw__status">
        <span class="pw__stat"><i>实时</i><b :class="`ws-${store.wsStatus}`">{{ wsLabel }}</b></span>
        <span class="pw__stat"><i>点位</i><b>{{ pointCount }}</b></span>
        <span class="pw__stat"><i>报警</i><b :class="{ 'is-alert': store.alarmCount > 0 }">{{ store.alarmCount }}</b></span>
        <span class="pw__stat"><i>更新</i><b>{{ lastUpdateLabel }}</b></span>
        <el-button size="small" type="primary" :icon="Setting" @click="$router.push(`/projects/${projectId}/config`)">配置</el-button>
      </div>
    </div>

    <el-tabs v-model="activeView" class="pw__tabs">
      <el-tab-pane
        v-for="t in viewTabs"
        :key="t.key"
        :label="t.label"
        :name="t.key"
      >
        <CardDashboard v-if="t.type === 'card'" />
        <DiagramView
          v-else-if="t.type === 'diagram' && t.view"
          :view="t.view"
          :can-edit="isStaff"
          @saved="onViewSaved"
        />
        <TimeseriesView
          v-else-if="t.type === 'timeseries' && t.view"
          :view="t.view"
          :can-edit="isStaff"
          @saved="onViewSaved"
        />
        <div v-else class="pw__placeholder">{{ placeholderLabel(t.type) }}</div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft, Setting } from '@element-plus/icons-vue'

import CardDashboard from './views/CardDashboard.vue'
import DiagramView from './views/DiagramView.vue'
import TimeseriesView from './views/TimeseriesView.vue'
import { getProject, listViews, buildProjectWsPath } from '@/api/projects'
import { useWebSocket, buildWsUrl } from '@/composables/useWebSocket'
import { useProjectStore } from '@/stores/project'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const projectId = Number(route.params.id)

const store = useProjectStore()
const userStore = useUserStore()
const isStaff = computed(() => userStore.userInfo?.is_staff === true)
const project = ref(null)
const views = ref([])
const activeView = ref('__default__')

store.reset(projectId)

const SCENE_LABELS = { industrial: '工业装置', smart_home: '智能家居', custom: '自定义' }
const sceneLabel = computed(() => SCENE_LABELS[project.value?.scene_type] || '场景')

// 视图 tab：无视图时给一个默认卡片大屏，保证开箱可看
const viewTabs = computed(() => {
  if (views.value.length === 0) {
    return [{ key: '__default__', label: '卡片大屏', type: 'card', view: null }]
  }
  return views.value.map((v) => ({ key: String(v.id), label: v.name, type: v.view_type, view: v }))
})

function placeholderLabel(type) {
  if (type === 'timeseries') return '时序趋势视图将在阶段 3 上线'
  return '该视图类型暂未实现'
}

function onViewSaved({ id, config }) {
  const v = views.value.find((x) => x.id === id)
  if (v) v.config = config
}

const pointCount = computed(() =>
  (store.layout?.sections || []).reduce(
    (n, sec) => n + (sec.sensors?.length || 0) + (sec.devices?.length || 0),
    0,
  ),
)

const WS_LABELS = {
  idle: '未连接', connecting: '连接中', open: '已连接',
  closed: '已断开', error: '异常', unauthorized: '未授权',
}
const wsLabel = computed(() => WS_LABELS[store.wsStatus] || store.wsStatus)

const now = ref(Date.now())
setInterval(() => { now.value = Date.now() }, 1000)
const lastUpdateLabel = computed(() => {
  if (!store.lastUpdateTs) return '—'
  const diff = Math.max(0, Math.floor((now.value - store.lastUpdateTs) / 1000))
  return diff < 2 ? '刚刚' : `${diff}s 前`
})

async function init() {
  try {
    project.value = await getProject(projectId)
  } catch (e) {
    console.error('[project] 加载项目失败', e)
  }
  store.loadLayout(projectId)
  store.loadSnapshot(projectId)
  try {
    const data = await listViews(projectId)
    views.value = data.results || data || []
    const def = views.value.find((v) => v.is_default) || views.value[0]
    if (def) activeView.value = String(def.id)
  } catch (e) {
    console.error('[project] 加载视图失败', e)
  }
}
init()

const { displayStatus } = useWebSocket(
  () => buildWsUrl(buildProjectWsPath(projectId)),
  {
    snapshot:        (data) => store.applySnapshot(data),
    sample:          (data) => store.applySample(data),
    'device.status': (data) => store.applyDeviceStatus(data),
  },
)
watch(displayStatus, (v) => { store.wsStatus = v }, { immediate: true })
</script>

<style scoped lang="scss">
.pw {
  padding: 0;
}

.pw__header {
  align-items: flex-start;
}

.pw__title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.pw__name {
  margin: 0;
}

.pw__code {
  font-family: var(--iot-font-mono, ui-monospace, 'SFMono-Regular', monospace);
  font-size: var(--iot-font-size-sm);
  color: var(--iot-text-secondary);
}

.pw__status {
  display: flex;
  align-items: center;
  gap: var(--iot-spacing-md);
}

.pw__stat {
  display: flex;
  flex-direction: column;
  align-items: flex-end;

  i {
    font-style: normal;
    font-size: 10px;
    color: var(--iot-text-secondary);
    letter-spacing: 0.5px;
  }
  b {
    font-size: var(--iot-font-size-md);
    color: var(--iot-text-primary);
    font-variant-numeric: tabular-nums;

    &.is-alert { color: var(--iot-color-danger); }
    &.ws-open { color: var(--iot-color-success); }
    &.ws-error, &.ws-closed, &.ws-unauthorized { color: var(--iot-color-danger); }
    &.ws-connecting { color: var(--iot-color-warning); }
  }
}

.pw__placeholder {
  padding: 60px 20px;
  text-align: center;
  color: var(--iot-text-secondary);
  border: 1px dashed var(--iot-border-color);
  background: var(--iot-bg-card);
  border-radius: var(--iot-radius-lg);
}
</style>
