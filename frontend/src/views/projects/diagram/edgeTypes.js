import { markRaw } from 'vue'

import PidEdge from './PidEdge.vue'

export const DEFAULT_EDGE_KIND = 'process'
export const EDGE_KINDS = new Set(['process', 'utility', 'signal'])

/**
 * 连线持久化只保留真正参与渲染的字段。
 * 运行时也忽略旧画布中的 medium；数据库迁移会统一清除历史残留。
 */
export function normalizeEdgeData(data) {
  return {
    label: typeof data?.label === 'string' ? data.label : '',
    kind: EDGE_KINDS.has(data?.kind) ? data.kind : DEFAULT_EDGE_KIND,
  }
}

export function getPidEdgeStyle(kind, selected = false) {
  const selectedWidth = selected ? 0.5 : 0
  switch (kind) {
    case 'utility':
      return {
        stroke: '#287aa9',
        strokeWidth: 1.8 + selectedWidth,
        strokeDasharray: '9 5',
        strokeLinecap: 'round',
      }
    case 'signal':
      return {
        stroke: '#b06b35',
        strokeWidth: 1.3 + selectedWidth,
        strokeDasharray: '3 5',
        strokeLinecap: 'round',
      }
    case 'process':
    default:
      return {
        stroke: '#27323a',
        strokeWidth: 2.5 + selectedWidth,
        strokeLinecap: 'round',
      }
  }
}

export function buildEdgeTypes() {
  return { pid: markRaw(PidEdge) }
}
