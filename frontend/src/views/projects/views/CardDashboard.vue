<template>
  <div class="card-dash">
    <!-- 仪表盘搜索与筛选工具栏 -->
    <div class="cd-toolbar iot-mb-md">
      <el-input
        v-model="searchQuery"
        placeholder="搜索点位名称 / 位号..."
        :prefix-icon="Search"
        clearable
        class="cd-search-input"
      />
      <div class="cd-filter-group">
        <el-radio-group v-model="statusFilter" size="small" class="segmented-radio-group">
          <el-radio-button value="all">全部</el-radio-button>
          <el-radio-button value="online">仅在线</el-radio-button>
          <el-radio-button value="alarm">报警/离线</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <transition-group name="list" tag="div" class="cd-sections-list">
      <section
        v-for="sec in filteredSections"
        :key="sec.id ?? '__unassigned__'"
        class="cd-section"
        :class="{ 'cd-section--collapsed': collapsedSections[sec.id] }"
      >
        <div class="cd-section__head" @click="toggleSection(sec.id)">
          <div class="cd-section__title-wrap">
            <el-icon class="cd-section__arrow" :class="{ 'is-collapsed': collapsedSections[sec.id] }">
              <ArrowRight />
            </el-icon>
            <span class="cd-section__name">{{ sec.name }}</span>
            <el-tag size="small" type="info" effect="light" round class="cd-section__badge">
              {{ sec.sensors.length }} 传感器 · {{ sec.devices.length }} 设备
            </el-tag>
          </div>
        </div>

        <el-collapse-transition>
          <div v-show="!collapsedSections[sec.id]" class="cd-section__content">
            <div v-if="sec.sensors && sec.sensors.length" class="cd-subsection">
              <div class="cd-subsection__title">传感器</div>
              <div class="card-dash__grid">
                <InstrumentCard
                  v-for="b in sec.sensors"
                  :key="'s-' + b.id"
                  :sample="sensorSample(b)"
                  :now="now"
                />
              </div>
            </div>

            <div v-if="sec.devices && sec.devices.length" class="cd-subsection">
              <div class="cd-subsection__title">设备</div>
              <div class="card-dash__grid">
                <DeviceCard
                  v-for="b in sec.devices"
                  :key="'d-' + b.id"
                  :binding="b"
                  :state="store.findDevice(b.device_id)"
                  :now="now"
                  :can-control="isStaff"
                />
              </div>
            </div>
          </div>
        </el-collapse-transition>
      </section>
    </transition-group>

    <div v-if="filteredSections.length === 0" class="card-dash__empty">
      <el-empty :description="searchQuery ? '未找到匹配的点位' : '本房间暂无可显示的点位'" />
      <p v-if="!searchQuery" class="card-dash__empty-hint">请到配置页将传感器 / 设备导入到本房间。</p>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { Search, ArrowRight } from '@element-plus/icons-vue'

import InstrumentCard from '../cards/InstrumentCard.vue'
import DeviceCard from '../cards/DeviceCard.vue'
import { useProjectStore } from '@/stores/project'
import { useUserStore } from '@/stores/user'

const props = defineProps({
  // 限定只渲染某个房间(分区)的成员；为 null 时渲染全部房间（兜底）
  sectionId: { type: [Number, null], default: null },
})

const store = useProjectStore()
const userStore = useUserStore()
const isStaff = computed(() => userStore.userInfo?.is_staff === true)

const sections = computed(() => {
  const all = store.layout?.sections || []
  return props.sectionId == null ? all : all.filter((s) => s.id === props.sectionId)
})

// 搜索和状态过滤
const searchQuery = ref('')
const statusFilter = ref('all') // 'all', 'online', 'alarm'

// 分区展开收起状态
const collapsedSections = ref({})

function toggleSection(secId) {
  collapsedSections.value[secId] = !collapsedSections.value[secId]
}

// 状态判断 helper
function isSensorOnline(s) {
  const live = store.findByBinding(s.point_id)
  if (!live || !live.ts) return false
  return (now.value - live.ts * 1000) < 120000
}

function isSensorAlarm(s) {
  const live = store.findByBinding(s.point_id)
  if (!live) return false
  const status = live.status
  return ['warn_high', 'warn_low', 'alarm_high', 'alarm_low'].includes(status)
}

function isDeviceOnline(d) {
  const state = store.findDevice(d.device_id)
  if (!state) return false
  const best = Math.max(state.last_seen || 0, state.ts || 0)
  if (best > 0) return (now.value - best * 1000) < 180000
  if (typeof state.is_online === 'boolean') return state.is_online
  return false
}

