<template>
  <section class="folder-browser iot-card iot-mb-lg" :class="{ 'is-dragging-resources': draggingCount > 0 }">
    <div class="folder-intro">
      <div class="folder-intro__icon"><FolderOpened /></div>
      <div>
        <h2>{{ ls.t('resourceFolders.directoryTitle') }}</h2>
        <p>{{ ls.t('resourceFolders.directorySubtitle') }}</p>
      </div>
    </div>
    <div class="folder-toolbar">
      <div class="folder-modes">
        <el-button :type="mode === 'folder' && !currentFolderId ? 'primary' : 'default'" @click="navigate('folder', null)">
          <el-icon><House /></el-icon>{{ ls.t('resourceFolders.directoryHome') }}
        </el-button>
        <el-button :type="mode === 'all' ? 'primary' : 'default'" @click="navigate('all', null)">{{ ls.t('resourceFolders.allResources') }}</el-button>
        <el-button :type="mode === 'unfiled' ? 'primary' : 'default'" @click="navigate('unfiled', null)">{{ ls.t('resourceFolders.unfiled') }}</el-button>
      </div>
      <el-button v-if="isStaff && mode === 'folder'" type="primary" plain :icon="FolderAdd" @click="openCreate">
        {{ ls.t('resourceFolders.newFolder') }}
      </el-button>
    </div>

    <transition name="drag-hint">
      <div v-if="draggingCount > 0" class="folder-drag-hint">
        <span class="folder-drag-hint__pulse" />
        {{ ls.t('resourceFolders.dragHint').replace('{count}', draggingCount) }}
      </div>
    </transition>

    <el-breadcrumb v-if="mode === 'folder'" separator="/" class="folder-breadcrumb">
      <el-breadcrumb-item>
        <button type="button" class="crumb-button" @click="navigate('folder', null)">{{ ls.t('resourceFolders.root') }}</button>
      </el-breadcrumb-item>
      <el-breadcrumb-item v-for="item in breadcrumbs" :key="item.id">
        <button type="button" class="crumb-button" @click="navigate('folder', item.id)">{{ item.name }}</button>
      </el-breadcrumb-item>
    </el-breadcrumb>

    <div v-if="visibleFolders.length" class="folder-grid">
      <article
        v-for="folder in visibleFolders"
        :key="folder.id"
        class="folder-card"
        :class="{
          'is-drop-ready': draggingCount > 0,
          'is-drop-active': dropTargetId === folder.id,
        }"
        @click="navigate('folder', folder.id)"
        @dragenter.prevent.stop="dropTargetId = folder.id"
        @dragover.prevent.stop="dropTargetId = folder.id"
        @dragleave="handleDragLeave"
        @drop.prevent.stop="handleDrop(folder.id)"
      >
        <el-icon class="folder-icon"><FolderOpened v-if="dropTargetId === folder.id" /><Folder v-else /></el-icon>
        <div class="folder-meta">
          <strong>{{ folder.name }}</strong>
          <span>{{ folder.resource_count }} {{ ls.t('resourceFolders.resourceUnit') }} · {{ folder.child_count }} {{ ls.t('resourceFolders.childUnit') }}</span>
          <em v-if="dropTargetId === folder.id">{{ ls.t('resourceFolders.dropHere') }}</em>
        </div>
        <el-dropdown v-if="isStaff" trigger="click" @command="(command) => onFolderCommand(command, folder)" @click.stop>
          <el-button text circle :icon="MoreFilled" @click.stop />
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="rename">{{ ls.t('resourceFolders.rename') }}</el-dropdown-item>
              <el-dropdown-item command="move">{{ ls.t('resourceFolders.move') }}</el-dropdown-item>
              <el-dropdown-item command="up">{{ ls.t('resourceFolders.moveUp') }}</el-dropdown-item>
              <el-dropdown-item command="down">{{ ls.t('resourceFolders.moveDown') }}</el-dropdown-item>
              <el-dropdown-item command="delete" divided>{{ ls.t('common.delete') }}</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </article>
    </div>

    <el-dialog v-model="editVisible" :title="editingFolder ? ls.t('resourceFolders.editFolder') : ls.t('resourceFolders.newFolder')" width="460px" destroy-on-close>
      <el-form label-width="90px" @submit.prevent>
        <el-form-item :label="ls.t('resourceFolders.name')" required>
          <el-input v-model="folderForm.name" maxlength="100" show-word-limit @keyup.enter="saveFolder" />
        </el-form-item>
        <el-form-item :label="ls.t('resourceFolders.parent')">
          <el-select v-model="folderForm.parent" clearable :placeholder="ls.t('resourceFolders.root')" style="width: 100%">
            <el-option v-for="option in parentOptions" :key="option.id" :label="option.label" :value="option.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">{{ ls.t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="saving" @click="saveFolder">{{ ls.t('common.save') }}</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Folder, FolderAdd, FolderOpened, House, MoreFilled } from '@element-plus/icons-vue'
import { useLocaleStore } from '@/stores/locale'
import {
  createResourceFolder,
  deleteResourceFolder,
  getResourceFolders,
  reorderResourceFolders,
  updateResourceFolder,
} from '@/api/resourceFolders'

const props = defineProps({
  resourceType: { type: String, required: true },
  mode: { type: String, default: 'folder' },
  currentFolderId: { type: Number, default: null },
  isStaff: { type: Boolean, default: false },
  draggingCount: { type: Number, default: 0 },
})
const emit = defineEmits(['navigate', 'loaded', 'drop-resources'])
const ls = useLocaleStore()

const folders = ref([])
const editVisible = ref(false)
const editingFolder = ref(null)
const saving = ref(false)
const folderForm = ref({ name: '', parent: null })
const dropTargetId = ref(null)

const folderMap = computed(() => new Map(folders.value.map((item) => [item.id, item])))
const visibleFolders = computed(() => {
  const parentId = props.mode === 'folder' ? (props.currentFolderId ?? null) : null
  return folders.value.filter((item) => (item.parent ?? null) === parentId)
})
const breadcrumbs = computed(() => {
  const result = []
  let current = props.currentFolderId ? folderMap.value.get(props.currentFolderId) : null
  while (current) {
    result.unshift(current)
    current = current.parent ? folderMap.value.get(current.parent) : null
  }
  return result
})

function descendantsOf(folderId) {
  const result = new Set([folderId])
  let changed = true
  while (changed) {
    changed = false
    folders.value.forEach((item) => {
      if (item.parent && result.has(item.parent) && !result.has(item.id)) {
        result.add(item.id)
        changed = true
      }
    })
  }
  return result
}

function folderPath(folder) {
  const names = [folder.name]
  let parent = folder.parent ? folderMap.value.get(folder.parent) : null
  while (parent) {
    names.unshift(parent.name)
    parent = parent.parent ? folderMap.value.get(parent.parent) : null
  }
  return names.join(' / ')
}

const parentOptions = computed(() => {
  const excluded = editingFolder.value ? descendantsOf(editingFolder.value.id) : new Set()
  return folders.value
    .filter((item) => !excluded.has(item.id))
    .map((item) => ({ ...item, label: folderPath(item) }))
})

async function loadFolders() {
  try {
    const data = await getResourceFolders(props.resourceType)
    folders.value = data.results || data
    emit('loaded', folders.value)
  } catch {
    ElMessage.error(ls.t('resourceFolders.loadFailed'))
  }
}

function navigate(mode, folderId) {
  emit('navigate', { mode, folderId })
}

function handleDragLeave(event) {
  if (!event.currentTarget.contains(event.relatedTarget)) dropTargetId.value = null
}

function handleDrop(folderId) {
  if (!props.draggingCount) return
  dropTargetId.value = null
  emit('drop-resources', { folderId })
}

function openCreate() {
  editingFolder.value = null
  folderForm.value = { name: '', parent: props.currentFolderId ?? null }
  editVisible.value = true
}

function onFolderCommand(command, folder) {
  if (command === 'up' || command === 'down') {
    changeFolderOrder(folder, command === 'up' ? -1 : 1)
    return
  }
  if (command === 'delete') {
    removeFolder(folder)
    return
  }
  editingFolder.value = folder
  folderForm.value = {
    name: folder.name,
    parent: command === 'move' ? (folder.parent ?? null) : (folder.parent ?? null),
  }
  editVisible.value = true
}

async function changeFolderOrder(folder, delta) {
  const ordered = [...visibleFolders.value]
  const index = ordered.findIndex((item) => item.id === folder.id)
  const target = index + delta
  if (index < 0 || target < 0 || target >= ordered.length) return
  ;[ordered[index], ordered[target]] = [ordered[target], ordered[index]]
  try {
    await reorderResourceFolders(ordered.map((item) => item.id))
    await loadFolders()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || ls.t('resourceFolders.saveFailed'))
  }
}

