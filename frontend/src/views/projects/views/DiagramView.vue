<template>
  <div class="dv">
    <div class="dv__bar">
      <span class="dv__name">{{ view.name }}</span>
      <div class="dv__actions">
        <el-tag v-if="dirty" type="warning" size="small" effect="plain">未保存</el-tag>
        <el-button v-if="canEdit" size="small" @click="toggleMode">
          {{ mode === 'edit' ? '预览模式' : '编辑模式' }}
        </el-button>
        <el-button v-if="mode === 'edit' && canEdit" type="primary" size="small" :loading="saving" @click="save">
          保存
        </el-button>
      </div>
    </div>

    <DiagramEditor
      v-if="mode === 'edit'"
      :diagram="diagramObj"
      :targets="targets"
      @change="onCanvasChange"
    />
    <DiagramRuntime v-else :diagram="diagramObj" />
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'

import DiagramEditor from '../diagram/editor/DiagramEditor.vue'
import DiagramRuntime from '../diagram/runtime/DiagramRuntime.vue'
import { useProjectStore } from '@/stores/project'
import { updateView } from '@/api/projects'

const props = defineProps({
  // ProjectView 对象：{ id, name, view_type:'diagram', config(canvas) }
  view: { type: Object, required: true },
  canEdit: { type: Boolean, default: false },
})
const emit = defineEmits(['saved'])

const store = useProjectStore()

const EMPTY = () => ({ version: 1, viewport: { x: 0, y: 0, zoom: 1 }, nodes: [], edges: [] })
const canvas = ref(
  props.view.config && Array.isArray(props.view.config.nodes) ? props.view.config : EMPTY(),
)

const mode = ref('view')
const dirty = ref(false)
const saving = ref(false)

// DiagramEditor / DiagramRuntime 期望 { id, canvas } 形态的 diagram 对象
const diagramObj = computed(() => ({ id: props.view.id, canvas: canvas.value }))

// 可绑定点位 = 本视图所属房间(分区)的成员
const targets = computed(() => {
  const sensors = []
  const devices = []
  const secs = (store.layout?.sections || []).filter(
    (sec) => props.view.section == null || sec.id === props.view.section,
  )
  for (const sec of secs) {
    for (const s of sec.sensors || []) {
      sensors.push({ id: s.point_id, name: s.sensor_name || s.tag, tag: s.tag, data_key: s.data_key, unit: s.unit })
    }
    for (const d of sec.devices || []) {
      devices.push({ id: d.device_id, name: d.device_name || d.tag, tag: d.tag })
    }
  }
  return { sensors, devices }
})

function toggleMode() {
  mode.value = mode.value === 'edit' ? 'view' : 'edit'
}
function onCanvasChange(c) {
  canvas.value = c
  dirty.value = true
}
async function save() {
  saving.value = true
  try {
    await updateView(props.view.id, { config: canvas.value })
    dirty.value = false
    emit('saved', { id: props.view.id, config: canvas.value })
    ElMessage.success('已保存')
  } catch (e) {
    console.error('[diagram] 保存失败', e)
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped lang="scss">
.dv {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 230px);
  min-height: 480px;
  border: 1px solid var(--iot-border-color-light);
  border-radius: var(--iot-radius-lg);
  box-shadow: var(--iot-shadow-sm);
  overflow: hidden;
  background: var(--iot-bg-card);
}

.dv__bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--iot-spacing-sm) var(--iot-spacing-md);
  border-bottom: 1px solid var(--iot-border-color-light);
  flex-shrink: 0;
}

.dv__name {
  font-size: var(--iot-font-size-sm);
  font-weight: 600;
  color: var(--iot-text-primary);
}

.dv__actions {
  display: flex;
  align-items: center;
  gap: var(--iot-spacing-sm);
}
</style>
