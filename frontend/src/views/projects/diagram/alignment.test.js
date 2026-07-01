import assert from 'node:assert/strict'
import test from 'node:test'

import { computeNearAlignedPositions } from './alignment.js'

function node(id, x, width = 100) {
  return { id, position: { x, y: 0 }, data: { size: { w: width, h: 80 } } }
}

test('不同宽度节点按连接点中心对齐', () => {
  const nodes = [node('sensor', 100, 100), node('control', 100, 110), node('device', 100, 100)]
  const edges = [
    { source: 'sensor', target: 'control', sourceHandle: 'bottom', targetHandle: 'top' },
    { source: 'control', target: 'device', sourceHandle: 'bottom', targetHandle: 'top' },
  ]
  const changed = computeNearAlignedPositions({ nodes, edges })

  assert.deepEqual(changed.get('sensor'), { x: 101.5, y: 0 })
  assert.deepEqual(changed.get('control'), { x: 96.5, y: 0 })
  assert.deepEqual(changed.get('device'), { x: 101.5, y: 0 })
})

test('对齐结果不受连线数组顺序影响', () => {
  const nodes = [node('a', 100), node('b', 104), node('c', 108)]
  const edges = [
    { source: 'a', target: 'b', sourceHandle: 'bottom', targetHandle: 'top' },
    { source: 'b', target: 'c', sourceHandle: 'bottom', targetHandle: 'top' },
  ]
  const forward = computeNearAlignedPositions({ nodes, edges })
  const reversed = computeNearAlignedPositions({ nodes, edges: [...edges].reverse() })

  assert.deepEqual([...forward], [...reversed])
})

test('超过阈值的偏差不会被自动移动', () => {
  const nodes = [node('a', 0), node('b', 20)]
  const edges = [{ source: 'a', target: 'b', sourceHandle: 'bottom', targetHandle: 'top' }]

  assert.equal(computeNearAlignedPositions({ nodes, edges, threshold: 10 }).size, 0)
})
