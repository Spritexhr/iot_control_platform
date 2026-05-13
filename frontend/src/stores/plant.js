import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { getPlantSnapshot, injectDisturbance } from '@/api/realtime'

/**
 * 装置实时数据 store。
 * - samples: Map<sensor_id, sample>,sample 字段见后端 PointSample.to_dict()
 * - SSE 推 sample 事件 → applySample 更新单点
 * - 初始化或重连后用 applySnapshot 全量刷新
 */
export const usePlantStore = defineStore('plant', () => {
  const plantCode = ref('EB')
  const samples = ref(new Map())
  const lastUpdateTs = ref(0)
  const sseStatus = ref('idle')
  const currentScenario = ref('none')

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
    // Vue 3 的 reactivity 对 Map 是浅响应,直接 set 即可触发 getter 中的依赖
    const m = new Map(samples.value)
    m.set(sample.sensor_id, sample)
    samples.value = m
    lastUpdateTs.value = Date.now()
  }

  async function loadSnapshot() {
    try {
      const data = await getPlantSnapshot(plantCode.value)
      applySnapshot(data)
    } catch (e) {
      console.error('[plant] 加载快照失败', e)
    }
  }

  async function setDisturbance(scenario) {
    try {
      await injectDisturbance(scenario)
      currentScenario.value = scenario
      return true
    } catch (e) {
      console.error('[plant] 下发扰动失败', e)
      return false
    }
  }

  // ---------- getters ----------
  const samplesList = computed(() => Array.from(samples.value.values()))

  const alarmCount = computed(() => {
    let n = 0
    for (const s of samples.value.values()) {
      if (s.status && s.status !== 'normal') n++
    }
    return n
  })

  return {
    // state
    plantCode,
    samples,
    samplesList,
    lastUpdateTs,
    sseStatus,
    currentScenario,
    alarmCount,
    // actions
    applySnapshot,
    applySample,
    loadSnapshot,
    setDisturbance,
  }
})
