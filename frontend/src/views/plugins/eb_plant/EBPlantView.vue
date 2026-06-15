<template>
  <div class="eb-plant">
    <!-- 顶部状态栏 -->
    <header class="eb-plant__header">
      <div class="eb-plant__title">
        <span class="eb-plant__title-tag">PLANT</span>
        <h1>全厂设备辅助监控大屏</h1>
        <span class="eb-plant__sub">Plant-wide Equipment Monitoring · IoT Layer</span>
      </div>
      <div class="eb-plant__status">
        <div class="eb-plant__stat">
          <span class="eb-plant__stat-label">实时</span>
          <span class="eb-plant__stat-value" :class="`status-${sseStatus}`">{{ sseStatusLabel }}</span>
        </div>
        <div class="eb-plant__stat">
          <span class="eb-plant__stat-label">点位</span>
          <span class="eb-plant__stat-value">{{ store.samplesList.length }}</span>
        </div>
        <div class="eb-plant__stat">
          <span class="eb-plant__stat-label">报警</span>
          <span class="eb-plant__stat-value" :class="{ 'is-alert': store.alarmCount > 0 }">
            {{ store.alarmCount }}
          </span>
        </div>
        <div class="eb-plant__stat">
          <span class="eb-plant__stat-label">更新</span>
          <span class="eb-plant__stat-value">{{ lastUpdateLabel }}</span>
        </div>
      </div>
    </header>

    <!-- 操作栏 -->
    <div class="eb-plant__toolbar">
      <el-button size="small" type="primary" @click="$router.push('/plugins/eb_plant/config')">
        配置面板
      </el-button>
      <el-button size="small" @click="$router.push('/plugins/plant_diagram')">
        P&amp;ID 画板
      </el-button>
    </div>

    <!-- 仪表卡片网格 -->
    <main class="eb-plant__grid">
      <InstrumentCard
        v-for="s in store.samplesList"
        :key="s.sensor_id"
        :sample="s"
        :now="now"
      />
      <div v-if="store.samplesList.length === 0" class="eb-plant__empty">
        <p>暂无可显示的传感器。</p>
        <p class="eb-plant__empty-hint">
          请先到
          <el-link type="primary" @click="$router.push('/plugins/eb_plant/config')">
            配置面板
          </el-link>
          从主模型选取要展示的传感器。
        </p>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'

import InstrumentCard from './InstrumentCard.vue'
import { useWebSocket, buildWsUrl } from '@/composables/useWebSocket'
import { usePlantStore } from '@/stores/plant'
import { buildPlantWsPath } from '@/api/plugins/eb_plant'

const store = usePlantStore()

const sseStatus = computed(() => store.sseStatus)
const sseStatusLabel = computed(() => ({
  idle: '未连接',
  connecting: '连接中',
  open: '已连接',
  closed: '已断开',
  error: '异常',
  unauthorized: '未授权',
}[sseStatus.value] || sseStatus.value))

const now = ref(Date.now())
let tickTimer = null
onMounted(() => {
  tickTimer = setInterval(() => { now.value = Date.now() }, 1000)
})
onUnmounted(() => {
  if (tickTimer) clearInterval(tickTimer)
})

const lastUpdateLabel = computed(() => {
  if (!store.lastUpdateTs) return '—'
  const diff = Math.max(0, Math.floor((now.value - store.lastUpdateTs) / 1000))
  if (diff < 2) return '刚刚'
  return `${diff}s 前`
})

// 1. 初始拉一次快照（WS 建连后会再发一次 snapshot 全量覆盖，这里只是首屏不空白）
store.loadSnapshot()

// 2. 建立 WebSocket 长连接（连上后 consumer 会立刻发 snapshot 事件覆盖）
const { displayStatus } = useWebSocket(
  () => buildWsUrl(buildPlantWsPath()),
  {
    snapshot: (data) => store.applySnapshot(data),
    sample:   (data) => store.applySample(data),
  },
)

watch(displayStatus, (v) => { store.sseStatus = v }, { immediate: true })
</script>

<style scoped lang="scss">
.eb-plant {
  min-height: calc(100vh - 64px);
  background: #f4f3ee;
  background-image:
    linear-gradient(rgba(0, 0, 0, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 0, 0, 0.04) 1px, transparent 1px);
  background-size: 24px 24px;
  padding: 20px 24px;
  font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  color: #2a2a2a;
}

.eb-plant__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  padding-bottom: 14px;
  border-bottom: 2px solid #2a2a2a;
  margin-bottom: 16px;
}

.eb-plant__title-tag {
  display: inline-block;
  padding: 2px 8px;
  background: #2a2a2a;
  color: #fafaf7;
  font-size: 11px;
  letter-spacing: 2px;
  font-family: 'JetBrains Mono', monospace;
  margin-right: 12px;
  vertical-align: middle;
}

.eb-plant__title h1 {
  display: inline-block;
  font-size: 20px;
  font-weight: 600;
  margin: 0;
  vertical-align: middle;
}

.eb-plant__sub {
  display: block;
  margin-top: 4px;
  font-size: 11px;
  color: #777;
  letter-spacing: 1px;
  font-family: 'JetBrains Mono', monospace;
}

.eb-plant__status {
  display: flex;
  gap: 18px;
}

.eb-plant__stat {
  text-align: right;
}

.eb-plant__stat-label {
  display: block;
  font-size: 10px;
  color: #888;
  letter-spacing: 1px;
}

.eb-plant__stat-value {
  display: block;
  font-size: 16px;
  font-weight: 600;
  font-family: 'JetBrains Mono', monospace;
  font-variant-numeric: tabular-nums;

  &.is-alert { color: #c0392b; }
  &.status-open { color: #2e7d4f; }
  &.status-error, &.status-closed { color: #c0392b; }
  &.status-connecting { color: #b07a16; }
}

.eb-plant__toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.eb-plant__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

.eb-plant__empty {
  grid-column: 1 / -1;
  text-align: center;
  padding: 60px 20px;
  color: #888;
  font-size: 14px;
  border: 1px dashed #aaa;
  background: #ffffff;
}

.eb-plant__empty-hint {
  margin-top: 8px;
  font-size: 13px;
}
</style>
