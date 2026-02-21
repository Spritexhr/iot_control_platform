import request from './index'

// ==================== 传感器类型 ====================
export function getSensorTypes() {
  return request.get('/sensor-types/')
}

export function createSensorType(data) {
  return request.post('/sensor-types/', data)
}

export function updateSensorType(id, data) {
  return request.put(`/sensor-types/${id}/`, data)
}

export function deleteSensorType(id) {
  return request.delete(`/sensor-types/${id}/`)
}

// ==================== 传感器 ====================

/** 获取传感器列表（支持筛选） */
export function getSensors(params = {}) {
  return request.get('/sensors/', { params })
}

/** 获取传感器详情 */
export function getSensor(deviceId) {
  return request.get(`/sensors/${deviceId}/`)
}

/** 创建传感器 */
export function createSensor(data) {
  return request.post('/sensors/', data)
}

/** 更新传感器 */
export function updateSensor(deviceId, data) {
  return request.put(`/sensors/${deviceId}/`, data)
}

/** 删除传感器 */
export function deleteSensor(deviceId) {
  return request.delete(`/sensors/${deviceId}/`)
}

/** 获取传感器历史数据 */
export function getSensorData(deviceId, params = {}) {
  return request.get(`/sensors/${deviceId}/data/`, { params })
}

/** 获取传感器状态记录 */
export function getSensorStatus(deviceId, params = {}) {
  return request.get(`/sensors/${deviceId}/status/`, { params })
}

/** 向传感器发送命令 */
export function sendSensorCommand(deviceId, commandName, params = {}, makeSure = false) {
  return request.post(`/sensors/${deviceId}/command/`, {
    command_name: commandName,
    params,
    make_sure: makeSure,
  })
}
