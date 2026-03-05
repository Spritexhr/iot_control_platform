import request from './index'

/** 获取平台配置列表 */
export function getPlatformConfigs(params = {}) {
  return request.get('/platform-configs/', { params })
}

/** 获取单条配置（按 key） */
export function getPlatformConfig(key) {
  return request.get(`/platform-configs/${encodeURIComponent(key)}/`)
}

/** 创建配置（仅管理员） */
export function createPlatformConfig(data) {
  return request.post('/platform-configs/', data)
}

/** 更新配置（仅管理员） */
export function updatePlatformConfig(key, data) {
  return request.put(`/platform-configs/${encodeURIComponent(key)}/`, data)
}

/** 删除配置（仅管理员） */
export function deletePlatformConfig(key) {
  return request.delete(`/platform-configs/${encodeURIComponent(key)}/`)
}
