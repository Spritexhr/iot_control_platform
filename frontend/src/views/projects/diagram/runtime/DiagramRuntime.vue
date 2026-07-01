<template>
  <div class="runtime">
    <VueFlow
      v-model:nodes="nodes"
      v-model:edges="edges"
      :node-types="nodeTypes"
      :edge-types="edgeTypes"
      :default-viewport="defaultViewport"
      :nodes-draggable="false"
      :nodes-connectable="false"
      :elements-selectable="false"
      :zoom-on-double-click="false"
      :pan-on-drag="true"
    >
      <Background pattern-color="#d8d2c4" :gap="16" />
      <Controls :show-interactive="false" />
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

import { buildNodeTypes } from '../editor/nodeTypes'
import { buildEdgeTypes } from '../edgeTypes'
import { canvasToFlow } from '../canvasCodec'

const props = defineProps({
  diagram: { type: Object, required: true },
})

// 节点类型映射（type -> 组件），与编辑态共用同一图元注册表
const nodeTypes = buildNodeTypes()
const edgeTypes = buildEdgeTypes()

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
