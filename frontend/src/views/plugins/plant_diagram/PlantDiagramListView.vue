<template>
  <div class="diagram-list">
    <div class="iot-page-header">
      <div>
        <h1 class="iot-page-title">P&amp;ID 画板 - {{ plantCode }}</h1>
        <p class="iot-page-subtitle">为该装置管理工艺流程图，绑定传感器实时显示</p>
      </div>
      <el-button v-if="isStaff" type="primary" :icon="Plus" @click="openCreate">新建画板</el-button>
    </div>

    <div class="iot-card">
      <div class="iot-card__body">
        <el-table :data="diagrams" v-loading="loading" stripe>
          <el-table-column prop="name" label="名称" min-width="200">
            <template #default="{ row }">
              <router-link :to="`/plugins/plant_diagram/${row.id}`" class="diagram-list__name">
                {{ row.name }}
                <el-tag v-if="row.is_default" size="small" type="success">默认</el-tag>
              </router-link>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="描述" min-width="200" />
          <el-table-column label="节点数" width="100" align="center">
            <template #default="{ row }">{{ row.node_count }}</template>
          </el-table-column>
          <el-table-column label="连线数" width="100" align="center">
            <template #default="{ row }">{{ row.edge_count }}</template>
          </el-table-column>
          <el-table-column label="更新时间" width="180">
            <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
          </el-table-column>
          <el-table-column v-if="isStaff" label="操作" width="220" align="center">
            <template #default="{ row }">
              <el-button text type="primary" size="small" @click="goEdit(row)">编辑</el-button>
              <el-button text size="small" @click="goView(row)">查看</el-button>
              <el-popconfirm title="确定删除此画板？" @confirm="handleDelete(row.id)">
                <template #reference>
                  <el-button text type="danger" size="small">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <el-dialog v-model="createOpen" title="新建画板" width="480px">
      <el-form label-position="top">
        <el-form-item label="装置代号">
          <el-input v-model="form.plant_code" placeholder="例如 EB" />
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="例如 EB 主反应区" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="form.is_default">设为默认画板</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createOpen = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

import { useUserStore } from '@/stores/user'
import { createDiagram, deleteDiagram, listDiagrams } from '@/api/plugins/plant_diagram'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const isStaff = computed(() => userStore.userInfo?.is_staff === true)
const plantCode = computed(() => (route.params.plantCode || 'EB').toString().toUpperCase())

const diagrams = ref([])
const loading = ref(false)

const createOpen = ref(false)
const creating = ref(false)
const form = reactive({ plant_code: '', name: '', description: '', is_default: false })

function openCreate() {
  form.plant_code = plantCode.value
  form.name = ''
  form.description = ''
  form.is_default = diagrams.value.length === 0
  createOpen.value = true
}

async function handleCreate() {
  if (!form.plant_code || !form.name) {
    ElMessage.warning('请填写装置代号和名称')
    return
  }
  creating.value = true
  try {
    const created = await createDiagram({
      plant_code: form.plant_code,
      name: form.name,
      description: form.description,
      is_default: form.is_default,
      canvas: { version: 1, viewport: { x: 0, y: 0, zoom: 1 }, nodes: [], edges: [] },
    })
    createOpen.value = false
    ElMessage.success('画板创建成功')
    router.push(`/plugins/plant_diagram/${created.id}?mode=edit`)
  } catch (e) {
    console.error('[diagram] 创建失败', e)
    ElMessage.error('创建失败')
  } finally {
    creating.value = false
  }
}

async function handleDelete(id) {
  try {
    await deleteDiagram(id)
    ElMessage.success('已删除')
    await load()
  } catch (e) {
    console.error('[diagram] 删除失败', e)
    ElMessage.error('删除失败')
  }
}

function goEdit(row) { router.push(`/plugins/plant_diagram/${row.id}?mode=edit`) }
function goView(row) { router.push(`/plugins/plant_diagram/${row.id}`) }

async function load() {
  loading.value = true
  try {
    const res = await listDiagrams(plantCode.value)
    diagrams.value = Array.isArray(res) ? res : (res.results || [])
  } catch (e) {
    console.error('[diagram] 列表失败', e)
    diagrams.value = []
  } finally {
    loading.value = false
  }
}

function formatTime(str) {
  if (!str) return '--'
  const d = new Date(str)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

onMounted(load)
</script>

<style scoped>
.diagram-list__name {
  color: var(--iot-color-primary);
  text-decoration: none;
}
.diagram-list__name:hover { text-decoration: underline; }
</style>
