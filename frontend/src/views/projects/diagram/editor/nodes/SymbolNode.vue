<template>
  <div class="symbol-node" :class="`symbol-node--${type}`">
    <!-- 纯文本注释：本身就是文字，没有独立于文字的图形可转 -->
    <template v-if="def && def.labelMode === 'plain'">
      <Handle id="left"   type="source" :position="Position.Left" />
      <Handle id="right"  type="source" :position="Position.Right" />
      <Handle id="top"    type="source" :position="Position.Top" />
      <Handle id="bottom" type="source" :position="Position.Bottom" />
      <div class="symbol-node__plain-label">
        {{ data.label || def.defaultData?.label || '注释' }}
      </div>
    </template>

    <!-- 图形图元：旋转/镜像只作用于图形，4个连接点固定在四边不随图形转动 -->
    <template v-else-if="def">
      <Handle id="left"   type="source" :position="Position.Left" />
      <Handle id="right"  type="source" :position="Position.Right" />
      <Handle id="top"    type="source" :position="Position.Top" />
      <Handle id="bottom" type="source" :position="Position.Bottom" />
      <div class="symbol-node__transform" :style="transformStyle">
        <SymbolGlyph
          class="symbol-node__glyph"
          :viewBox="def.viewBox"
          :draw="def.draw"
          :style="{ width: def.size.w + 'px', height: def.size.h + 'px' }"
        />
      </div>
      <div v-if="def.labelMode !== 'none' && data.label" class="symbol-node__label">
        {{ data.label }}
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'

import SymbolGlyph from '../SymbolGlyph.vue'
import { SIMPLE_SYMBOLS } from '../symbols'

// Vue Flow 通过 nodeTypes 注册时会把 node.type 作为 prop 传入，据此查注册表
const props = defineProps({
  type: { type: String, required: true },
  data: { type: Object, required: true },
})

const def = computed(() => SIMPLE_SYMBOLS[props.type] || null)

// 旋转（每次 90°）+ 水平/竖直镜像：只套在图形+连接点上（不含标签文字），
// 这样旋转后管口朝向也跟着转，符合 P&ID 里转个阀门接竖直管的习惯，文字始终保持水平可读
const transformStyle = computed(() => {
  const rotation = props.data?.rotation || 0
  const sx = props.data?.flipH ? -1 : 1
  const sy = props.data?.flipV ? -1 : 1
  if (!rotation && sx === 1 && sy === 1) return null
  return { transform: `rotate(${rotation}deg) scale(${sx}, ${sy})` }
})
</script>

<style scoped>
.symbol-node {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.symbol-node__transform {
  position: relative;
  display: inline-flex;
}

.symbol-node__glyph {
  display: block;
}

.symbol-node__label {
  font-size: 11px;
  color: #2a2a2a;
  font-family: 'JetBrains Mono', monospace;
}

.symbol-node__plain-label {
  font-size: 13px;
  color: #2a2a2a;
  font-family: -apple-system, 'PingFang SC', sans-serif;
  background: rgba(255, 255, 255, 0.85);
  border: 1px dashed #888;
  padding: 4px 10px;
  border-radius: 3px;
}
</style>
