import request from './index'

/** 获取 MQTT 连接状态 */
export function getMqttStatus() {
  return request.get('/mqtt/status/')
}

/** 获取仪表盘统计数据 */
export function getDashboardStats() {
  return request.get('/dashboard/stats/')
}
