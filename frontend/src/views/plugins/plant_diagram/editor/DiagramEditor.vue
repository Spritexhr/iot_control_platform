<template>
  <div class="editor">
    <ToolboxPanel />

    <div class="editor__canvas-wrap" @drop="onDrop" @dragover.prevent>
      <VueFlow
        v-model:nodes="nodes"
        v-model:edges="edges"
        :default-viewport="defaultViewport"
        :snap-to-grid="true"
        :snap-grid="[10, 10]"
        :delete-key-code="['Backspace', 'Delete']"
        :connection-mode="ConnectionMode.Loose"
        fit-view-on-init
        @nodes-change="onChange"
        @edges-change="onChange"
        @connect="onConnect"
        @node-click="onNodeClick"
        @edge-click="onEdgeClick"
        @pane-click="clearSelection"
        @viewport-change="onViewportChange"
      >
        <Background pattern-color="#d8d2c4" :gap="16" />
        <Controls />

        <template #node-instrument="nodeProps">
          <InstrumentNode v-bind="nodeProps" />
        </template>
        <template #node-vessel="nodeProps">
          <VesselNode v-bind="nodeProps" />
        </template>
        <template #node-column="nodeProps">
          <SimpleSymbolNode v-bind="nodeProps" kind="column" />
        </template>
        <template #node-valve="nodeProps">
          <SimpleSymbolNode v-bind="nodeProps" kind="valve" />
        </template>
        <template #node-pump="nodeProps">
          <SimpleSymbolNode v-bind="nodeProps" kind="pump" />
        </template>
        <template #node-heat_exchanger="nodeProps">
          <SimpleSymbolNode v-bind="nodeProps" kind="heat_exchanger" />
        </template>
        <template #node-mixer="nodeProps">
          <SimpleSymbolNode v-bind="nodeProps" kind="mixer" />
        </template>
        <template #node-filter="nodeProps">
          <SimpleSymbolNode v-bind="nodeProps" kind="filter" />
        </template>
        <template #node-label="nodeProps">
          <SimpleSymbolNode v-bind="nodeProps" kind="label" />
        </template>
      </VueFlow>
    </div>

    <PropertiesPanel
      :selection="selection"
      :targets="targets"
      @update-node="applyNodePatch"
      @update-edge="applyEdgePatch"
      @delete-node="removeNode"
      @delete-edge="removeEdge"
    />
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ConnectionMode, VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'

import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'

import ToolboxPanel from './ToolboxPanel.vue'
import PropertiesPanel from './PropertiesPanel.vue'
import InstrumentNode from './nodes/InstrumentNode.vue'
import VesselNode from './nodes/VesselNode.vue'
import SimpleSymbolNode from './nodes/SimpleSymbolNode.vue'

const props = defineProps({
  diagram: { type: Object, required: true },
  targets: { type: Object, default: () => ({ sensors: [], devices: [] }) },
})
const emit = defineEmits(['change'])

const { project, screenToFlowCoordinate } = useVueFlow()

// ============ canvas <-> Vue Flow 互转 ============
// canvas.nodes 形如：{ id, type, position, size, binding, data }
// Vue Flow 节点：{ id, type, position, data:{...原 data, binding, size} }
function canvasToFlow(canvas) {
  const nodes = (canvas?.nodes || []).map((n) => ({
    id: n.id,
    type: n.type,
    position: { x: n.position?.x || 0, y: n.position?.y || 0 },
    data: { ...(n.data || {}), binding: n.binding || { kind: 'none', id: '' }, size: n.size },
  }))
  const edges = (canvas?.edges || []).map((e) => ({
    id: e.id,
    source: e.source,
    sourceHandle: e.sourcePort || e.sourceHandle || 'right',
    target: e.target,
    targetHandle: e.targetPort || e.targetHandle || 'left',
    type: 'smoothstep',
    data: { label: e.data?.label || '', kind: e.data?.kind || 'process', medium: e.data?.medium || '' },
    label: e.data?.label || '',
    style: edgeStyle(e.data?.kind),
    markerEnd: 'arrowclosed',
  }))
  return { nodes, edges }
}

function flowToCanvas() {
  return {
    version: 1,
    viewport: viewport.value,
    nodes: nodes.value.map((n) => ({
      id: n.id,
      type: n.type,
      position: { x: Math.round(n.position.x), y: Math.round(n.position.y) },
      size: n.data?.size,
      binding: n.data?.binding || { kind: 'none', id: '' },
      data: stripBindingAndSize(n.data),
    })),
    edges: edges.value.map((e) => ({
      id: e.id,
      source: e.source, sourcePort: e.sourceHandle || 'right',
      target: e.target, targetPort: e.targetHandle || 'left',
      type: 'process_line',
      data: e.data || {},
    })),
  }
}

function stripBindingAndSize(data) {
  if (!data) return {}
  const { binding, size, ...rest } = data
  return rest
}

