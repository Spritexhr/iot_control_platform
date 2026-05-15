import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { getPlantSnapshot } from '@/api/plugins/eb_plant'

/**
 * EB 装置实时数据 store。
 * - samples: Map<sensor_id, sample>,sample 字段见后端 PointSample.to_dict()
 * - SSE 推 sample 事件 → applySample 更新单点
 * - 初始化或重连后用 applySnapshot 全量刷新
 */
export const usePlantStore = defineStore('plant', () => {
  const samples = ref(new Map())
  const lastUpdateTs = ref(0)
  const sseStatus = ref('idle')

  function applySnapshot(payload) {
    const list = payload?.samples || []
    const next = new Map()
    for (const s of list) {
      next.set(s.sensor_id, s)
    }
    samples.value = next
    lastUpdateTs.value = Date.now()
  }

  function applySample(sample) {
    if (!sample || !sample.sensor_id) return
    const m = new Map(samples.value)
    m.set(sample.sensor_id, sample)
    samples.value = m
    lastUpdateTs.value = Date.now()
  }

  async function loadSnapshot() {
    try {
      const data = await getPlantSnapshot()
      applySnapshot(data)
    } catch (e) {
      console.error('[plant] 加载快照失败', e)
    }
  }

  const samplesList = computed(() => Array.from(samples.value.values()))

  const alarmCount = computed(() => {
    let n = 0
    for (const s of samples.value.values()) {
      if (s.status && s.status !== 'normal') n++
    }
    return n
  })

  return {
    samples,
    samplesList,
    lastUpdateTs,
    sseStatus,
    alarmCount,
    applySnapshot,
    applySample,
    loadSnapshot,
  }
})
