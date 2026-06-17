import request from '../index'

const BASE = '/plugins/eb_plant'

/** 取大屏当前实时快照（传感器最新值 + 设备最新状态） */
export function getPlantSnapshot() {
  return request.get(`${BASE}/snapshot`)
}

/** 取大屏骨架：有序工段，每段挂传感器/设备绑定（含静态元信息） */
export function getPlantLayout() {
  return request.get(`${BASE}/layout`)
}

/**
 * EB 大屏 WebSocket 路径（不含 host）。
 * useWebSocket(buildWsUrl(buildPlantWsPath()), ...) 用。
 */
export function buildPlantWsPath() {
  return '/ws/plugins/eb_plant/'
}

// ---------- 视图配置 ----------
export function getEBConfig() {
  return request.get(`${BASE}/config`)
}

export function saveEBConfig(payload) {
  return request.put(`${BASE}/config`, payload)
}

// ---------- 主模型来源 ----------
export function listBindableSources() {
  return request.get(`${BASE}/bindable_sources`)
}

// ---------- 传感器绑定 ----------
export function listSensorBindings() {
  return request.get(`${BASE}/sensor_bindings/`)
}

export function createSensorBindings(sensorIds) {
  return request.post(`${BASE}/sensor_bindings/`, { sensor_ids: sensorIds })
}

/** 为某个 sensor 追加一条不同 data_key 的 binding。payload: { sensor, data_key, tag?, area?, severity? } */
export function createSensorFieldBinding(payload) {
  return request.post(`${BASE}/sensor_bindings/`, payload)
}

export function updateSensorBinding(id, patch) {
  return request.patch(`${BASE}/sensor_bindings/${id}/`, patch)
}

export function deleteSensorBinding(id) {
  return request.delete(`${BASE}/sensor_bindings/${id}/`)
}

// ---------- 设备绑定 ----------
export function listDeviceBindings() {
  return request.get(`${BASE}/device_bindings/`)
}

export function createDeviceBindings(deviceIds) {
  return request.post(`${BASE}/device_bindings/`, { device_ids: deviceIds })
}

export function updateDeviceBinding(id, patch) {
  return request.patch(`${BASE}/device_bindings/${id}/`, patch)
}

export function deleteDeviceBinding(id) {
  return request.delete(`${BASE}/device_bindings/${id}/`)
}

// ---------- 工段（栏目） ----------
export function listSections() {
  return request.get(`${BASE}/sections/`)
}

export function createSection(payload) {
  return request.post(`${BASE}/sections/`, payload)
}

export function updateSection(id, patch) {
  return request.patch(`${BASE}/sections/${id}/`, patch)
}

export function deleteSection(id) {
  return request.delete(`${BASE}/sections/${id}/`)
}

/** 按 section id 数组批量写显示顺序 */
export function reorderSections(order) {
  return request.post(`${BASE}/sections/reorder/`, { order })
}