function edgeStyle(kind) {
  switch (kind) {
    case 'utility': return { stroke: '#2a2a2a', strokeWidth: 1.2, strokeDasharray: '6 4' }
    case 'signal':  return { stroke: '#888',    strokeWidth: 1,   strokeDasharray: '2 3' }
    case 'process':
    default:        return { stroke: '#2a2a2a', strokeWidth: 2 }
  }
}

// ============ state ============
const initial = canvasToFlow(props.diagram?.canvas)
const nodes = ref(initial.nodes)
const edges = ref(initial.edges)
const viewport = ref(props.diagram?.canvas?.viewport || { x: 0, y: 0, zoom: 1 })
const defaultViewport = viewport.value

const selection = ref(null)        // { kind: 'node'|'edge', payload }

// 当父组件换了 diagram（例如从列表跳转过来），重置画布
watch(() => props.diagram?.id, () => {
  const init = canvasToFlow(props.diagram?.canvas)
  nodes.value = init.nodes
  edges.value = init.edges
  viewport.value = props.diagram?.canvas?.viewport || { x: 0, y: 0, zoom: 1 }
  selection.value = null
})

// ============ 事件 ============
function emitCanvas() {
  emit('change', flowToCanvas())
}
function onChange() {
  emitCanvas()
}
function onViewportChange(v) {
  viewport.value = v
  emitCanvas()
}

function onConnect(connection) {
  const id = `e_${Date.now()}_${Math.floor(Math.random() * 1000)}`
  edges.value.push({
    id,
    source: connection.source,
    sourceHandle: connection.sourceHandle || 'right',
    target: connection.target,
    targetHandle: connection.targetHandle || 'left',
    type: 'smoothstep',
    data: { label: '', kind: 'process', medium: '' },
    style: edgeStyle('process'),
    markerEnd: 'arrowclosed',
  })
  emitCanvas()
}

function onNodeClick({ node }) {
  selection.value = { kind: 'node', payload: node }
}
function onEdgeClick({ edge }) {
  selection.value = { kind: 'edge', payload: edge }
}
function clearSelection() {
  selection.value = null
}

function applyNodePatch({ id, patch }) {
  const idx = nodes.value.findIndex((n) => n.id === id)
  if (idx < 0) return
  const old = nodes.value[idx]
  nodes.value.splice(idx, 1, {
    ...old,
    position: patch.position ?? old.position,
    data: { ...old.data, ...patch.data },
  })
  if (selection.value?.kind === 'node' && selection.value.payload.id === id) {
    selection.value = { kind: 'node', payload: nodes.value[idx] }
  }
  emitCanvas()
}

function applyEdgePatch({ id, patch }) {
  const idx = edges.value.findIndex((e) => e.id === id)
  if (idx < 0) return
  const old = edges.value[idx]
  const data = { ...old.data, ...patch.data }
  edges.value.splice(idx, 1, {
    ...old,
    data,
    label: data.label || '',
    style: edgeStyle(data.kind),
  })
  if (selection.value?.kind === 'edge' && selection.value.payload.id === id) {
    selection.value = { kind: 'edge', payload: edges.value[idx] }
  }
  emitCanvas()
}

function removeNode(id) {
  nodes.value = nodes.value.filter((n) => n.id !== id)
  edges.value = edges.value.filter((e) => e.source !== id && e.target !== id)
  selection.value = null
  emitCanvas()
}
function removeEdge(id) {
  edges.value = edges.value.filter((e) => e.id !== id)
  selection.value = null
  emitCanvas()
}

// 从工具箱拖入新节点
function onDrop(event) {
  event.preventDefault()
  const raw = event.dataTransfer?.getData('application/x-plant-node')
  if (!raw) return
  let payload
  try { payload = JSON.parse(raw) } catch { return }

  // 屏幕坐标 → 画布坐标
  const pos = screenToFlowCoordinate
    ? screenToFlowCoordinate({ x: event.clientX, y: event.clientY })
    : project({ x: event.clientX, y: event.clientY })

  const id = `n_${payload.type}_${Date.now()}_${Math.floor(Math.random() * 1000)}`
  nodes.value.push({
    id,
    type: payload.type,
    position: { x: Math.round(pos.x), y: Math.round(pos.y) },
    data: {
      ...(payload.defaultData || {}),
      binding: { kind: 'none', id: '' },
    },
  })
  emitCanvas()
}
</script>

<style scoped>
.editor {
  flex: 1;
  display: flex;
  min-height: 0;
}

.editor__canvas-wrap {
  flex: 1;
  position: relative;
  background: #f4f3ee;
}

:deep(.vue-flow__node) {
  font-family: -apple-system, 'PingFang SC', sans-serif;
}

:deep(.vue-flow__edge-text) {
  font-size: 11px;
  fill: #555;
}
</style>
