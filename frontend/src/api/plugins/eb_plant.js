import request from '../index'

const BASE = '/plugins/eb_plant'

/** 取大屏当前已绑定传感器的快照 */
export function getPlantSnapshot() {
  return request.get(`${BASE}/snapshot`)
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
