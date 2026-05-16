import request from '../index'

/**
 * 工厂 P&ID 画板 API 客户端。
 * 后端路径：/api/plugins/plant_diagram/
 */

const BASE = '/plugins/plant_diagram'

/** 列出某 plant 下的所有画板（不含 canvas 数据） */
export function listDiagrams(plantCode) {
  const params = plantCode ? { plant_code: plantCode } : {}
  return request.get(`${BASE}/`, { params })
}

/** 取一张画板的完整数据（含 canvas） */
export function getDiagram(id) {
  return request.get(`${BASE}/${id}/`)
}

/** 新建画板 */
export function createDiagram(payload) {
  return request.post(`${BASE}/`, payload)
}

/** 更新（整体替换 canvas） */
export function updateDiagram(id, payload) {
  return request.put(`${BASE}/${id}/`, payload)
}

/** 部分更新 */
export function patchDiagram(id, payload) {
  return request.patch(`${BASE}/${id}/`, payload)
}

/** 删除 */
export function deleteDiagram(id) {
  return request.delete(`${BASE}/${id}/`)
}

/**
 * 拉可绑定的传感器/设备清单。
 * 装置插件接管"哪些点位被纳入大屏"，本接口按 plantCode 返回该装置已绑定的点位
 * （EB 装置走 EBPlantSensorBinding/EBPlantDeviceBinding），与大屏的点位集合一致。
 *
 * 返回 {
 *   sensors: [{ id (point_id), name, tag, data_key, unit, area, type, hi_threshold, lo_threshold, severity }],
 *   devices: [{ id, name, tag, area, type, commands }],
 * }
 */
export function getBindableTargets(plantCode) {
  const params = plantCode ? { plant_code: plantCode } : {}
  return request.get(`${BASE}/bindable_targets/`, { params })
}
