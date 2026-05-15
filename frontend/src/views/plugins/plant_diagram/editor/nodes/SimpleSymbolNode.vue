<template>
  <div class="sym-node" :class="`sym-node--${kind}`">
    <Handle id="left"   type="source" :position="Position.Left" />
    <Handle id="right"  type="source" :position="Position.Right" />
    <Handle id="top"    type="source" :position="Position.Top" />
    <Handle id="bottom" type="source" :position="Position.Bottom" />

    <!-- 阀门 -->
    <svg v-if="kind === 'valve'" viewBox="0 0 80 50" class="sym-node__svg">
      <polygon points="6,8 40,25 6,42" fill="#fff" stroke="#2a2a2a" stroke-width="1.5" />
      <polygon points="74,8 40,25 74,42" fill="#fff" stroke="#2a2a2a" stroke-width="1.5" />
    </svg>

    <!-- 塔 -->
    <svg v-else-if="kind === 'column'" viewBox="0 0 60 140" class="sym-node__svg">
      <ellipse cx="30" cy="10" rx="26" ry="8" fill="#fff" stroke="#2a2a2a" stroke-width="1.5" />
      <rect x="4" y="10" width="52" height="120" fill="#fff" stroke="#2a2a2a" stroke-width="1.5" />
      <ellipse cx="30" cy="130" rx="26" ry="8" fill="#fff" stroke="#2a2a2a" stroke-width="1.5" />
      <line v-for="y in [40, 60, 80, 100]" :key="y" x1="4" :y1="y" x2="56" :y2="y" stroke="#2a2a2a" stroke-width="0.7" />
    </svg>

    <!-- 泵 -->
    <svg v-else-if="kind === 'pump'" viewBox="0 0 70 60" class="sym-node__svg">
      <circle cx="35" cy="35" r="22" fill="#fff" stroke="#2a2a2a" stroke-width="1.5" />
      <line x1="35" y1="13" x2="62" y2="6" stroke="#2a2a2a" stroke-width="1.5" />
      <polygon points="35,35 22,28 22,42" fill="#2a2a2a" />
    </svg>

    <!-- 换热器：壳管式 -->
    <svg v-else-if="kind === 'heat_exchanger'" viewBox="0 0 100 50" class="sym-node__svg">
      <rect x="6" y="10" width="88" height="30" rx="6" fill="#fff" stroke="#2a2a2a" stroke-width="1.5" />
      <line x1="6"  y1="20" x2="94" y2="20" stroke="#2a2a2a" stroke-width="1" />
      <line x1="6"  y1="30" x2="94" y2="30" stroke="#2a2a2a" stroke-width="1" />
      <line x1="18" y1="2"  x2="18" y2="10" stroke="#2a2a2a" stroke-width="1.5" />
      <line x1="82" y1="40" x2="82" y2="48" stroke="#2a2a2a" stroke-width="1.5" />
    </svg>

    <!-- 混合器：Y 形 -->
    <svg v-else-if="kind === 'mixer'" viewBox="0 0 70 60" class="sym-node__svg">
      <circle cx="35" cy="30" r="22" fill="#fff" stroke="#2a2a2a" stroke-width="1.5" />
      <line x1="35" y1="8"  x2="35" y2="52" stroke="#2a2a2a" stroke-width="1.2" />
      <line x1="13" y1="30" x2="57" y2="30" stroke="#2a2a2a" stroke-width="1.2" />
      <line x1="19" y1="14" x2="51" y2="46" stroke="#2a2a2a" stroke-width="1" />
      <line x1="51" y1="14" x2="19" y2="46" stroke="#2a2a2a" stroke-width="1" />
    </svg>

    <!-- 过滤器：漏斗+滤网 -->
    <svg v-else-if="kind === 'filter'" viewBox="0 0 60 70" class="sym-node__svg">
      <polygon points="6,8 54,8 36,36 36,62 24,62 24,36" fill="#fff" stroke="#2a2a2a" stroke-width="1.5" />
      <line v-for="x in [10, 18, 26, 34, 42, 50]" :key="x" :x1="x" y1="20" :x2="x" y2="14" stroke="#2a2a2a" stroke-width="0.8" />
    </svg>

    <!-- 标签 -->
    <div v-else-if="kind === 'label'" class="sym-node__plain-label">{{ data.label || '注释' }}</div>

    <div v-if="kind !== 'label'" class="sym-node__label">{{ data.label || '' }}</div>
  </div>
</template>

<script setup>
import { Handle, Position } from '@vue-flow/core'

defineProps({
  kind: { type: String, required: true },   // valve | column | pump | label
  data: { type: Object, required: true },
})
</script>

<style scoped>
.sym-node {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.sym-node--valve          .sym-node__svg { width: 80px;  height: 50px;  }
.sym-node--column         .sym-node__svg { width: 60px;  height: 140px; }
.sym-node--pump           .sym-node__svg { width: 70px;  height: 60px;  }
.sym-node--heat_exchanger .sym-node__svg { width: 110px; height: 56px;  }
.sym-node--mixer          .sym-node__svg { width: 70px;  height: 60px;  }
.sym-node--filter         .sym-node__svg { width: 60px;  height: 70px;  }

.sym-node__label {
  font-size: 11px;
  color: #2a2a2a;
  font-family: 'JetBrains Mono', monospace;
}

.sym-node__plain-label {
  font-size: 13px;
  color: #2a2a2a;
  font-family: -apple-system, 'PingFang SC', sans-serif;
  background: rgba(255, 255, 255, 0.85);
  border: 1px dashed #888;
  padding: 4px 10px;
  border-radius: 3px;
}
</style>
