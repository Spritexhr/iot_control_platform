import request from './index'

/**
 * 获取装置当前所有点位快照。
 * @param {string} plantCode 例如 'EB'
 */
export function getPlantSnapshot(plantCode) {
  return request.get(`/realtime/plant/${plantCode}/snapshot`)
}

/**
 * 下发扰动场景给模拟器。
 * @param {string} scenario  none / ethylene_overfeed / cooling_failure / deb_snowball
 */
export function injectDisturbance(scenario) {
  return request.post('/realtime/plant/EB/disturbance', { scenario })
}

/**
 * 构造 SSE 流的完整 URL(由 useSSE 直接交给 EventSource 用)。
 * 注意:EventSource 无法附带 Authorization header,
 * SSE 端点目前用 AllowAny 权限。生产环境可换为 token 查询参数 + 自定义鉴权。
 */
export function buildPlantStreamUrl(plantCode) {
  // 直接拼后端 API,经 Vite 代理或同源访问
  return `/api/realtime/plant/${plantCode}/stream`
}
