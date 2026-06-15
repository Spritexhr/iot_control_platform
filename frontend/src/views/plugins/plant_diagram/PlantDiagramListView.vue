<template>
  <div class="diagram-list">
    <div class="iot-page-header">
      <div>
        <h1 class="iot-page-title">P&amp;ID 画板</h1>
        <p class="iot-page-subtitle">全厂工艺流程图（P&amp;ID）管理，可绑定传感器实时显示数据</p>
      </div>
      <div v-if="isStaff" class="diagram-list__toolbar">
        <el-button :icon="Upload" @click="triggerImport">导入</el-button>
        <el-button type="primary" :icon="Plus" @click="openCreate">新建画板</el-button>
        <input
          ref="importInput"
          type="file"
          accept="application/json,.json"
          style="display: none"
          @change="handleImportFile"
        />
      </div>
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
              <el-button text size="small" @click="handleExport(row)">导出</el-button>
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
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="例如 主反应区 / 公用工程" />
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
import { onMounted, reactive, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus, Upload } from '@element-plus/icons-vue'

import { useUserStore } from '@/stores/user'
import { createDiagram, deleteDiagram, listDiagrams, getDiagram } from '@/api/plugins/plant_diagram'

const router = useRouter()
const userStore = useUserStore()

const isStaff = computed(() => userStore.userInfo?.is_staff === true)

const diagrams = ref([])
const loading = ref(false)

const createOpen = ref(false)
const creating = ref(false)
const form = reactive({ name: '', description: '', is_default: false })

function openCreate() {
  form.name = ''
  form.description = ''
  form.is_default = false
  createOpen.value = true
}

async function handleCreate() {
  if (!form.name) {
    ElMessage.warning('请填写画板名称')
    return
  }
  creating.value = true
  try {
    const created = await createDiagram({
      plant_code: 'PLANT',
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

// ==================== 导出 ====================
// 导出单张画板为 .json 文件（含 canvas）。文件结构带 _type 标记便于导入时校验。
async function handleExport(row) {
  try {
    const full = await getDiagram(row.id)
    const payload = {
      _type: 'plant_diagram',
      _version: 1,
      name: full.name,
      description: full.description,
      plant_code: full.plant_code,
      canvas: full.canvas,
    }
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${full.plant_code}_${full.name || 'diagram'}.json`.replace(/[\\/:*?"<>|]/g, '_')
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    console.error('[diagram] 导出失败', e)
    ElMessage.error('导出失败')
  }
}

// ==================== 导入 ====================
const importInput = ref(null)
function triggerImport() {
  importInput.value?.click()
}

async function handleImportFile(event) {
  const file = event.target.files?.[0]
  event.target.value = ''  // 允许连续导入同一文件
  if (!file) return
  let parsed
  try {
    parsed = JSON.parse(await file.text())
  } catch {
    ElMessage.error('文件不是合法的 JSON')
    return
  }
  if (parsed._type !== 'plant_diagram' || typeof parsed.canvas !== 'object') {
    ElMessage.error('不是有效的画板导出文件')
    return
  }
  const targetCode = (parsed.plant_code || '').toString().toUpperCase() || 'PLANT'
  try {
    const created = await createDiagram({
      plant_code: targetCode,
      name: `${parsed.name || '导入画板'}（导入）`,
      description: parsed.description || '',
      is_default: false,
      canvas: parsed.canvas,
    })
    ElMessage.success('导入成功')
    router.push(`/plugins/plant_diagram/${created.id}?mode=edit`)
  } catch (e) {
    console.error('[diagram] 导入失败', e)
    ElMessage.error('导入失败')
  }
}

async function load() {
  loading.value = true
  try {
    const res = await listDiagrams()
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

.diagram-list__form-hint {
  margin-top: 4px;
  font-size: 12px;
  color: var(--iot-text-secondary);
  line-height: 1.4;
}

.diagram-list__toolbar {
  display: flex;
  gap: 8px;
}
</style>
