<template>
  <div class="runtime">
    <VueFlow
      v-model:nodes="nodes"
      v-model:edges="edges"
      :default-viewport="defaultViewport"
      :nodes-draggable="false"
      :nodes-connectable="false"
      :elements-selectable="false"
      :zoom-on-double-click="false"
      :pan-on-drag="true"
      fit-view-on-init
    >
      <Background pattern-color="#d8d2c4" :gap="16" />
      <Controls :show-interactive="false" />

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
</template>

<script setup>
import { ref, watch } from 'vue'
import { VueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'

import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'

import InstrumentNode from '../editor/nodes/InstrumentNode.vue'
import VesselNode from '../editor/nodes/VesselNode.vue'
import SimpleSymbolNode from '../editor/nodes/SimpleSymbolNode.vue'

const props = defineProps({
  diagram: { type: Object, required: true },
})

function edgeStyle(kind) {
  switch (kind) {
    case 'utility': return { stroke: '#2a2a2a', strokeWidth: 1.2, strokeDasharray: '6 4' }
    case 'signal':  return { stroke: '#888',    strokeWidth: 1,   strokeDasharray: '2 3' }
    default:        return { stroke: '#2a2a2a', strokeWidth: 2 }
  }
}

function canvasToFlow(canvas) {
  const nodes = (canvas?.nodes || []).map((n) => ({
    id: n.id,
    type: n.type,
    position: { x: n.position?.x || 0, y: n.position?.y || 0 },
    data: { ...(n.data || {}), binding: n.binding || { kind: 'none', id: '' }, size: n.size },
  }))
  const edges = (canvas?.edges || []).map((e) => ({
    id: e.id,
    source: e.source, sourceHandle: e.sourcePort || 'right',
    target: e.target, targetHandle: e.targetPort || 'left',
    type: 'smoothstep',
    label: e.data?.label || '',
    style: edgeStyle(e.data?.kind),
    markerEnd: 'arrowclosed',
  }))
  return { nodes, edges }
}

const initial = canvasToFlow(props.diagram?.canvas)
const nodes = ref(initial.nodes)
const edges = ref(initial.edges)
const defaultViewport = props.diagram?.canvas?.viewport || { x: 0, y: 0, zoom: 1 }

watch(() => props.diagram?.id, () => {
  const init = canvasToFlow(props.diagram?.canvas)
  nodes.value = init.nodes
  edges.value = init.edges
})
</script>

<style scoped>
.runtime {
  flex: 1;
  display: flex;
  min-height: 0;
  background: #f4f3ee;
  background-image:
    linear-gradient(rgba(0, 0, 0, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 0, 0, 0.04) 1px, transparent 1px);
  background-size: 24px 24px;
}
</style>
