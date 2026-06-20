<template>
  <div class="projects-list-view">
    <div class="iot-page-header">
      <div>
        <h1 class="iot-page-title">项目 / 场景</h1>
        <p class="iot-page-subtitle">一个项目 = 装置（传感器 / 设备）+ 控制（自动化规则）+ 展示（多视图）</p>
      </div>
      <el-button v-if="isStaff" type="primary" :icon="Plus" @click="openCreate">新建项目</el-button>
    </div>

    <!-- 顶部统计概览条 -->
    <div v-if="projects.length" class="projects-stats-ribbon iot-mb-lg">
      <div class="stat-card">
        <div class="stat-card__icon-box"><el-icon><Folder /></el-icon></div>
        <div class="stat-card__info">
          <span class="stat-card__label">项目总数</span>
          <span class="stat-card__val">{{ totalProjects }}</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-card__icon-box"><el-icon><Cpu /></el-icon></div>
        <div class="stat-card__info">
          <span class="stat-card__label">纳管传感器</span>
          <span class="stat-card__val">{{ totalSensors }}</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-card__icon-box"><el-icon><Connection /></el-icon></div>
        <div class="stat-card__info">
          <span class="stat-card__label">受控设备</span>
          <span class="stat-card__val">{{ totalDevices }}</span>
        </div>
      </div>
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
            <div class="project-card__badge-wrap">
              <span class="project-card__icon-box">
                <el-icon><component :is="getSceneIcon(p.scene_type)" /></el-icon>
              </span>
              <span class="project-card__code">{{ p.code }}</span>
            </div>
            <el-tag size="small" :type="getTagType(p.scene_type)" effect="plain" round>{{ sceneLabel(p.scene_type) }}</el-tag>
          </div>
          
          <h3 class="project-card__name">{{ p.name }}</h3>
          <p class="project-card__desc">{{ p.description || '暂无描述信息' }}</p>
          
          <div class="project-card__stats">
            <span class="project-card__stat-item">
              <el-icon><Cpu /></el-icon> {{ p.sensor_count }} 传感器
            </span>
            <span class="project-card__stat-item">
              <el-icon><Connection /></el-icon> {{ p.device_count }} 设备
            </span>
            <span class="project-card__stat-item">
              <el-icon><Folder /></el-icon> {{ p.section_count }} 分区
            </span>
            <span class="project-card__stat-item">
              <el-icon><Monitor /></el-icon> {{ p.view_count }} 视图
            </span>
          </div>
          
          <div class="project-card__actions" @click.stop>
            <el-button type="primary" size="small" @click="$router.push(`/projects/${p.id}`)">进入项目</el-button>
            <el-dropdown v-if="isStaff" trigger="click" @command="handleCommand($event, p)">
              <el-button size="small" :icon="MoreFilled" circle class="project-card__more-btn" />
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="config" :icon="Setting">配置管理</el-dropdown-item>
                  <el-dropdown-item command="delete" :icon="Delete" style="color: var(--iot-color-danger)">删除项目</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </div>

      <div v-else class="iot-card empty-card">
        <el-empty :description="loading ? '加载中…' : (isStaff ? '暂无项目，点击右上角「新建项目」开始' : '暂无项目，请联系管理员创建')" />
      </div>
    </div>

    <el-dialog v-model="dialogVisible" title="新建项目" width="580px" class="create-project-dialog">
      <el-form :model="form" label-position="top">
        <div class="form-row">
          <el-form-item label="项目代号" required style="flex: 1">
            <el-input v-model="form.code" placeholder="如 EB / HOME" maxlength="30" />
          </el-form-item>
          <el-form-item label="项目名称" required style="flex: 2">
            <el-input v-model="form.name" placeholder="如 苯乙烯生产工厂" maxlength="100" />
          </el-form-item>
        </div>
        
        <el-form-item label="场景类型" required>
          <div class="scene-templates">
            <div 
              class="scene-template-card" 
              :class="{ active: form.scene_type === 'industrial' }"
              @click="form.scene_type = 'industrial'"
            >
              <el-icon class="scene-template-card__icon"><OfficeBuilding /></el-icon>
              <span class="scene-template-card__name">工业装置</span>
              <span class="scene-template-card__desc">生产工厂、配电等</span>
            </div>
            <div 
              class="scene-template-card" 
              :class="{ active: form.scene_type === 'smart_home' }"
              @click="form.scene_type = 'smart_home'"
            >
              <el-icon class="scene-template-card__icon"><House /></el-icon>
              <span class="scene-template-card__name">智能家居</span>
              <span class="scene-template-card__desc">家庭控制、楼宇等</span>
            </div>
            <div 
              class="scene-template-card" 
              :class="{ active: form.scene_type === 'custom' }"
              @click="form.scene_type = 'custom'"
            >
              <el-icon class="scene-template-card__icon"><Folder /></el-icon>
              <span class="scene-template-card__name">自定义</span>
              <span class="scene-template-card__desc">自由定义分区视图</span>
            </div>
          </div>
        </el-form-item>
        
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="添加项目背景及作用描述..." />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitCreate">创建项目</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Plus, 
  Folder, 
  Cpu, 
  Connection, 
  MoreFilled, 
  Delete, 
  Setting, 
  OfficeBuilding, 
  House, 
  Monitor 
} from '@element-plus/icons-vue'

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

