<template>
  <div class="pw">
    <header class="pw__header">
      <div class="pw__title">
        <el-button link class="pw__back" @click="$router.push('/projects')">← 项目</el-button>
        <span class="pw__tag">{{ sceneLabel }}</span>
        <h1>{{ project?.name || '加载中…' }}</h1>
        <span class="pw__code">{{ project?.code }}</span>
      </div>
      <div class="pw__status">
        <span class="pw__stat"><i>实时</i><b :class="`ws-${store.wsStatus}`">{{ wsLabel }}</b></span>
        <span class="pw__stat"><i>点位</i><b>{{ pointCount }}</b></span>
        <span class="pw__stat"><i>报警</i><b :class="{ 'is-alert': store.alarmCount > 0 }">{{ store.alarmCount }}</b></span>
        <span class="pw__stat"><i>更新</i><b>{{ lastUpdateLabel }}</b></span>
        <el-button size="small" type="primary" @click="$router.push(`/projects/${projectId}/config`)">配置</el-button>
      </div>
    </header>

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
        <div v-else class="pw__placeholder">{{ placeholderLabel(t.type) }}</div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import CardDashboard from './views/CardDashboard.vue'
import DiagramView from './views/DiagramView.vue'
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
  min-height: calc(100vh - 64px);
  background: #f4f3ee;
  background-image:
    linear-gradient(rgba(0, 0, 0, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 0, 0, 0.04) 1px, transparent 1px);
  background-size: 24px 24px;
  padding: 20px 24px;
  color: #2a2a2a;
}

.pw__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  padding-bottom: 14px;
  border-bottom: 2px solid #2a2a2a;
  margin-bottom: 12px;
}

.pw__title {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.pw__back { font-size: 12px; }

.pw__tag {
  padding: 2px 8px;
  background: #2a2a2a;
  color: #fafaf7;
  font-size: 11px;
  letter-spacing: 1px;
  font-family: 'JetBrains Mono', monospace;
}

.pw__title h1 {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
}

.pw__code {
  font-size: 12px;
  color: #888;
  font-family: 'JetBrains Mono', monospace;
}

.pw__status {
  display: flex;
  align-items: center;
  gap: 16px;
}

.pw__stat {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  i { font-style: normal; font-size: 10px; color: #888; letter-spacing: 1px; }
  b {
    font-size: 15px;
    font-family: 'JetBrains Mono', monospace;
    font-variant-numeric: tabular-nums;
    &.is-alert { color: #c0392b; }
    &.ws-open { color: #2e7d4f; }
    &.ws-error, &.ws-closed, &.ws-unauthorized { color: #c0392b; }
    &.ws-connecting { color: #b07a16; }
  }
}

.pw__placeholder {
  padding: 60px 20px;
  text-align: center;
  color: #999;
  font-size: 14px;
  border: 1px dashed #bbb;
  background: #fff;
  border-radius: 6px;
}
</style>
