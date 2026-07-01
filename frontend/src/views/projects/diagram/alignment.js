const VERTICAL_HANDLES = new Set(['top', 'bottom'])
const HORIZONTAL_HANDLES = new Set(['left', 'right'])

function handleCenter(node, handleId) {
  const position = node?.position || { x: 0, y: 0 }
  const width = Number(node?.data?.size?.w || node?.dimensions?.width || 0)
  const height = Number(node?.data?.size?.h || node?.dimensions?.height || 0)
  switch (handleId) {
    case 'left':   return { x: position.x, y: position.y + height / 2 }
    case 'right':  return { x: position.x + width, y: position.y + height / 2 }
    case 'top':    return { x: position.x + width / 2, y: position.y }
    case 'bottom': return { x: position.x + width / 2, y: position.y + height }
    default:       return null
  }
}

function buildAlignmentGroups(nodes, edges, axis, threshold) {
  const byId = new Map(nodes.map((node) => [node.id, node]))
  const parent = new Map()
  const find = (id) => {
    const current = parent.get(id)
    if (current === id) return id
    const root = find(current)
    parent.set(id, root)
    return root
  }
  const union = (left, right) => {
    if (!parent.has(left)) parent.set(left, left)
    if (!parent.has(right)) parent.set(right, right)
    const leftRoot = find(left)
    const rightRoot = find(right)
    if (leftRoot === rightRoot) return
    const [root, child] = String(leftRoot) < String(rightRoot)
      ? [leftRoot, rightRoot]
      : [rightRoot, leftRoot]
    parent.set(child, root)
  }

  for (const edge of edges) {
    const sourceNode = byId.get(edge.source)
    const targetNode = byId.get(edge.target)
    if (!sourceNode || !targetNode) continue
    const sourceHandle = edge.sourceHandle || 'right'
    const targetHandle = edge.targetHandle || 'left'
    const compatible = axis === 'x'
      ? VERTICAL_HANDLES.has(sourceHandle) && VERTICAL_HANDLES.has(targetHandle)
      : HORIZONTAL_HANDLES.has(sourceHandle) && HORIZONTAL_HANDLES.has(targetHandle)
    if (!compatible) continue
    const sourcePoint = handleCenter(sourceNode, sourceHandle)
    const targetPoint = handleCenter(targetNode, targetHandle)
    if (!sourcePoint || !targetPoint) continue
    if (Math.abs(sourcePoint[axis] - targetPoint[axis]) <= threshold) {
      union(sourceNode.id, targetNode.id)
    }
  }

  const groups = new Map()
  for (const nodeId of parent.keys()) {
    const root = find(nodeId)
    if (!groups.has(root)) groups.set(root, [])
    groups.get(root).push(nodeId)
  }
  return [...groups.values()].filter((group) => group.length > 1)
}

/**
 * 以连接点中心为约束求解近对齐节点。
 * 返回 Map<nodeId, position>，不修改入参，且结果与 edges 顺序无关。
 */
export function computeNearAlignedPositions({
  nodes = [], edges = [], threshold = 10, anchorNodeId = null, scopeNodeId = null,
}) {
  const original = new Map(nodes.map((node) => [node.id, node.position]))
  const working = nodes.map((node) => ({ ...node, position: { ...node.position } }))
  const byId = new Map(working.map((node) => [node.id, node]))

  for (const axis of ['x', 'y']) {
    for (const group of buildAlignmentGroups(working, edges, axis, threshold)) {
      if (scopeNodeId && !group.includes(scopeNodeId)) continue
      const groupNodes = group.map((id) => byId.get(id)).filter(Boolean)
      const centers = groupNodes.map((node) => handleCenter(node, axis === 'x' ? 'top' : 'left')[axis])
      const anchorIndex = anchorNodeId ? groupNodes.findIndex((node) => node.id === anchorNodeId) : -1
      const rawTarget = anchorIndex >= 0
        ? centers[anchorIndex]
        : centers.reduce((sum, value) => sum + value, 0) / centers.length
      const targetCenter = Math.round(rawTarget * 2) / 2

      groupNodes.forEach((node, index) => {
        node.position[axis] += targetCenter - centers[index]
      })
    }
  }

  const changed = new Map()
  for (const node of working) {
    const before = original.get(node.id)
    if (Math.abs(node.position.x - before.x) >= 0.01 || Math.abs(node.position.y - before.y) >= 0.01) {
      changed.set(node.id, node.position)
    }
  }
  return changed
}