// 统计计算
const totalProjects = computed(() => projects.value.length)
const totalSensors = computed(() => projects.value.reduce((acc, p) => acc + (p.sensor_count || 0), 0))
const totalDevices = computed(() => projects.value.reduce((acc, p) => acc + (p.device_count || 0), 0))

const SCENE_LABELS = { industrial: '工业装置', smart_home: '智能家居', custom: '自定义' }
function sceneLabel(t) { return SCENE_LABELS[t] || t }

function getSceneIcon(t) {
  if (t === 'industrial') return OfficeBuilding
  if (t === 'smart_home') return House
  return Folder
}

function getTagType(t) {
  if (t === 'industrial') return 'warning'
  if (t === 'smart_home') return 'success'
  return 'info'
}

function handleCommand(cmd, p) {
  if (cmd === 'config') {
    router.push(`/projects/${p.id}/config`)
  } else if (cmd === 'delete') {
    onDelete(p)
  }
}

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
  animation: iot-fade-in 0.4s ease forwards;
}

/* 顶部统计概览条 */
.projects-stats-ribbon {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--iot-spacing-md);
  
  .stat-card {
    background: var(--iot-bg-card);
    border: 1px solid var(--iot-border-color-light);
    border-radius: var(--iot-radius-lg);
    padding: var(--iot-spacing-md) var(--iot-spacing-lg);
    display: flex;
    align-items: center;
    gap: var(--iot-spacing-md);
    box-shadow: var(--iot-shadow-sm);
    transition: transform var(--iot-transition-base), box-shadow var(--iot-transition-base);

    &:hover {
      transform: translateY(-2px);
      box-shadow: var(--iot-shadow-md);
    }

    &__icon-box {
      width: 44px;
      height: 44px;
      border-radius: var(--iot-radius-base);
      background: var(--iot-color-primary-bg);
      color: var(--iot-color-primary);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
    }

    &__info {
      display: flex;
      flex-direction: column;
    }

    &__label {
      font-size: var(--iot-font-size-xs);
      color: var(--iot-text-secondary);
    }

    &__val {
      font-size: var(--iot-font-size-xl);
      font-weight: 700;
      color: var(--iot-text-primary);
      line-height: 1.2;
    }
  }
}

/* 项目卡片 */
.project-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: var(--iot-spacing-lg);
  cursor: pointer;
  height: 100%;

  &__top {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  &__badge-wrap {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  &__icon-box {
    width: 28px;
    height: 28px;
    border-radius: var(--iot-radius-sm);
    background: var(--iot-border-color-lighter);
    color: var(--iot-text-secondary);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
  }

  &__code {
    font-family: var(--iot-font-mono, ui-monospace, 'SFMono-Regular', monospace);
    font-size: var(--iot-font-size-sm);
    font-weight: 600;
    color: var(--iot-color-primary);
    background: var(--iot-color-primary-bg);
    padding: 2px 6px;
    border-radius: 4px;
  }

  &__name {
    font-size: var(--iot-font-size-md);
    font-weight: 600;
    color: var(--iot-text-primary);
    margin: 4px 0 0;
  }

  &__desc {
    font-size: var(--iot-font-size-sm);
    color: var(--iot-text-secondary);
    margin: 0;
    line-height: 1.5;
    height: 42px;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  &__stats {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    font-size: var(--iot-font-size-xs);
    color: var(--iot-text-secondary);
    padding: var(--iot-spacing-sm) 0;
    border-top: 1px dashed var(--iot-border-color-light);
    border-bottom: 1px dashed var(--iot-border-color-light);
    margin-top: auto;
  }

  &__stat-item {
    display: flex;
    align-items: center;
    gap: 4px;

    .el-icon {
      font-size: 13px;
    }
  }

  &__actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 4px;

    .el-button--primary {
      flex: 1;
      margin-right: 8px;
    }
  }

  &__more-btn {
    border-color: var(--iot-border-color);
    color: var(--iot-text-secondary);

    &:hover {
      background: var(--iot-border-color-lighter);
      color: var(--iot-text-primary);
    }
  }
}

/* 创建弹窗的表单布局 */
.form-row {
  display: flex;
  gap: var(--iot-spacing-md);
}

.scene-templates {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--iot-spacing-sm);
  width: 100%;
}

.scene-template-card {
  border: 1px solid var(--iot-border-color);
  border-radius: var(--iot-radius-base);
  padding: var(--iot-spacing-sm) var(--iot-spacing-md);
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  cursor: pointer;
  transition: all var(--iot-transition-base);

  &__icon {
    font-size: 24px;
    color: var(--iot-text-secondary);
    margin-bottom: 6px;
    transition: color var(--iot-transition-base);
  }

  &__name {
    font-size: var(--iot-font-size-sm);
    font-weight: 600;
    color: var(--iot-text-primary);
    margin-bottom: 4px;
  }

  &__desc {
    font-size: 11px;
    color: var(--iot-text-secondary);
    line-height: 1.3;
  }

  &:hover {
    border-color: var(--iot-color-primary-light);
    background: var(--iot-bg-card-hover);

    .scene-template-card__icon {
      color: var(--iot-color-primary-light);
    }
  }

  &.active {
    border-color: var(--iot-color-primary);
    background: var(--iot-color-primary-bg);

    .scene-template-card__icon {
      color: var(--iot-color-primary);
    }

    .scene-template-card__name {
      color: var(--iot-color-primary);
    }
  }
}

.empty-card {
  padding: 60px 0;
  display: flex;
  justify-content: center;
}
</style>

