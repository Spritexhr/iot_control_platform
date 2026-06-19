<template>
  <div class="pl">
    <div class="pl__head">
      <div>
        <h1 class="pl__title">项目 / 场景</h1>
        <p class="pl__sub">一个项目 = 装置（传感器/设备）+ 控制（自动化规则）+ 展示（多视图）</p>
      </div>
      <el-button v-if="isStaff" type="primary" @click="openCreate">新建项目</el-button>
    </div>

    <div v-loading="loading" class="pl__grid">
      <div
        v-for="p in projects"
        :key="p.id"
        class="pl-card"
        @click="$router.push(`/projects/${p.id}`)"
      >
        <div class="pl-card__top">
          <span class="pl-card__code">{{ p.code }}</span>
          <span class="pl-card__scene">{{ sceneLabel(p.scene_type) }}</span>
        </div>
        <h3 class="pl-card__name">{{ p.name }}</h3>
        <p class="pl-card__desc">{{ p.description || '—' }}</p>
        <div class="pl-card__stats">
          <span>{{ p.sensor_count }} 传感器</span>
          <span>{{ p.device_count }} 设备</span>
          <span>{{ p.section_count }} 分区</span>
          <span>{{ p.view_count }} 视图</span>
        </div>
        <div class="pl-card__actions" @click.stop>
          <el-button size="small" @click="$router.push(`/projects/${p.id}`)">进入</el-button>
          <el-button v-if="isStaff" size="small" @click="$router.push(`/projects/${p.id}/config`)">配置</el-button>
          <el-button v-if="isStaff" size="small" type="danger" plain @click="onDelete(p)">删除</el-button>
        </div>
      </div>

      <div v-if="!loading && projects.length === 0" class="pl__empty">
        暂无项目。{{ isStaff ? '点击右上角「新建项目」开始。' : '请联系管理员创建。' }}
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
    await ElMessageBox.confirm(`确认删除项目「${p.name}」？其分区、成员、视图将一并删除（不影响主模型传感器/设备）。`, '删除项目', { type: 'warning' })
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
.pl {
  padding: 24px;
}

.pl__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.pl__title {
  font-size: 22px;
  font-weight: 600;
  margin: 0;
}

.pl__sub {
  margin: 6px 0 0;
  font-size: 13px;
  color: #8a8a82;
}

.pl__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
  min-height: 120px;
}

.pl-card {
  background: #fff;
  border: 1px solid #e3e0d6;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: box-shadow 0.2s, border-color 0.2s;

  &:hover {
    border-color: #d97757;
    box-shadow: 0 4px 16px rgba(217, 119, 87, 0.12);
  }
}

.pl-card__top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pl-card__code {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  font-weight: 600;
  color: #d97757;
}

.pl-card__scene {
  font-size: 11px;
  color: #999;
  background: #f4f3ee;
  padding: 1px 8px;
  border-radius: 10px;
}

.pl-card__name {
  font-size: 16px;
  margin: 10px 0 4px;
}

.pl-card__desc {
  font-size: 12px;
  color: #999;
  margin: 0 0 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pl-card__stats {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 11px;
  color: #777;
  font-family: 'JetBrains Mono', monospace;
  padding-bottom: 12px;
  border-bottom: 1px solid #f0eee6;
}

.pl-card__actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.pl__empty {
  grid-column: 1 / -1;
  text-align: center;
  padding: 60px;
  color: #999;
  border: 1px dashed #ccc;
  border-radius: 8px;
}
</style>
