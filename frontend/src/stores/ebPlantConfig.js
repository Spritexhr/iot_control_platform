import { defineStore } from 'pinia'
import { ref } from 'vue'

import {
  getEBConfig,
  saveEBConfig,
  listBindableSources,
  listSensorBindings,
  createSensorBindings,
  updateSensorBinding,
  deleteSensorBinding,
  listDeviceBindings,
  createDeviceBindings,
  updateDeviceBinding,
  deleteDeviceBinding,
} from '@/api/plugins/eb_plant'

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

  async function loadAll() {
    const [cfg, sources, sBindings, dBindings] = await Promise.all([
      getEBConfig(),
      listBindableSources(),
      listSensorBindings(),
      listDeviceBindings(),
    ])
    config.value = cfg
    bindableSensors.value = sources.sensors || []
    bindableDevices.value = sources.devices || []
    sensorBindings.value = Array.isArray(sBindings) ? sBindings : sBindings.results || []
    deviceBindings.value = Array.isArray(dBindings) ? dBindings : dBindings.results || []
  }

  async function refreshBindings() {
    const [sources, sBindings, dBindings] = await Promise.all([
      listBindableSources(),
      listSensorBindings(),
      listDeviceBindings(),
    ])
    bindableSensors.value = sources.sensors || []
    bindableDevices.value = sources.devices || []
    sensorBindings.value = Array.isArray(sBindings) ? sBindings : sBindings.results || []
    deviceBindings.value = Array.isArray(dBindings) ? dBindings : dBindings.results || []
  }

  async function importSensors(ids) {
    if (!ids.length) return
    await createSensorBindings(ids)
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
    loadAll,
    refreshBindings,
    importSensors,
    importDevices,
    patchSensorBinding,
    patchDeviceBinding,
    removeSensorBinding,
    removeDeviceBinding,
    saveViewSettings,
  }
})
