<template>
  <div class="pw">
    <div class="pw-header">
      <!-- 面包屑与项目名称 -->
      <div class="pw-header__nav">
        <el-button class="pw-back-btn" :icon="ArrowLeft" text @click="$router.push('/projects')">返回项目</el-button>
        <div class="pw-header__title-area">
          <h1 class="pw-header__title">{{ project?.name || '加载中…' }}</h1>
          <span class="pw-header__code">{{ project?.code }}</span>
          <el-tag size="small" :type="getTagType(project?.scene_type)" effect="plain" round>{{ sceneLabel }}</el-tag>
        </div>
      </div>
      
      <!-- 监控状态面板 -->
      <div class="pw-monitor-panel">
        <div class="monitor-item">
          <span class="monitor-item__label">连接状态</span>
          <div class="monitor-item__value">
            <span class="ws-pulse-dot" :class="`ws-${store.wsStatus}`"></span>
            <span class="ws-label" :class="`ws-${store.wsStatus}`">{{ wsLabel }}</span>
          </div>
        </div>
        <div class="monitor-divider"></div>
        <div class="monitor-item">
          <span class="monitor-item__label">点位数量</span>
          <span class="monitor-item__value font-mono">{{ pointCount }}</span>
        </div>
        <div class="monitor-divider"></div>
        <div class="monitor-item">
          <span class="monitor-item__label">触发报警</span>
          <span
            class="monitor-item__value font-mono"
            :class="{ 'is-alert': roomAlarmCount > 0 }"
          >{{ roomAlarmCount }}</span>
        </div>
        <div class="monitor-divider"></div>
        <div class="monitor-item">
          <span class="monitor-item__label">数据更新</span>
          <span class="monitor-item__value font-mono">{{ lastUpdateLabel }}</span>
        </div>
        <div class="monitor-divider"></div>
        <div class="monitor-actions">
          <el-button 
            type="primary" 
            plain 
            :icon="Setting" 
            class="pw-config-btn"
            @click="$router.push(`/projects/${projectId}/config`)"
          >配置</el-button>
        </div>
      </div>
    </div>

    <!-- 房间(分区)导航 -->
    <div v-if="rooms.length" class="pw-room-nav">
      <el-icon class="pw-room-nav__icon"><House /></el-icon>
      <el-radio-group v-model="activeRoomId" class="pw-room-radio">
        <el-radio-button v-for="r in rooms" :key="r.id" :value="r.id">{{ r.name }}</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 当前房间的视图切换标签页 -->
    <el-tabs v-if="activeRoomId != null" v-model="activeView" class="pw__tabs segmented-tabs">
      <el-tab-pane
        v-for="t in viewTabs"
        :key="t.key"
        :name="t.key"
      >
        <template #label>
          <span class="tab-label-custom">
            <el-icon class="tab-icon"><component :is="getViewIcon(t.type)" /></el-icon>
            <span>{{ t.label }}</span>
          </span>
        </template>

        <transition name="fade" mode="out-in">
          <div :key="t.key" class="tab-content-wrap">
            <CardDashboard v-if="t.type === 'card'" :section-id="activeRoomId" />
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
            <ControlSchemeView
              v-else-if="t.type === 'control'"
              :project-id="projectId"
              :section-id="activeRoomId"
            />
            <div v-else class="pw__placeholder">{{ placeholderLabel(t.type) }}</div>
          </div>
        </transition>
      </el-tab-pane>
    </el-tabs>

    <div v-else class="pw__placeholder">
      该项目还没有房间（分区）。请到
      <el-link type="primary" :underline="false" @click="$router.push(`/projects/${projectId}/config`)">配置页</el-link>
      新建房间并导入传感器 / 设备。
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  ArrowLeft,
  Setting,
  Grid,
  Share,
  TrendCharts,
  Monitor,
  House,
  Cpu
} from '@element-plus/icons-vue'

import CardDashboard from './views/CardDashboard.vue'
import DiagramView from './views/DiagramView.vue'
import TimeseriesView from './views/TimeseriesView.vue'
import ControlSchemeView from './views/ControlSchemeView.vue'
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
const activeRoomId = ref(null)
const activeView = ref('')

store.reset(projectId)

// 房间列表来自 layout（含成员），房间优先导航
const rooms = computed(() => store.layout?.sections || [])
const activeRoom = computed(() => rooms.value.find((r) => r.id === activeRoomId.value) || null)
const activeRoomViews = computed(() => views.value.filter((v) => v.section === activeRoomId.value))

