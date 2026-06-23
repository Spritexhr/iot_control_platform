<template>
  <div class="plugins-list-view">
    <div class="iot-page-header">
      <div>
        <h1 class="iot-page-title">插件中心</h1>
        <p class="iot-page-subtitle">浏览、启用与管理实验性扩展功能</p>
      </div>
      <div class="header-actions">
        <el-button v-if="isSuperuser" type="primary" :icon="Connection" @click="handleSync">
          同步插件
        </el-button>
      </div>
    </div>

    <div v-loading="loading">
      <div v-if="visiblePlugins.length" class="iot-grid iot-grid--cards">
        <div v-for="p in visiblePlugins" :key="p.name" class="iot-card plugin-card">
          <div class="plugin-card__header">
            <div class="plugin-card__icon">
              <el-icon :size="24"><component :is="iconFor(p.name)" /></el-icon>
            </div>
            <div class="plugin-card__title-block">
              <div class="plugin-card__title">
                {{ titleFor(p.name) }}
              </div>
              <div class="plugin-card__name">{{ p.name }} · v{{ p.version || '0.0.0' }}</div>
            </div>
            <el-tag :type="p.enabled ? 'success' : 'info'" size="small">
              {{ p.enabled ? '已启用' : '已禁用' }}
            </el-tag>
          </div>

          <div class="plugin-card__desc">{{ p.description || '（无描述）' }}</div>

          <div class="plugin-card__footer">
            <el-button
              v-if="hasUI(p.name) && p.enabled"
              type="primary"
              :icon="View"
              @click="goPlugin(p.name)"
            >
              进入
            </el-button>
            <el-button v-else-if="hasUI(p.name)" disabled :icon="View">
              已禁用
            </el-button>
            <el-button v-else disabled>无可视界面</el-button>

            <el-switch
              v-if="isSuperuser"
              :model-value="p.enabled"
              :disabled="toggling === p.name"
              active-text="启用"
              inactive-text="禁用"
              inline-prompt
              @change="(v) => handleToggle(p, v)"
            />
          </div>
        </div>
      </div>

      <div v-else class="iot-card empty-card">
        <el-empty :description="loading ? '加载中…' : '暂无可用插件'">
          <el-button v-if="isSuperuser" type="primary" :icon="Connection" @click="handleSync">
            同步插件
          </el-button>
        </el-empty>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Connection, View, Box, DataLine } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { getPlugins, syncPlugins, enablePlugin, disablePlugin } from '@/api/plugins'

const router = useRouter()
const userStore = useUserStore()
const isSuperuser = computed(() => userStore.userInfo?.is_superuser === true)

const plugins = ref([])
const loading = ref(false)
const toggling = ref('')

const visiblePlugins = computed(() => plugins.value)

const KNOWN_PLUGINS = {
  data_viz: { title: '数据可视化', icon: DataLine, route: '/plugins/data_viz' },
}

function hasUI(name) {
  return name in KNOWN_PLUGINS
}
function iconFor(name) {
  return KNOWN_PLUGINS[name]?.icon || Box
}
function titleFor(name) {
  return KNOWN_PLUGINS[name]?.title || name
}
function goPlugin(name) {
  const route = KNOWN_PLUGINS[name]?.route
  if (route) router.push(route)
}

async function fetchPlugins() {
  loading.value = true
  try {
    const res = await getPlugins()
    plugins.value = res.results || res
  } catch (e) {
    ElMessage.error('获取插件列表失败')
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function handleSync() {
  loading.value = true
  try {
    const res = await syncPlugins()
    ElMessage.success(res.message || '同步完成')
    await fetchPlugins()
  } catch (e) {
    ElMessage.error('同步失败：' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

async function handleToggle(plugin, enabled) {
  toggling.value = plugin.name
  try {
    if (enabled) {
      await enablePlugin(plugin.name)
      ElMessage.success(`已启用 ${plugin.name}（重启后生效）`)
    } else {
      await disablePlugin(plugin.name)
      ElMessage.warning(`已禁用 ${plugin.name}（重启后生效）`)
    }
    await fetchPlugins()
  } catch (e) {
    ElMessage.error('切换失败：' + (e.response?.data?.detail || e.message))
  } finally {
    toggling.value = ''
  }
}

onMounted(fetchPlugins)
</script>

<style scoped>
.plugins-list-view {
  padding: 0;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.plugin-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 20px;
  transition: all var(--iot-transition-fast);
}

.plugin-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--iot-shadow-lg);
}

.plugin-card__header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.plugin-card__icon {
  width: 40px;
  height: 40px;
  border-radius: var(--iot-radius-base);
  background: var(--iot-color-primary-bg);
  color: var(--iot-color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.plugin-card__title-block {
  flex: 1;
  min-width: 0;
}

.plugin-card__title {
  font-size: 15px;
  font-weight: 600;
  color: var(--iot-text-primary);
}

.plugin-card__name {
  font-size: 12px;
  color: var(--iot-text-secondary);
  margin-top: 2px;
  font-family: var(--iot-font-mono, monospace);
}

.plugin-card__desc {
  font-size: 13px;
  color: var(--iot-text-secondary);
  line-height: 1.6;
  min-height: 40px;
}

.plugin-card__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-top: 8px;
  border-top: 1px solid var(--iot-border-light);
}

.empty-card {
  padding: 40px 0;
}
</style>
