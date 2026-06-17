import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { getPlantSnapshot, getPlantLayout } from '@/api/plugins/eb_plant'

/**
 * EB 装置实时数据 store。
 * - samples: Map<sensor_id, sample>，sample 字段见后端 PointSample.to_dict()
 * - devices: Map<device_id, state>，设备最新状态（status dict / is_online / last_seen）
 * - layout:  按工段分组的骨架（含每段的传感器/设备绑定静态元信息）
 *
 * 数据流：
 * - 骨架 applyLayout 拉一次（配置变更后重拉）
 * - 实时值首帧 applySnapshot（HTTP + WS 建连各发一次，含 samples + devices）
 * - 增量：applySample（传感器单点）/ applyDeviceStatus（设备单点）
 */
export const usePlantStore = defineStore('plant', () => {
  const samples = ref(new Map())
  const devices = ref(new Map())
  const layout = ref({ sections: [] })
  const lastUpdateTs = ref(0)
  const sseStatus = ref('idle')

  function applySnapshot(payload) {
    const list = payload?.samples || []
    const next = new Map()
    for (const s of list) {
      next.set(s.sensor_id, s)
    }
    samples.value = next

    const dList = payload?.devices || []
    const dNext = new Map()
    for (const d of dList) {
      if (d && d.device_id) dNext.set(d.device_id, d)
    }
    devices.value = dNext

    lastUpdateTs.value = Date.now()
  }

  function applySample(sample) {
    if (!sample || !sample.sensor_id) return
    const m = new Map(samples.value)
    m.set(sample.sensor_id, sample)
    samples.value = m
    lastUpdateTs.value = Date.now()
  }

  /**
   * 设备状态增量。WS device.status payload 字段：
   * {device_id, event, status, timestamp, received_at, is_online, last_seen}
   * 合并到已有 state（保留 snapshot/layout 来的 name/tag），ts 用 timestamp。
   */
  function applyDeviceStatus(payload) {
    if (!payload || !payload.device_id) return
    const m = new Map(devices.value)
    const prev = m.get(payload.device_id) || {}
    m.set(payload.device_id, {
      ...prev,
      device_id: payload.device_id,
      status: payload.status ?? prev.status ?? {},
      event: payload.event ?? prev.event ?? '',
      is_online: payload.is_online,
      last_seen: payload.last_seen ?? prev.last_seen ?? null,
      ts: payload.timestamp ?? prev.ts ?? null,
    })
    devices.value = m
    lastUpdateTs.value = Date.now()
  }

  function applyLayout(payload) {
    layout.value = payload && Array.isArray(payload.sections) ? payload : { sections: [] }
  }

  async function loadSnapshot() {
    try {
      const data = await getPlantSnapshot()
      applySnapshot(data)
    } catch (e) {
      console.error('[plant] 加载快照失败', e)
    }
  }

  async function loadLayout() {
    try {
      const data = await getPlantLayout()
      applyLayout(data)
    } catch (e) {
      console.error('[plant] 加载布局失败', e)
    }
  }

  const samplesList = computed(() => Array.from(samples.value.values()))
  const devicesList = computed(() => Array.from(devices.value.values()))

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

  function findDevice(deviceId) {
    if (!deviceId) return null
    return devices.value.get(deviceId) || null
  }

  return {
    samples,
    samplesList,
    devices,
    devicesList,
    layout,
    lastUpdateTs,
    sseStatus,
    alarmCount,
    applySnapshot,
    applySample,
    applyDeviceStatus,
    applyLayout,
    loadSnapshot,
    loadLayout,
    findByBinding,
    findDevice,
  }
})
