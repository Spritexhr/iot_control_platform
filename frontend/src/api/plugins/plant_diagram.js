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
 * 拉可绑定的传感器/设备清单（主模型全量）。
 * 返回 { sensors: [{id,name,type,data_fields}], devices: [{id,name,type,commands}] }
 * 位号、单位、阈值等绘制参数由节点属性面板保存到 canvas JSON。
 */
export function getBindableTargets() {
  return request.get(`${BASE}/bindable_targets/`)
}
