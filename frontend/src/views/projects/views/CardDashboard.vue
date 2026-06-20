<template>
  <div class="card-dash">
    <section
      v-for="sec in sections"
      :key="sec.id ?? '__unassigned__'"
      class="cd-section"
    >
      <div class="cd-section__head">
        <span class="cd-section__name">{{ sec.name }}</span>
        <span class="cd-section__count">
          {{ (sec.sensors?.length || 0) }} 传感器 · {{ (sec.devices?.length || 0) }} 设备
        </span>
      </div>

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
    </section>

    <div v-if="sections.length === 0" class="card-dash__empty">
      <p>暂无可显示的点位。</p>
      <p class="card-dash__empty-hint">请到配置页建立分区，并从主模型选取要展示的传感器 / 设备。</p>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'

import InstrumentCard from '../cards/InstrumentCard.vue'
import DeviceCard from '../cards/DeviceCard.vue'
import { useProjectStore } from '@/stores/project'
import { useUserStore } from '@/stores/user'

const store = useProjectStore()
const userStore = useUserStore()
const isStaff = computed(() => userStore.userInfo?.is_staff === true)

const sections = computed(() => store.layout?.sections || [])

// 卡片数据 = 成员静态元信息 merge 实时 sample（没数据也先出骨架卡）
function sensorSample(b) {
  const live = store.findByBinding(b.point_id) || {}
  return {
    sensor_id: b.point_id,
    tag: b.tag || b.sensor_id,
    unit: b.unit || '',
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
  gap: var(--iot-spacing-lg);
}

.cd-section {
  background: var(--iot-bg-card);
  border: 1px solid var(--iot-border-color-light);
  border-radius: var(--iot-radius-lg);
  box-shadow: var(--iot-shadow-sm);
  padding: var(--iot-spacing-md) var(--iot-spacing-lg) var(--iot-spacing-lg);
}

.cd-section__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 10px;
  margin-bottom: var(--iot-spacing-md);
  border-bottom: 1px solid var(--iot-border-color-light);
}

.cd-section__name {
  font-size: var(--iot-font-size-md);
  font-weight: 600;
  color: var(--iot-text-primary);
}

.cd-section__count {
  font-size: var(--iot-font-size-xs);
  color: var(--iot-text-secondary);
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
}

.card-dash__empty-hint {
  margin-top: 8px;
  font-size: 13px;
}
</style>