// 过滤后的分区数据
const filteredSections = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  const filter = statusFilter.value

  return sections.value.map(sec => {
    // 过滤传感器
    const filteredSensors = (sec.sensors || []).filter(s => {
      const name = s.sensor_name || s.tag || s.sensor_id || ''
      const tag = s.tag || ''
      const matchesQuery = name.toLowerCase().includes(query) || tag.toLowerCase().includes(query)
      if (!matchesQuery) return false

      if (filter === 'online') return isSensorOnline(s)
      if (filter === 'alarm') return isSensorAlarm(s)
      return true
    })

    // 过滤设备
    const filteredDevices = (sec.devices || []).filter(d => {
      const name = d.device_name || d.tag || d.device_id || ''
      const tag = d.tag || ''
      const matchesQuery = name.toLowerCase().includes(query) || tag.toLowerCase().includes(query)
      if (!matchesQuery) return false

      if (filter === 'online') return isDeviceOnline(d)
      if (filter === 'alarm') return !isDeviceOnline(d) // 离线设备在“报警/离线”过滤中显示
      return true
    })

    return {
      ...sec,
      sensors: filteredSensors,
      devices: filteredDevices,
      totalCount: filteredSensors.length + filteredDevices.length
    }
  }).filter(sec => sec.totalCount > 0)
})

// 卡片数据 = 成员静态元信息 merge 实时 sample（没数据也先出骨架卡）
function sensorSample(b) {
  const live = store.findByBinding(b.point_id) || {}
  return {
    sensor_id: b.point_id,
    tag: b.tag || b.sensor_id,
    unit: b.unit || '',
    hi_threshold: b.hi_threshold,
    lo_threshold: b.lo_threshold,
    status: 'normal',
    value: null,
    ts: null,
    metadata: { name: b.sensor_name || b.tag },
    ...live,
  }
}

const now = ref(Date.now())
let tickTimer = null
onMounted(() => { tickTimer = setInterval(() => { now.value = Date.now() }, 1000) })
onUnmounted(() => { if (tickTimer) clearInterval(tickTimer) })
</script>

<style scoped lang="scss">
.card-dash {
  display: flex;
  flex-direction: column;
  gap: var(--iot-spacing-md);
}

/* 工具栏 */
.cd-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--iot-spacing-md);
  flex-wrap: wrap;

  .cd-search-input {
    width: 280px;

    :deep(.el-input__wrapper) {
      border-radius: var(--iot-radius-base);
    }
  }

  /* 分段式选择器 */
  .segmented-radio-group {
    background: var(--iot-border-color-light);
    padding: 3px;
    border-radius: var(--iot-radius-base);
    border: 1px solid var(--iot-border-color-light);

    :deep(.el-radio-button__inner) {
      border: none !important;
      background: transparent !important;
      color: var(--iot-text-secondary);
      border-radius: calc(var(--iot-radius-base) - 2px) !important;
      padding: 6px 16px;
      font-size: var(--iot-font-size-xs);
      box-shadow: none !important;

      &:hover {
        color: var(--iot-text-primary);
      }
    }

    :deep(.el-radio-button__original-input:checked + .el-radio-button__inner) {
      background: var(--iot-bg-card) !important;
      color: var(--iot-text-primary) !important;
      box-shadow: var(--iot-shadow-sm) !important;
    }
  }
}

.cd-sections-list {
  display: flex;
  flex-direction: column;
  gap: var(--iot-spacing-lg);
}

/* 分区容器 */
.cd-section {
  background: var(--iot-bg-card);
  border: 1px solid var(--iot-border-color-light);
  border-radius: var(--iot-radius-lg);
  box-shadow: var(--iot-shadow-sm);
  padding: 0 var(--iot-spacing-lg) var(--iot-spacing-lg);
  transition: all var(--iot-transition-slow);

  &--collapsed {
    padding-bottom: 0;
  }
}

.cd-section__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--iot-spacing-md) 0;
  cursor: pointer;
  user-select: none;
}

.cd-section__title-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}

.cd-section__arrow {
  font-size: 14px;
  color: var(--iot-text-secondary);
  transition: transform var(--iot-transition-base);

  &.is-collapsed {
    transform: rotate(0deg);
  }

  &:not(.is-collapsed) {
    transform: rotate(90deg);
  }
}

.cd-section__name {
  font-size: var(--iot-font-size-md);
  font-weight: 600;
  color: var(--iot-text-primary);
}

.cd-section__badge {
  font-size: 10px;
  font-weight: 500;
}

.cd-section__content {
  padding-top: var(--iot-spacing-sm);
  border-top: 1px solid var(--iot-border-color-light);
}

.cd-subsection + .cd-subsection {
  margin-top: var(--iot-spacing-md);
}

.cd-subsection__title {
  font-size: var(--iot-font-size-xs);
  letter-spacing: 0.5px;
  color: var(--iot-text-secondary);
  margin-bottom: var(--iot-spacing-sm);
  padding-left: 6px;
  border-left: 3px solid var(--iot-color-primary);
}

.card-dash__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: var(--iot-spacing-md);
  align-items: start;
}

.card-dash__empty {
  text-align: center;
  padding: 60px 20px;
  color: var(--iot-text-secondary);
  font-size: var(--iot-font-size-base);
  border: 1px dashed var(--iot-border-color);
  background: var(--iot-bg-card);
  border-radius: var(--iot-radius-lg);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.card-dash__empty-hint {
  margin-top: 8px;
  font-size: 13px;
}

/* Transition Group Animations */
.list-enter-active,
.list-leave-active {
  transition: all 0.3s ease;
}
.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateY(15px);
}

@media screen and (max-width: 767px) {
  .cd-toolbar {
    flex-direction: column;
    align-items: stretch;

    .cd-search-input {
      width: 100%;
    }
  }
}
</style>

