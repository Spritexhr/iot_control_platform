<template>
  <aside class="toolbox">
    <template v-for="group in groups" :key="group.name">
      <div class="toolbox__section-title">{{ group.name }}</div>
      <div class="toolbox__grid">
        <div
          v-for="item in group.items"
          :key="item.type"
          class="toolbox__item"
          :draggable="true"
          :title="item.label"
          @dragstart="onDragStart($event, item)"
        >
          <SymbolGlyph
            class="toolbox__preview"
            :view-box="item.glyph.viewBox"
            :draw="item.glyph.draw"
          />
          <div class="toolbox__label">{{ item.label }}</div>
        </div>
      </div>
    </template>

    <div class="toolbox__hint">
      把图元拖到画布即可放置<br />
      节点四边为连接点，鼠标拖出生成连线
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'

import SymbolGlyph from './SymbolGlyph.vue'
import { PALETTE } from './symbols'

// 按 group 归组，保持 PALETTE 中首次出现的顺序
const groups = computed(() => {
  const order = []
  const map = {}
  for (const item of PALETTE) {
    if (!map[item.group]) {
      map[item.group] = { name: item.group, items: [] }
      order.push(map[item.group])
    }
    map[item.group].items.push(item)
  }
  return order
})

function onDragStart(event, item) {
  const payload = { type: item.type, defaultData: item.defaultData }
  event.dataTransfer.setData('application/x-plant-node', JSON.stringify(payload))
  event.dataTransfer.effectAllowed = 'copy'
}
</script>

<style scoped>
.toolbox {
  width: 132px;
  flex-shrink: 0;
  background: var(--iot-bg-card);
  border-right: 1px solid var(--iot-border-color-light);
  padding: 10px 8px;
  overflow-y: auto;
}

.toolbox__section-title {
  font-size: var(--iot-font-size-xs);
  color: var(--iot-text-secondary);
  margin: 10px 0 6px;
  letter-spacing: 1px;
}

.toolbox__section-title:first-child {
  margin-top: 0;
}

.toolbox__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.toolbox__item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 6px 4px;
  border: 1px solid var(--iot-border-color-light);
  border-radius: var(--iot-radius-sm);
  background: var(--iot-bg-card-hover);
  cursor: grab;
  user-select: none;
  transition: border-color var(--iot-transition-fast), background var(--iot-transition-fast);
}

.toolbox__item:hover {
  border-color: var(--iot-color-primary);
  background: var(--iot-color-primary-bg);
}

.toolbox__item:active {
  cursor: grabbing;
}

.toolbox__preview {
  width: 38px;
  height: 38px;
}

.toolbox__label {
  font-size: var(--iot-font-size-xs);
  color: var(--iot-text-regular);
}

.toolbox__hint {
  margin-top: 14px;
  font-size: 11px;
  color: var(--iot-text-secondary);
  line-height: 1.5;
  padding: 8px 4px;
  border-top: 1px dashed var(--iot-border-color-light);
}
</style>