async function saveFolder() {
  const name = folderForm.value.name.trim()
  if (!name) {
    ElMessage.warning(ls.t('resourceFolders.folderNameRequired'))
    return
  }
  saving.value = true
  try {
    const payload = { name, parent: folderForm.value.parent ?? null }
    if (editingFolder.value) {
      await updateResourceFolder(editingFolder.value.id, payload)
      ElMessage.success(ls.t('resourceFolders.updated'))
    } else {
      await createResourceFolder({ ...payload, resource_type: props.resourceType })
      ElMessage.success(ls.t('resourceFolders.created'))
    }
    editVisible.value = false
    await loadFolders()
  } catch (error) {
    const data = error.response?.data
    ElMessage.error(data?.detail || data?.name?.[0] || data?.parent?.[0] || ls.t('resourceFolders.saveFailed'))
  } finally {
    saving.value = false
  }
}

async function removeFolder(folder) {
  try {
    await ElMessageBox.confirm(
      ls.t('resourceFolders.deleteConfirm').replace('{name}', folder.name),
      ls.t('resourceFolders.deleteTitle'), { type: 'warning' },
    )
    await deleteResourceFolder(folder.id)
    ElMessage.success(ls.t('resourceFolders.deleted'))
    await loadFolders()
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    ElMessage.error(error.response?.data?.detail || ls.t('resourceFolders.deleteFailed'))
  }
}

