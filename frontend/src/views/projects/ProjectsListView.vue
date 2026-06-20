<template>
  <div class="projects-list-view">
    <div class="iot-page-header">
      <div>
        <h1 class="iot-page-title">项目 / 场景</h1>
        <p class="iot-page-subtitle">一个项目 = 装置（传感器 / 设备）+ 控制（自动化规则）+ 展示（多视图）</p>
      </div>
      <el-button v-if="isStaff" type="primary" :icon="Plus" @click="openCreate">新建项目</el-button>
    </div>

    <div v-loading="loading">
      <div v-if="projects.length" class="iot-grid iot-grid--cards">
        <div
          v-for="p in projects"
          :key="p.id"
          class="iot-card iot-card--hover project-card"
          @click="$router.push(`/projects/${p.id}`)"
        >
          <div class="project-card__top">
            <span class="project-card__code">{{ p.code }}</span>
            <el-tag size="small" effect="plain" round>{{ sceneLabel(p.scene_type) }}</el-tag>
          </div>
          <h3 class="project-card__name">{{ p.name }}</h3>
          <p class="project-card__desc">{{ p.description || '—' }}</p>
          <div class="project-card__stats">
            <span>{{ p.sensor_count }} 传感器</span>
            <span>{{ p.device_count }} 设备</span>
            <span>{{ p.section_count }} 分区</span>
            <span>{{ p.view_count }} 视图</span>
          </div>
          <div class="project-card__actions" @click.stop>
            <el-button size="small" @click="$router.push(`/projects/${p.id}`)">进入</el-button>
            <el-button v-if="isStaff" size="small" @click="$router.push(`/projects/${p.id}/config`)">配置</el-button>
            <el-button v-if="isStaff" size="small" type="danger" plain @click="onDelete(p)">删除</el-button>
          </div>
        </div>
      </div>

      <div v-else class="iot-card empty-card">
        <el-empty :description="loading ? '加载中…' : (isStaff ? '暂无项目，点击右上角「新建项目」开始' : '暂无项目，请联系管理员创建')" />
      </div>
    </div>

    <el-dialog v-model="dialogVisible" title="新建项目" width="460px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="项目代号" required>
          <el-input v-model="form.code" placeholder="唯一短码，如 EB / HOME" maxlength="30" />
        </el-form-item>
        <el-form-item label="项目名称" required>
          <el-input v-model="form.name" placeholder="如 苯乙烯生产工厂" maxlength="100" />
        </el-form-item>
        <el-form-item label="场景类型">
          <el-select v-model="form.scene_type" style="width: 100%">
            <el-option label="工业装置" value="industrial" />
            <el-option label="智能家居" value="smart_home" />
            <el-option label="自定义" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

import { listProjects, createProject, deleteProject } from '@/api/projects'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const isStaff = computed(() => userStore.userInfo?.is_staff === true)

const projects = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const saving = ref(false)
const form = ref({ code: '', name: '', scene_type: 'custom', description: '' })

const SCENE_LABELS = { industrial: '工业装置', smart_home: '智能家居', custom: '自定义' }
function sceneLabel(t) { return SCENE_LABELS[t] || t }

async function load() {
  loading.value = true
  try {
    const data = await listProjects()
    projects.value = data.results || data || []
  } catch (e) {
    console.error('[projects] 加载列表失败', e)
  } finally {
    loading.value = false
  }
}
load()

function openCreate() {
  form.value = { code: '', name: '', scene_type: 'custom', description: '' }
  dialogVisible.value = true
}

async function submitCreate() {
  if (!form.value.code || !form.value.name) {
    ElMessage.warning('请填写项目代号和名称')
    return
  }
  saving.value = true
  try {
    const created = await createProject(form.value)
    dialogVisible.value = false
    ElMessage.success('项目已创建')
    router.push(`/projects/${created.id}/config`)
  } catch (e) {
    ElMessage.error(e.response?.data?.code?.[0] || e.response?.data?.detail || '创建失败')
  } finally {
    saving.value = false
  }
}

async function onDelete(p) {
  try {
    await ElMessageBox.confirm(`确认删除项目「${p.name}」？其分区、成员、视图将一并删除（不影响主模型传感器 / 设备）。`, '删除项目', { type: 'warning' })
  } catch { return }
  try {
    await deleteProject(p.id)
    ElMessage.success('已删除')
    load()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}
</script>

<style scoped lang="scss">
.projects-list-view {
  padding: 0;
}

.project-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: var(--iot-spacing-lg);
  cursor: pointer;
}

.project-card__top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.project-card__code {
  font-family: var(--iot-font-mono, ui-monospace, 'SFMono-Regular', monospace);
  font-size: var(--iot-font-size-sm);
  font-weight: 600;
  color: var(--iot-color-primary);
}

.project-card__name {
  font-size: var(--iot-font-size-md);
  font-weight: 600;
  color: var(--iot-text-primary);
  margin: 4px 0 0;
}

.project-card__desc {
  font-size: var(--iot-font-size-sm);
  color: var(--iot-text-secondary);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-card__stats {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: var(--iot-font-size-xs);
  color: var(--iot-text-secondary);
  padding-bottom: var(--iot-spacing-md);
  border-bottom: 1px solid var(--iot-border-color-light);
}

.project-card__actions {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}

.empty-card {
  padding: 48px 0;
}
</style>
