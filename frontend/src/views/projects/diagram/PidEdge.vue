<template>
  <SmoothStepEdge
    :id="id"
    :source-x="sourceX"
    :source-y="sourceY"
    :target-x="targetX"
    :target-y="targetY"
    :source-position="sourcePosition"
    :target-position="targetPosition"
    :marker-start="markerStart"
    :marker-end="markerEnd"
    :interaction-width="interactionWidth"
    :label="renderedLabel"
    :label-style="labelStyle"
    :label-show-bg="Boolean(label)"
    :label-bg-style="labelBackgroundStyle"
    :label-bg-padding="[7, 4]"
    :label-bg-border-radius="4"
    :style="lineStyle"
  />
</template>

<script setup>
import { computed } from 'vue'
import { SmoothStepEdge } from '@vue-flow/core'

const props = defineProps({
  id: { type: String, required: true },
  sourceX: { type: Number, required: true },
  sourceY: { type: Number, required: true },
  targetX: { type: Number, required: true },
  targetY: { type: Number, required: true },
  sourcePosition: { type: String, default: undefined },
  targetPosition: { type: String, default: undefined },
  markerStart: { type: String, default: undefined },
  markerEnd: { type: String, default: undefined },
  interactionWidth: { type: Number, default: 20 },
  selected: { type: Boolean, default: false },
  label: { type: String, default: '' },
  style: { type: Object, default: () => ({}) },
  data: { type: Object, default: () => ({ label: '', kind: 'process' }) },
})

const renderedLabel = computed(() => props.label?.trim() || props.data?.label?.trim() || '')

const lineStyle = computed(() => {
  const selectedWidth = props.selected ? 0.5 : 0
  if (props.style && Object.keys(props.style).length) {
    const strokeWidth = Number(props.style.strokeWidth || 2) + selectedWidth
    return { ...props.style, strokeWidth }
  }
  switch (props.data?.kind) {
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
})

const labelStyle = {
  fill: '#27323a',
  fontSize: '12px',
  fontWeight: 600,
}

const labelBackgroundStyle = {
  fill: '#fffdf8',
  stroke: '#cec5b8',
  strokeWidth: 1,
}
</script>
