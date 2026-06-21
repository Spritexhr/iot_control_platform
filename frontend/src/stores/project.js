import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { getProjectLayout, getProjectSnapshot } from '@/api/projects'

/**
 * 项目（场景）实时数据 store（升格自 stores/plant.js）。
 * 一个 ProjectWorkspace 实例对应一个项目；切换项目时调 reset() 再 load。
 *
 * - samples: Map<point_id, sample>，sample 字段见后端 PointSample.to_dict()
 * - devices: Map<device_id, state>
 * - layout:  按分区分组的骨架（含每段传感器/设备成员静态元信息）
 */
export const useProjectStore = defineStore('project', () => {
  const currentProjectId = ref(null)
  const samples = ref(new Map())
  const devices = ref(new Map())
  const layout = ref({ sections: [] })
  const lastUpdateTs = ref(0)
  const wsStatus = ref('idle')

  function reset(projectId = null) {
    currentProjectId.value = projectId
    samples.value = new Map()
    devices.value = new Map()
    layout.value = { sections: [] }
    lastUpdateTs.value = 0
  }

  function applySnapshot(payload) {
    const next = new Map()
    for (const s of payload?.samples || []) {
      if (s && s.sensor_id) next.set(s.sensor_id, s)
    }
    samples.value = next

    const dNext = new Map()
    for (const d of payload?.devices || []) {
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

  async function loadLayout(projectId) {
    try {
      applyLayout(await getProjectLayout(projectId))
    } catch (e) {
      console.error('[project] 加载布局失败', e)
    }
  }

  async function loadSnapshot(projectId) {
    try {
      applySnapshot(await getProjectSnapshot(projectId))
    } catch (e) {
      console.error('[project] 加载快照失败', e)
    }
  }

  const alarmCount = computed(() => {
    let n = 0
    for (const s of samples.value.values()) {
      if (s.status && s.status !== 'normal') n++
    }
    return n
  })

  /** 按节点 binding 取实时样本，规则同 EB（兼容纯 sensor_id 回落到 sensor_id::*） */
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
    return deviceId ? devices.value.get(deviceId) || null : null
  }

  /** 取某房间(分区)对象（含其传感器/设备成员） */
  function getSection(sectionId) {
    const sid = Number(sectionId)
    return (layout.value?.sections || []).find((s) => s.id === sid) || null
  }

  /** 取某房间的成员 { sensors, devices }，供视图按房间过滤候选数据源 */
  function sectionMembers(sectionId) {
    const sec = getSection(sectionId)
    return { sensors: sec?.sensors || [], devices: sec?.devices || [] }
  }

  return {
    currentProjectId,
    samples,
    devices,
    layout,
    lastUpdateTs,
    wsStatus,
    alarmCount,
    reset,
    applySnapshot,
    applySample,
    applyDeviceStatus,
    applyLayout,
    loadLayout,
    loadSnapshot,
    findByBinding,
    findDevice,
    getSection,
    sectionMembers,
  }
})