defineExpose({ refresh: loadFolders })
onMounted(loadFolders)
</script>

<style scoped>
.folder-browser {
  position: relative;
  overflow: hidden;
  padding: 22px;
  border: 1px solid rgba(217, 119, 87, .16);
  background:
    radial-gradient(circle at 92% 0, rgba(217, 119, 87, .11), transparent 30%),
    linear-gradient(145deg, #fffdf8 0%, #faf5ec 100%);
}
.folder-browser::after { content: ''; position: absolute; top: -28px; right: -22px; width: 110px; height: 76px; border: 1px solid rgba(217, 119, 87, .1); border-radius: 50%; transform: rotate(-12deg); pointer-events: none; }
.folder-browser.is-dragging-resources { border-color: rgba(217, 119, 87, .48); box-shadow: 0 12px 34px rgba(121, 75, 48, .1); }
.folder-intro { display: flex; align-items: center; gap: 12px; margin-bottom: 18px; }
.folder-intro__icon { display: grid; width: 42px; height: 42px; flex: 0 0 auto; place-items: center; border-radius: 13px; color: #c86647; background: rgba(217, 119, 87, .13); font-size: 22px; }
.folder-intro h2 { margin: 0; color: var(--iot-text-primary); font-size: 17px; }
.folder-intro p { margin: 4px 0 0; color: var(--iot-text-secondary); font-size: 13px; }
.folder-toolbar { position: relative; z-index: 1; display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.folder-modes { display: flex; gap: 6px; padding: 4px; border: 1px solid rgba(113, 91, 76, .1); border-radius: 12px; background: rgba(255, 255, 255, .68); flex-wrap: wrap; }
.folder-modes :deep(.el-button) { margin: 0; border: 0; border-radius: 9px; box-shadow: none; }
.folder-breadcrumb { margin-top: 18px; padding: 11px 14px; border-radius: 10px; background: rgba(255,255,255,.62); }
.crumb-button { border: 0; padding: 0; background: none; color: inherit; cursor: pointer; font: inherit; }
.crumb-button:hover { color: var(--iot-color-primary, #d97757); }
.folder-drag-hint { display: flex; align-items: center; gap: 9px; margin-top: 14px; padding: 10px 13px; border: 1px dashed rgba(217, 119, 87, .55); border-radius: 10px; color: #a84e34; background: rgba(255, 245, 238, .78); font-size: 13px; }
.folder-drag-hint__pulse { width: 8px; height: 8px; border-radius: 50%; background: #d97757; box-shadow: 0 0 0 5px rgba(217,119,87,.14); animation: drop-pulse 1.2s infinite; }
.folder-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(225px, 1fr)); gap: 13px; margin-top: 18px; }
.folder-card { position: relative; display: flex; align-items: center; gap: 13px; min-height: 84px; padding: 15px; overflow: hidden; border: 1px solid rgba(113, 91, 76, .14); border-radius: 14px; background: rgba(255, 255, 255, .84); box-shadow: 0 5px 16px rgba(81, 62, 48, .045); cursor: pointer; transition: border-color .18s, transform .18s, box-shadow .18s, background .18s; }
.folder-card::before { content: ''; position: absolute; top: 0; left: 16px; width: 46px; height: 4px; border-radius: 0 0 4px 4px; background: rgba(217, 119, 87, .42); }
.folder-card:hover { border-color: rgba(217, 119, 87, .52); box-shadow: 0 9px 22px rgba(102, 66, 45, .09); transform: translateY(-2px); }
.folder-card.is-drop-ready { border-style: dashed; }
.folder-card.is-drop-active { border-color: #d97757; border-style: solid; background: #fff5ee; box-shadow: 0 0 0 4px rgba(217, 119, 87, .14), 0 12px 26px rgba(126, 67, 42, .14); transform: translateY(-3px) scale(1.01); }
.folder-icon { display: grid; width: 42px; height: 42px; flex: 0 0 auto; place-items: center; border-radius: 12px; color: #cc6a4b; background: rgba(217, 119, 87, .11); font-size: 25px; }
.is-drop-active .folder-icon { color: #fff; background: #d97757; }
.folder-meta { display: flex; flex: 1; min-width: 0; flex-direction: column; gap: 5px; }
.folder-meta strong { overflow: hidden; color: var(--iot-text-primary); text-overflow: ellipsis; white-space: nowrap; }
.folder-meta span { color: var(--iot-text-secondary); font-size: 12px; }
.folder-meta em { color: #bd5b3e; font-size: 12px; font-style: normal; font-weight: 600; }
.drag-hint-enter-active, .drag-hint-leave-active { transition: opacity .18s, transform .18s; }
.drag-hint-enter-from, .drag-hint-leave-to { opacity: 0; transform: translateY(-5px); }
@keyframes drop-pulse { 50% { box-shadow: 0 0 0 8px rgba(217,119,87,0); } }
:global(html.dark) .folder-browser { background: radial-gradient(circle at 92% 0, rgba(232,136,90,.10), transparent 30%), linear-gradient(145deg, var(--iot-bg-card), var(--iot-bg-page)); }
:global(html.dark) .folder-modes, :global(html.dark) .folder-breadcrumb { background: rgba(255,255,255,.035); }
:global(html.dark) .folder-card { border-color: var(--iot-border-color); background: var(--iot-bg-card); }
:global(html.dark) .folder-card.is-drop-active { border-color: var(--iot-color-primary); background: var(--iot-color-primary-bg); }
@media (max-width: 640px) {
  .folder-browser { padding: 16px; }
  .folder-toolbar { align-items: stretch; flex-direction: column; }
  .folder-modes { display: grid; grid-template-columns: 1fr 1fr; }
  .folder-modes :deep(.el-button:first-child) { grid-column: 1 / -1; }
  .folder-grid { grid-template-columns: 1fr; }
}
</style>
