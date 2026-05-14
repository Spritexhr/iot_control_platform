import request from '../index'

/**
 * 获取 EB 装置当前所有点位快照。
 */
export function getPlantSnapshot() {
  return request.get('/plugins/eb_plant/snapshot')
}

/**
 * 下发扰动场景给模拟器。
 * @param {string} scenario  none / ethylene_overfeed / cooling_failure / deb_snowball
 */
export function injectDisturbance(scenario) {
  return request.post('/plugins/eb_plant/disturbance', { scenario })
}

/**
 * 构造 SSE 流的完整 URL（由 useSSE 直接交给 EventSource 用）。
 * 注意:EventSource 无法附带 Authorization header,
 * SSE 端点目前用 AllowAny 权限。生产环境可换为 token 查询参数 + 自定义鉴权。
 */
export function buildPlantStreamUrl() {
  return '/api/plugins/eb_plant/stream'
}
