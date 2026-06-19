import request from './index'

const BASE = '/projects'

// ==================== 项目 ====================
export function listProjects() {
  return request.get(`${BASE}/`)
}
export function getProject(id) {
  return request.get(`${BASE}/${id}/`)
}
export function createProject(payload) {
  return request.post(`${BASE}/`, payload)
}
export function updateProject(id, patch) {
  return request.patch(`${BASE}/${id}/`, patch)
}
export function deleteProject(id) {
  return request.delete(`${BASE}/${id}/`)
}

// ==================== 聚合（实时） ====================
/** 展示骨架：有序分区，每段挂传感器/设备成员（含静态元信息） */
export function getProjectLayout(id) {
  return request.get(`${BASE}/${id}/layout/`)
}
/** 当前实时快照（传感器最新值 + 设备状态，现查 DB） */
export function getProjectSnapshot(id) {
  return request.get(`${BASE}/${id}/snapshot/`)
}
/** 可导入到本项目的全量传感器/设备（含已占用判断） */
export function listProjectBindableSources(id) {
  return request.get(`${BASE}/${id}/bindable_sources/`)
}
/** 项目实时 WebSocket 路径（不含 host）。useWebSocket(buildWsUrl(buildProjectWsPath(id)), ...) 用 */
export function buildProjectWsPath(id) {
  return `/ws/projects/${id}/`
}

// ==================== 分区 ====================
export function listSections(projectId) {
  return request.get('/project_sections/', { params: { project: projectId } })
}
export function createSection(payload) {
  return request.post('/project_sections/', payload)
}
export function updateSection(id, patch) {
  return request.patch(`/project_sections/${id}/`, patch)
}
export function deleteSection(id) {
  return request.delete(`/project_sections/${id}/`)
}
/** 按 section id 数组批量写显示顺序 */
export function reorderSections(order) {
  return request.post('/project_sections/reorder/', { order })
}

// ==================== 传感器成员 ====================
export function listSensorMembers(projectId) {
  return request.get('/project_sensor_members/', { params: { project: projectId } })
}
/** 批量导入：按各 sensor 的 data_fields 自动拆分多字段 */
export function createSensorMembers(projectId, sensorIds) {
  return request.post('/project_sensor_members/', { project: projectId, sensor_ids: sensorIds })
}
/** 为某传感器追加一条不同 data_key 的成员。payload: { project, sensor, data_key, tag?, ... } */
export function createSensorFieldMember(payload) {
  return request.post('/project_sensor_members/', payload)
}
export function updateSensorMember(id, patch) {
  return request.patch(`/project_sensor_members/${id}/`, patch)
}
export function deleteSensorMember(id) {
  return request.delete(`/project_sensor_members/${id}/`)
}

// ==================== 设备成员 ====================
export function listDeviceMembers(projectId) {
  return request.get('/project_device_members/', { params: { project: projectId } })
}
export function createDeviceMembers(projectId, deviceIds) {
  return request.post('/project_device_members/', { project: projectId, device_ids: deviceIds })
}
export function updateDeviceMember(id, patch) {
  return request.patch(`/project_device_members/${id}/`, patch)
}
export function deleteDeviceMember(id) {
  return request.delete(`/project_device_members/${id}/`)
}

// ==================== 视图 ====================
export function listViews(projectId) {
  return request.get('/project_views/', { params: { project: projectId } })
}
export function createView(payload) {
  return request.post('/project_views/', payload)
}
export function updateView(id, patch) {
  return request.patch(`/project_views/${id}/`, patch)
}
export function deleteView(id) {
  return request.delete(`/project_views/${id}/`)
}
