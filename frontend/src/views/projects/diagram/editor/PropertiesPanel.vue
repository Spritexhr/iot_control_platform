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

        <el-form-item v-if="bindableKinds.length" label="绑定">
          <el-radio-group v-model="local.binding.kind" @change="onBindingKindChange">
            <el-radio value="none">不绑定</el-radio>
            <el-radio v-if="bindableKinds.includes('sensor')" value="sensor">传感器</el-radio>
            <el-radio v-if="bindableKinds.includes('device')" value="device">设备</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item v-if="local.binding.kind === 'sensor' && bindableKinds.includes('sensor')" label="选择传感器">
          <el-select
            v-model="local.binding.id"
            filterable
            placeholder="搜索位号 / 名称"
            @change="onSensorChange"
          >
            <el-option
              v-for="s in targets.sensors"
              :key="s.id"
              :label="sensorOptionLabel(s)"
              :value="s.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item v-if="local.binding.kind === 'device' && bindableKinds.includes('device')" label="选择设备">
          <el-select
            v-model="local.binding.id"
            filterable
            placeholder="搜索位号 / 名称"
            @change="emitChange"
          >
            <el-option
              v-for="d in targets.devices"
              :key="d.id"
              :label="deviceOptionLabel(d)"
              :value="d.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="坐标">
          <div class="props__pos">
            <el-input-number v-model="local.position.x" :step="10" controls-position="right" @change="emitChange" />
            <el-input-number v-model="local.position.y" :step="10" controls-position="right" @change="emitChange" />
          </div>
        </el-form-item>

        <el-form-item v-if="rotatable" label="变换">
          <div class="props__transform">
            <el-button size="small" @click="rotate90">旋转 90°（{{ local.data.rotation || 0 }}°）</el-button>
            <el-button
              size="small"
              :type="local.data.flipH ? 'primary' : 'default'"
              @click="toggleFlipH"
            >
              水平镜像
            </el-button>
            <el-button
              size="small"
              :type="local.data.flipV ? 'primary' : 'default'"
              @click="toggleFlipV"
            >
              竖直镜像
            </el-button>
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
          <el-input v-model="local.data.medium" placeholder="例如：物料A+物料B" @input="emitChange" />
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

import { getNodeMeta } from './symbols'

const props = defineProps({
  selection: { type: Object, default: null },
  targets:   { type: Object, default: () => ({ sensors: [], devices: [] }) },
})

const emit = defineEmits(['update-node', 'update-edge', 'delete-node', 'delete-edge'])

// selection: { kind: 'node'|'edge', payload: nodeOrEdge }
const node = computed(() => props.selection?.payload || null)
const kind = computed(() => props.selection?.kind || null)

// 图元能力来自注册表（symbols.js），不写死类型判断——以后给某个图元加绑定/转动能力，
// 只需在 symbols.js 对应条目加标记，这里和模板自动跟着生效
const meta = computed(() => getNodeMeta(node.value?.type))
const bindableKinds = computed(() => meta.value?.bindable || [])
const rotatable = computed(() => meta.value?.rotatable !== false)

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

function rotate90() {
  local.data.rotation = ((local.data.rotation || 0) + 90) % 360
  emitChange()
}
function toggleFlipH() {
  local.data.flipH = !local.data.flipH
  emitChange()
}
function toggleFlipV() {
  local.data.flipV = !local.data.flipV
  emitChange()
}

// 选传感器时把它的变量键值（data_key）和单位顺带记到节点 data 上，
// 这样仪表图元未收到实时数据前也能显示键值/单位，不必等 SSE 推送
function onSensorChange() {
  const target = props.targets.sensors.find((s) => s.id === local.binding.id)
  if (target) {
    local.data.dataKey = target.data_key || (target.id.includes('::') ? target.id.split('::')[1] : '')
    local.data.unit = target.unit || ''
  }
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
  return getNodeMeta(t)?.label || t
}

function sensorOptionLabel(s) {
  // 优先用位号，工程师习惯；带上字段名（data_key）和单位辅助识别
  const head = s.tag ? `${s.tag} · ${s.name}` : `${s.id} · ${s.name}`
  const dk = s.data_key ? ` / ${s.data_key}` : ''
  const unit = s.unit ? ` (${s.unit})` : ''
  return `${head}${dk}${unit}`
}

function deviceOptionLabel(d) {
  return d.tag ? `${d.tag} · ${d.name}` : `${d.id} · ${d.name}`
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

.props__transform {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
</style>