const SCENE_LABELS = { industrial: '工业装置', smart_home: '智能家居', custom: '自定义' }
const sceneLabel = computed(() => SCENE_LABELS[project.value?.scene_type] || '场景')

function getTagType(t) {
  if (t === 'industrial') return 'warning'
  if (t === 'smart_home') return 'success'
  return 'info'
}

function getViewIcon(type) {
  if (type === 'card') return Grid
  if (type === 'diagram') return Share
  if (type === 'timeseries') return TrendCharts
  if (type === 'control') return Cpu
  return Monitor
}

// 当前房间的视图 tab：无视图时给一个默认卡片大屏，保证开箱可看
const viewTabs = computed(() => {
  if (activeRoomId.value == null) return []
  if (activeRoomViews.value.length === 0) {
    return [{ key: `room-${activeRoomId.value}-default`, label: '卡片大屏', type: 'card', view: null }]
  }
  return activeRoomViews.value.map((v) => ({ key: String(v.id), label: v.name, type: v.view_type, view: v }))
})

// 选中当前房间的默认视图（is_default 优先，否则第一个；无视图则落到默认卡片）
function selectDefaultView() {
  const rv = activeRoomViews.value
  if (rv.length === 0) {
    activeView.value = `room-${activeRoomId.value}-default`
    return
  }
  const def = rv.find((v) => v.is_default) || rv[0]
  activeView.value = String(def.id)
}
watch(activeRoomId, () => { selectDefaultView() })

function placeholderLabel(type) {
  return '该视图类型暂未实现'
}

function onViewSaved({ id, config }) {
  const v = views.value.find((x) => x.id === id)
  if (v) v.config = config
}

// 点位数量 = 当前房间的传感器 + 设备
const pointCount = computed(() => {
  const r = activeRoom.value
  return r ? (r.sensors?.length || 0) + (r.devices?.length || 0) : 0
})

// 触发报警 = 当前房间内非 normal 状态的传感器数
const roomAlarmCount = computed(() => {
  const r = activeRoom.value
  if (!r) return 0
  let n = 0
  for (const s of r.sensors || []) {
    const live = store.findByBinding(s.point_id)
    if (live && live.status && live.status !== 'normal') n++
  }
  return n
})

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
  try {
    const data = await listViews(projectId)
    views.value = data.results || data || []
  } catch (e) {
    console.error('[project] 加载视图失败', e)
  }
  // 等 layout 就绪后再定房间：默认视图所在房间 > 第一个房间
  await Promise.all([store.loadLayout(projectId), store.loadSnapshot(projectId)])
  const defView = views.value.find((v) => v.is_default)
  activeRoomId.value = defView ? defView.section : (rooms.value[0]?.id ?? null)
  selectDefaultView()
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
  animation: iot-fade-in 0.4s ease forwards;
}

.pw-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--iot-spacing-lg);
  margin-bottom: var(--iot-spacing-lg);
  flex-wrap: wrap;

  &__nav {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .pw-back-btn {
    align-self: flex-start;
    padding: 0;
    height: auto;
    font-size: var(--iot-font-size-sm);
    color: var(--iot-text-secondary);

    &:hover {
      color: var(--iot-color-primary);
    }
  }

  &__title-area {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  &__title {
    font-size: var(--iot-font-size-xl);
    font-weight: 600;
    color: var(--iot-text-primary);
    margin: 0;
    letter-spacing: -0.01em;
  }

  &__code {
    font-family: var(--iot-font-mono, ui-monospace, 'SFMono-Regular', monospace);
    font-size: var(--iot-font-size-sm);
    color: var(--iot-text-secondary);
    background: var(--iot-border-color-light);
    padding: 2px 6px;
    border-radius: 4px;
  }
}

/* 状态面板 */
.pw-monitor-panel {
  background: var(--iot-bg-card);
  border: 1px solid var(--iot-border-color-light);
  border-radius: var(--iot-radius-lg);
  box-shadow: var(--iot-shadow-sm);
  display: flex;
  align-items: center;
  padding: 6px 16px;
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  transition: box-shadow var(--iot-transition-base);

  &:hover {
    box-shadow: var(--iot-shadow-base);
  }

  .monitor-item {
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 2px 12px;
    min-width: 80px;

    &__label {
      font-size: 10px;
      color: var(--iot-text-secondary);
      margin-bottom: 2px;
    }

    &__value {
      font-size: var(--iot-font-size-md);
      font-weight: 600;
      color: var(--iot-text-primary);
      display: flex;
      align-items: center;
      gap: 6px;
      line-height: 1.2;

      &.font-mono {
        font-family: var(--iot-font-mono, monospace);
      }

      &.is-alert {
        color: var(--iot-color-danger);
        animation: monitor-alert-pulse 1s infinite alternate;
      }
    }
  }

  .monitor-divider {
    width: 1px;
    height: 28px;
    background: var(--iot-border-color-light);
  }

  .monitor-actions {
    padding-left: 12px;
  }

  .pw-config-btn {
    height: 30px;
    padding: 0 14px;
    border-radius: var(--iot-radius-base);
  }
}

/* WS 连接点 */
.ws-pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--iot-text-placeholder);
  display: inline-block;

  &.ws-open {
    background: var(--iot-color-success);
    box-shadow: 0 0 0 0 rgba(76, 175, 130, 0.7);
    animation: ws-pulse 1.8s infinite;
  }
  &.ws-connecting {
    background: var(--iot-color-warning);
    box-shadow: 0 0 0 0 rgba(212, 160, 23, 0.7);
    animation: ws-pulse 1.8s infinite;
  }
  &.ws-error, &.ws-closed {
    background: var(--iot-color-danger);
  }
}

