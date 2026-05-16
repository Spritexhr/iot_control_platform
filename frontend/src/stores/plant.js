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

  /**
   * 按 P&ID 节点 binding 取实时样本。
   * - 完整 point_id (e.g. "S001::temperature") → 直接命中
   * - 纯 sensor_id (e.g. "S001") → 直接命中（单字段传感器），或回落到 sensor_id::* 中的第一条
   *   （兼容多字段传感器在老画板里 binding 用纯 sensor_id 的情况）
   */
  function findByBinding(id) {
    if (!id) return null
    const map = samples.value
    if (map.has(id)) return map.get(id)
    const prefix = `${id}::`
    for (const s of map.values()) {
      if (s.sensor_id === id || (typeof s.sensor_id === 'string' && s.sensor_id.startsWith(prefix))) {
        return s
      }
    }
    return null
  }

  return {
    samples,
    samplesList,
    lastUpdateTs,
    sseStatus,
    alarmCount,
    applySnapshot,
    applySample,
    loadSnapshot,
    findByBinding,
  }
})
