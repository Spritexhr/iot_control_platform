<template>
  <div class="vessel-node">
    <Handle id="left"   type="source" :position="Position.Left" />
    <Handle id="right"  type="source" :position="Position.Right" />
    <Handle id="top"    type="source" :position="Position.Top" />
    <Handle id="bottom" type="source" :position="Position.Bottom" />

    <svg :viewBox="`0 0 ${w} ${h}`" class="vessel-node__svg" preserveAspectRatio="none">
      <rect
        v-if="data.shape !== 'cstr'"
        :x="2" :y="2"
        :width="w - 4" :height="h - 4"
        rx="6"
        class="vessel-node__shape"
      />
      <g v-else>
        <rect :x="2" :y="14" :width="w - 4" :height="h - 28" class="vessel-node__shape" />
        <ellipse :cx="w / 2" :cy="14" :rx="(w - 4) / 2" :ry="12" class="vessel-node__shape" />
        <ellipse :cx="w / 2" :cy="h - 14" :rx="(w - 4) / 2" :ry="12" class="vessel-node__shape" />
      </g>
    </svg>

    <div class="vessel-node__label">{{ data.label || '反应器' }}</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'

const props = defineProps({
  data: { type: Object, required: true },
})

const w = computed(() => props.data?.size?.w || 140)
const h = computed(() => props.data?.size?.h || 180)
</script>

<style scoped>
.vessel-node {
  position: relative;
  width: v-bind(w + 'px');
  height: v-bind(h + 'px');
}

.vessel-node__svg {
  width: 100%;
  height: 100%;
}

.vessel-node__shape {
  fill: #ffffff;
  stroke: #2a2a2a;
  stroke-width: 1.5;
}

.vessel-node__label {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  color: #2a2a2a;
  pointer-events: none;
  text-align: center;
  padding: 0 8px;
}
</style>
