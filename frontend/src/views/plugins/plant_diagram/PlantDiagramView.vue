<template>
  <div class="diagram-view">
    <header class="diagram-view__header">
      <div class="diagram-view__title-group">
        <el-button text :icon="ArrowLeft" @click="goBack">返回画板列表</el-button>
        <span class="diagram-view__diagram-name">{{ diagram?.name || '画板' }}</span>
      </div>
      <div class="diagram-view__actions">
        <el-tag v-if="dirty" type="warning" size="small">未保存</el-tag>
        <el-button :disabled="!isStaff" :icon="EditPen" size="small" @click="toggleMode">
          {{ mode === 'edit' ? '预览模式' : '编辑模式' }}
        </el-button>
        <el-button
          v-if="mode === 'edit' && isStaff"
          type="primary"
          :icon="Check"
          size="small"
          :loading="saving"
          @click="save"
        >
          保存
        </el-button>
      </div>
    </header>

    <DiagramEditor
      v-if="mode === 'edit' && diagram"
      :diagram="diagram"
      :targets="targets"
      @change="onCanvasChange"
    />
    <DiagramRuntime
      v-else-if="diagram"
      :diagram="diagram"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Check, EditPen } from '@element-plus/icons-vue'

import DiagramEditor from './editor/DiagramEditor.vue'
import DiagramRuntime from './runtime/DiagramRuntime.vue'
import { useUserStore } from '@/stores/user'
import { usePlantStore } from '@/stores/plant'
import { useSSE } from '@/composables/useSSE'
import { buildPlantStreamUrl } from '@/api/plugins/eb_plant'
import {
  getBindableTargets,
  getDiagram,
  updateDiagram,
} from '@/api/plugins/plant_diagram'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const plantStore = usePlantStore()

const isStaff = computed(() => userStore.userInfo?.is_staff === true)
const mode = ref('view')        // edit | view
const diagram = ref(null)
const targets = ref({ sensors: [], devices: [] })
const dirty = ref(false)
const saving = ref(false)

function goBack() {
  if (dirty.value && !confirm('有未保存的修改，确定离开？')) return
  const code = diagram.value?.plant_code || 'EB'
  router.push(`/plugins/plant_diagram/list/${code}`)
}

function toggleMode() {
  if (!isStaff.value) {
    ElMessage.warning('需要工作人员权限')
    return
  }
  mode.value = mode.value === 'edit' ? 'view' : 'edit'
}

function onCanvasChange(canvas) {
  if (!diagram.value) return
  diagram.value.canvas = canvas
  dirty.value = true
}

async function save() {
  if (!diagram.value) return
  saving.value = true
  try {
    const { id, plant_code, name, description, is_default, sort_order, canvas } = diagram.value
    await updateDiagram(id, { plant_code, name, description, is_default, sort_order, canvas })
    dirty.value = false
    ElMessage.success('保存成功')
  } catch (e) {
    console.error('[diagram] 保存失败', e)
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function loadData() {
  const id = route.params.id
  if (!id) return
  try {
    diagram.value = await getDiagram(id)
    // 装置插件决定该画板能绑定哪些点位（EB 走 EBPlantSensorBinding 等），传 plant_code 给后端
    targets.value = await getBindableTargets(diagram.value?.plant_code || 'EB')
  } catch (e) {
    console.error('[diagram] 加载失败', e)
    ElMessage.error('加载画板失败')
  }
}

// 复用 EB 的 SSE 流喂 plantStore。useSSE 内部用 onScopeDispose 自清理。
plantStore.loadSnapshot()
const { displayStatus: sseStatus } = useSSE(buildPlantStreamUrl(), {
  snapshot: (data) => plantStore.applySnapshot(data),
  sample:   (data) => plantStore.applySample(data),
})
watch(sseStatus, (v) => { plantStore.sseStatus = v }, { immediate: true })

onMounted(async () => {
  await loadData()
  if (route.query.mode === 'edit' && isStaff.value) mode.value = 'edit'
})

// 离开前提示
function beforeUnload(e) {
  if (dirty.value) {
    e.preventDefault()
    e.returnValue = ''
  }
}
window.addEventListener('beforeunload', beforeUnload)
onUnmounted(() => window.removeEventListener('beforeunload', beforeUnload))
</script>

<style scoped>
.diagram-view {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 64px);
  background: var(--iot-bg-page);
}

.diagram-view__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  background: var(--iot-bg-card);
  border-bottom: 1px solid var(--iot-border-color-light);
  flex-shrink: 0;
}

.diagram-view__title-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.diagram-view__diagram-name {
  font-size: var(--iot-font-size-sm);
  font-weight: 600;
  color: var(--iot-text-primary);
}

.diagram-view__actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
