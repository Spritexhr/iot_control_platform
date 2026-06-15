<template>
  <div class="symbol-node" :class="`symbol-node--${type}`">
    <Handle id="left"   type="source" :position="Position.Left" />
    <Handle id="right"  type="source" :position="Position.Right" />
    <Handle id="top"    type="source" :position="Position.Top" />
    <Handle id="bottom" type="source" :position="Position.Bottom" />

    <!-- 纯文本注释 -->
    <div v-if="def && def.labelMode === 'plain'" class="symbol-node__plain-label">
      {{ data.label || def.defaultData?.label || '注释' }}
    </div>

    <!-- 图形图元 -->
    <template v-else-if="def">
      <SymbolGlyph
        class="symbol-node__glyph"
        :viewBox="def.viewBox"
        :draw="def.draw"
        :style="{ width: def.size.w + 'px', height: def.size.h + 'px' }"
      />
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
</script>

<style scoped>
.symbol-node {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
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
