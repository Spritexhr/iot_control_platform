import { defineStore } from 'pinia'
import { ref } from 'vue'

import {
  getEBConfig,
  saveEBConfig,
  listBindableSources,
  listSensorBindings,
  createSensorBindings,
  createSensorFieldBinding,
  updateSensorBinding,
  deleteSensorBinding,
  listDeviceBindings,
  createDeviceBindings,
  updateDeviceBinding,
  deleteDeviceBinding,
  listSections,
  createSection,
  updateSection,
  deleteSection,
  reorderSections,
} from '@/api/plugins/eb_plant'

function unwrapList(resp) {
  return Array.isArray(resp) ? resp : resp?.results || []
}

/**
 * EB 大屏配置 store：负责"挑设备/传感器 → 写入插件表"的状态。
 * 与 usePlantStore (实时数据) 解耦。
 */
export const useEBPlantConfigStore = defineStore('ebPlantConfig', () => {
  const config = ref({ view_settings: {} })
  const bindableSensors = ref([])
  const bindableDevices = ref([])
  const sensorBindings = ref([])
  const deviceBindings = ref([])
  const sections = ref([])

  async function loadAll() {
    const [cfg, sources, sBindings, dBindings, secs] = await Promise.all([
      getEBConfig(),
      listBindableSources(),
      listSensorBindings(),
      listDeviceBindings(),
      listSections(),
    ])
    config.value = cfg
    bindableSensors.value = sources.sensors || []
    bindableDevices.value = sources.devices || []
    sensorBindings.value = unwrapList(sBindings)
    deviceBindings.value = unwrapList(dBindings)
    sections.value = unwrapList(secs)
  }

  async function refreshBindings() {
    const [sources, sBindings, dBindings, secs] = await Promise.all([
      listBindableSources(),
      listSensorBindings(),
      listDeviceBindings(),
      listSections(),
    ])
    bindableSensors.value = sources.sensors || []
    bindableDevices.value = sources.devices || []
    sensorBindings.value = unwrapList(sBindings)
    deviceBindings.value = unwrapList(dBindings)
    sections.value = unwrapList(secs)
  }

  // ---------- 工段 ----------
  async function reloadSections() {
    sections.value = unwrapList(await listSections())
  }

  async function addSection(name) {
    const created = await createSection({ name, sort_order: sections.value.length })
    await reloadSections()
    return created
  }

  async function renameSection(id, name) {
    await updateSection(id, { name })
    const idx = sections.value.findIndex((s) => s.id === id)
    if (idx >= 0) sections.value[idx] = { ...sections.value[idx], name }
  }

  async function removeSection(id) {
    await deleteSection(id)
    await reloadSections()
    // 绑定的 section 在后端被 SET_NULL，刷新绑定让 UI 同步
    await refreshBindings()
  }

  async function saveSectionOrder(orderedIds) {
    await reorderSections(orderedIds)
    await reloadSections()
  }

  async function importSensors(ids) {
    if (!ids.length) return { created: 0 }
    const resp = await createSensorBindings(ids)
    await refreshBindings()
    return { created: Array.isArray(resp?.created) ? resp.created.length : 0 }
  }

  async function addSensorFieldBinding(payload) {
    await createSensorFieldBinding(payload)
    await refreshBindings()
  }

  async function importDevices(ids) {
    if (!ids.length) return
    await createDeviceBindings(ids)
    await refreshBindings()
  }

  async function patchSensorBinding(id, patch) {
    const updated = await updateSensorBinding(id, patch)
    const idx = sensorBindings.value.findIndex((b) => b.id === id)
    if (idx >= 0) sensorBindings.value[idx] = updated
  }

  async function patchDeviceBinding(id, patch) {
    const updated = await updateDeviceBinding(id, patch)
    const idx = deviceBindings.value.findIndex((b) => b.id === id)
    if (idx >= 0) deviceBindings.value[idx] = updated
  }

  async function removeSensorBinding(id) {
    await deleteSensorBinding(id)
    await refreshBindings()
  }

  async function removeDeviceBinding(id) {
    await deleteDeviceBinding(id)
    await refreshBindings()
  }

  async function saveViewSettings(settings) {
    const updated = await saveEBConfig({ view_settings: settings })
    config.value = updated
  }

  return {
    config,
    bindableSensors,
    bindableDevices,
    sensorBindings,
    deviceBindings,
    sections,
    loadAll,
    refreshBindings,
    importSensors,
    addSensorFieldBinding,
    importDevices,
    patchSensorBinding,
    patchDeviceBinding,
    removeSensorBinding,
    removeDeviceBinding,
    saveViewSettings,
    reloadSections,
    addSection,
    renameSection,
    removeSection,
    saveSectionOrder,
  }
})
