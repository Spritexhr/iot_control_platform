import request from './index'

// ==================== 控制方案（双位 / PI / PID） ====================

/** 列表（按 project / section 过滤） */
export function listControlSchemes(projectId, sectionId) {
  const params = {}
  if (projectId) params.project = projectId
  if (sectionId) params.section = sectionId
  return request.get('/control-schemes/', { params })
}

export function getControlScheme(id) {
  return request.get(`/control-schemes/${id}/`)
}

export function createControlScheme(payload) {
  return request.post('/control-schemes/', payload)
}

export function updateControlScheme(id, patch) {
  return request.patch(`/control-schemes/${id}/`, patch)
}

export function deleteControlScheme(id) {
  return request.delete(`/control-schemes/${id}/`)
}

/** 启用控制环 */
export function enableControlScheme(id) {
  return request.post(`/control-schemes/${id}/enable/`)
}

/** 停用控制环 */
export function disableControlScheme(id) {
  return request.post(`/control-schemes/${id}/disable/`)
}

/** 手动跑一拍（试一下）。send=false 仅计算不下发 */
export function stepControlScheme(id, send = true) {
  return request.post(`/control-schemes/${id}/step/`, { send })
}

/** 三套控制方案模板（参数 schema + 默认值） */
export function getControlTemplates() {
  return request.get('/control-schemes/templates/')
}