.ws-label {
  font-size: var(--iot-font-size-base);
  
  &.ws-open { color: var(--iot-color-success); }
  &.ws-connecting { color: var(--iot-color-warning); }
  &.ws-error, &.ws-closed { color: var(--iot-color-danger); }
}

/* 房间导航 */
.pw-room-nav {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: var(--iot-spacing-md);
  flex-wrap: wrap;

  &__icon {
    color: var(--iot-color-primary);
    font-size: 18px;
  }

  .pw-room-radio {
    flex-wrap: wrap;
    gap: 4px;
  }

  :deep(.el-radio-button__inner) {
    border-radius: var(--iot-radius-base) !important;
    border: 1px solid var(--iot-border-color-light);
    margin-right: 4px;
    box-shadow: none !important;
  }

  :deep(.el-radio-button:first-child .el-radio-button__inner) {
    border-left: 1px solid var(--iot-border-color-light);
  }

  :deep(.el-radio-button__original-input:checked + .el-radio-button__inner) {
    background: var(--iot-color-primary);
    border-color: var(--iot-color-primary);
    color: #fff;
  }
}

/* 分段式 Tab 样式 */
.segmented-tabs {
  margin-top: 4px;

  :deep(.el-tabs__header) {
    background: var(--iot-border-color-lighter);
    padding: 4px;
    border-radius: var(--iot-radius-lg);
    display: inline-flex;
    margin-bottom: var(--iot-spacing-lg);
    border: 1px solid var(--iot-border-color-light);
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
    height: 34px;
    line-height: 34px;
    padding: 0 18px !important;
    border-radius: var(--iot-radius-base);
    color: var(--iot-text-secondary) !important;
    font-weight: 500;
    transition: all var(--iot-transition-fast);
    font-size: var(--iot-font-size-sm);

    &:hover {
      color: var(--iot-text-primary) !important;
      background: rgba(0, 0, 0, 0.02);
    }

    &.is-active {
      color: var(--iot-text-primary) !important;
      background: var(--iot-bg-card);
      box-shadow: var(--iot-shadow-sm);
    }
  }
}

.tab-label-custom {
  display: flex;
  align-items: center;
  gap: 6px;

  .tab-icon {
    font-size: 14px;
  }
}

.tab-content-wrap {
  width: 100%;
}

.pw__placeholder {
  padding: 60px 20px;
  text-align: center;
  color: var(--iot-text-secondary);
  border: 1px dashed var(--iot-border-color);
  background: var(--iot-bg-card);
  border-radius: var(--iot-radius-lg);
}

/* Animations */
@keyframes ws-pulse {
  0% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(76, 175, 130, 0.7);
  }
  70% {
    transform: scale(1);
    box-shadow: 0 0 0 6px rgba(76, 175, 130, 0);
  }
  100% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(76, 175, 130, 0);
  }
}

@keyframes monitor-alert-pulse {
  from { text-shadow: 0 0 2px rgba(201, 74, 58, 0); }
  to { text-shadow: 0 0 8px rgba(201, 74, 58, 0.4); }
}

@media screen and (max-width: 767px) {
  .pw-header {
    flex-direction: column;
    align-items: stretch;
  }

  .pw-monitor-panel {
    justify-content: space-around;
    padding: 6px 8px;
    
    .monitor-item {
      min-width: 60px;
      padding: 2px 4px;
      align-items: center;
    }
  }
}
</style>

