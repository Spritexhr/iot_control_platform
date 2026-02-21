import request from './index'

// ==================== 设备类型 ====================
export function getDeviceTypes() {
  return request.get('/device-types/')
}

export function createDeviceType(data) {
  return request.post('/device-types/', data)
}

export function updateDeviceType(id, data) {
  return request.put(`/device-types/${id}/`, data)
}

export function deleteDeviceType(id) {
  return request.delete(`/device-types/${id}/`)
}

// ==================== 设备 ====================

/** 获取设备列表（支持筛选） */
export function getDevices(params = {}) {
  return request.get('/devices/', { params })
}

/** 获取设备详情 */
export function getDevice(deviceId) {
  return request.get(`/devices/${deviceId}/`)
}

/** 创建设备 */
export function createDevice(data) {
  return request.post('/devices/', data)
}

/** 更新设备 */
export function updateDevice(deviceId, data) {
  return request.put(`/devices/${deviceId}/`, data)
}

/** 删除设备 */
export function deleteDevice(deviceId) {
  return request.delete(`/devices/${deviceId}/`)
}

/** 获取设备历史数据 */
export function getDeviceData(deviceId, params = {}) {
  return request.get(`/devices/${deviceId}/data/`, { params })
}

/** 向设备发送命令 */
export function sendDeviceCommand(deviceId, commandName, params = {}, makeSure = false) {
  return request.post(`/devices/${deviceId}/command/`, {
    command_name: commandName,
    params,
    make_sure: makeSure,
  })
}
