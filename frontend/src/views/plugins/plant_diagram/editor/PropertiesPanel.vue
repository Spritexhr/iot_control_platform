<template>
  <aside class="props">
    <div v-if="!node" class="props__empty">
      选中节点 / 连线后可在此编辑属性
    </div>

    <template v-else-if="kind === 'node'">
      <div class="props__section-title">节点：{{ nodeTypeLabel(node.type) }}</div>

      <el-form size="small" label-position="top" @submit.prevent>
        <el-form-item label="显示名称">
          <el-input v-model="local.data.label" @input="emitChange" />
        </el-form-item>

        <el-form-item v-if="node.type === 'instrument'" label="符号 (ISA)">
          <el-select v-model="local.data.symbol" filterable allow-create @change="emitChange">
            <el-option v-for="s in symbols" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>

        <el-form-item label="绑定">
          <el-radio-group v-model="local.binding.kind" @change="onBindingKindChange">
            <el-radio value="none">不绑定</el-radio>
            <el-radio value="sensor">传感器</el-radio>
            <el-radio value="device">设备</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item v-if="local.binding.kind === 'sensor'" label="选择传感器">
          <el-select
            v-model="local.binding.id"
            filterable
            placeholder="搜索传感器 ID / 名称"
            @change="emitChange"
          >
            <el-option
              v-for="s in targets.sensors"
              :key="s.id"
              :label="`${s.id} · ${s.name}`"
              :value="s.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item v-if="local.binding.kind === 'device'" label="选择设备">
          <el-select
            v-model="local.binding.id"
            filterable
            placeholder="搜索设备 ID / 名称"
            @change="emitChange"
          >
            <el-option
              v-for="d in targets.devices"
              :key="d.id"
              :label="`${d.id} · ${d.name}`"
              :value="d.id"
            />
          </el-select>
        </el-form-item>

        <template v-if="node.type === 'instrument'">
          <el-form-item label="显示选项">
            <el-checkbox v-model="local.data.show_value" @change="emitChange">显示实时值</el-checkbox>
            <el-checkbox v-model="local.data.show_threshold" @change="emitChange">显示阈值</el-checkbox>
          </el-form-item>
        </template>

        <el-form-item label="坐标">
          <div class="props__pos">
            <el-input-number v-model="local.position.x" :step="10" controls-position="right" @change="emitChange" />
            <el-input-number v-model="local.position.y" :step="10" controls-position="right" @change="emitChange" />
          </div>
        </el-form-item>

        <el-form-item>
          <el-button type="danger" plain size="small" @click="$emit('delete-node', node.id)">删除节点</el-button>
        </el-form-item>
      </el-form>
    </template>

    <template v-else-if="kind === 'edge'">
      <div class="props__section-title">连线</div>
      <el-form size="small" label-position="top" @submit.prevent>
        <el-form-item label="标签">
          <el-input v-model="local.data.label" @input="emitChange" />
        </el-form-item>
        <el-form-item label="管线类型">
          <el-select v-model="local.data.kind" @change="emitChange">
            <el-option label="工艺管线（粗实线）" value="process" />
            <el-option label="公用工程（虚线）" value="utility" />
            <el-option label="信号线（细虚线）" value="signal" />
          </el-select>
        </el-form-item>
        <el-form-item label="介质">
          <el-input v-model="local.data.medium" placeholder="例如：EB+DEB" @input="emitChange" />
        </el-form-item>
        <el-form-item>
          <el-button type="danger" plain size="small" @click="$emit('delete-edge', node.id)">删除连线</el-button>
        </el-form-item>
      </el-form>
    </template>
  </aside>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'

const props = defineProps({
  selection: { type: Object, default: null },
  targets:   { type: Object, default: () => ({ sensors: [], devices: [] }) },
})

const emit = defineEmits(['update-node', 'update-edge', 'delete-node', 'delete-edge'])

// selection: { kind: 'node'|'edge', payload: nodeOrEdge }
const node = computed(() => props.selection?.payload || null)
const kind = computed(() => props.selection?.kind || null)

const symbols = ['TT', 'TI', 'PT', 'PI', 'FT', 'FI', 'LT', 'LI', 'AT', 'AI']

const local = reactive({
  data: {},
  binding: { kind: 'none', id: '' },
  position: { x: 0, y: 0 },
})

watch(() => props.selection, (sel) => {
  if (!sel) return
  const p = sel.payload
  local.data = { ...(p.data || {}) }
  if (sel.kind === 'node') {
    local.binding = { ...(p.data?.binding || { kind: 'none', id: '' }) }
    local.position = { x: Math.round(p.position?.x ?? 0), y: Math.round(p.position?.y ?? 0) }
  }
}, { immediate: true, deep: true })

function onBindingKindChange() {
  if (local.binding.kind === 'none') local.binding.id = ''
  emitChange()
}

function emitChange() {
  if (!props.selection) return
  if (kind.value === 'node') {
    emit('update-node', {
      id: node.value.id,
      patch: {
        data: { ...local.data, binding: { ...local.binding } },
        position: { ...local.position },
      },
    })
  } else if (kind.value === 'edge') {
    emit('update-edge', {
      id: node.value.id,
      patch: { data: { ...local.data } },
    })
  }
}

function nodeTypeLabel(t) {
  return ({
    instrument: '仪表', vessel: '反应器', column: '塔', valve: '阀门', pump: '泵',
    heat_exchanger: '换热器', mixer: '混合器', filter: '过滤器', label: '文本',
  })[t] || t
}
</script>

<style scoped>
.props {
  width: 280px;
  flex-shrink: 0;
  background: var(--iot-bg-card);
  border-left: 1px solid var(--iot-border-color-light);
  padding: 12px;
  overflow-y: auto;
}

.props__empty {
  color: var(--iot-text-secondary);
  font-size: var(--iot-font-size-sm);
  text-align: center;
  padding: 40px 8px;
}

.props__section-title {
  font-weight: 600;
  margin-bottom: 10px;
  font-size: var(--iot-font-size-sm);
  color: var(--iot-text-primary);
}

.props__pos {
  display: flex;
  gap: 6px;
}

.props__pos :deep(.el-input-number) {
  width: 100%;
}
</style>
