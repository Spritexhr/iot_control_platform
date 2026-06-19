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
  gap: 20px;
}

.cd-section {
  background: #ffffff;
  border: 1px solid #d8d6cc;
  border-radius: 6px;
  padding: 14px 16px 16px;
}

.cd-section__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 10px;
  margin-bottom: 12px;
  border-bottom: 1px solid #e6e4da;
}

.cd-section__name {
  font-size: 15px;
  font-weight: 600;
  color: #2a2a2a;
}

.cd-section__count {
  font-size: 11px;
  color: #999;
  font-family: 'JetBrains Mono', monospace;
}

.cd-subsection + .cd-subsection {
  margin-top: 14px;
}

.cd-subsection__title {
  font-size: 11px;
  letter-spacing: 1px;
  color: #8a8a82;
  margin-bottom: 8px;
  padding-left: 6px;
  border-left: 3px solid #c9b89a;
}

.card-dash__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
  align-items: start;
}

.card-dash__empty {
  text-align: center;
  padding: 60px 20px;
  color: #888;
  font-size: 14px;
  border: 1px dashed #aaa;
  background: #ffffff;
  border-radius: 6px;
}

.card-dash__empty-hint {
  margin-top: 8px;
  font-size: 13px;
}
</style>
