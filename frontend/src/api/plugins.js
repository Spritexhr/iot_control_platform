import request from './index'

// ==================== 插件管理 ====================

/** 列出已登记插件 */
export function getPlugins() {
  return request.get('/plugin-manager/')
}

/** 触发文件系统 → DB 同步（仅超级用户） */
export function syncPlugins() {
  return request.post('/plugin-manager/sync/')
}

/** 启用插件（重启后生效） */
export function enablePlugin(name) {
  return request.post(`/plugin-manager/${name}/enable/`)
}

/** 禁用插件（重启后生效） */
export function disablePlugin(name) {
  return request.post(`/plugin-manager/${name}/disable/`)
}

// ==================== data_viz 插件 ====================

/** 列出可视化数据源（sensors + devices） */
export function getDataVizSources() {
  return request.get('/plugins/data_viz/sources/')
}

/**
 * 取时间窗时序数据
 * @param {Object} p
 * @param {'sensor'|'device'} p.kind
 * @param {string} p.sourceId
 * @param {string} [p.start]  ISO datetime
 * @param {string} [p.end]    ISO datetime
 * @param {number} [p.limit]  默认 2000
 */
export function getDataVizSeries({ kind, sourceId, start, end, limit }) {
  return request.get('/plugins/data_viz/series/', {
    params: {
      kind,
      source_id: sourceId,
      start,
      end,
      limit,
    },
  })
}
