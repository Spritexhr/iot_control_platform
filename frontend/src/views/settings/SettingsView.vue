<template>
  <div class="settings-view">
    <div class="iot-page-header">
      <div>
        <h1 class="iot-page-title">{{ ls.t('settings.title') }}</h1>
        <p class="iot-page-subtitle">{{ ls.t('settings.subtitle') }}</p>
      </div>
    </div>

    <!-- ==================== MQTT 连接状态 ==================== -->
    <div class="iot-card iot-mb-lg">
      <div class="iot-card__header">
        <span class="section-title">{{ ls.t('settings.mqttStatus') }}</span>
        <el-button text :icon="Refresh" :loading="mqttLoading" @click="fetchMqttStatus">
          {{ ls.t('common.refresh') }}
        </el-button>
      </div>
      <div class="iot-card__body">
        <div class="setting-item">
          <span class="setting-label">{{ ls.t('settings.brokerAddr') }}</span>
          <span class="setting-value">{{ mqttInfo.broker || '--' }}:{{ mqttInfo.port || '--' }}</span>
        </div>
        <div class="setting-item">
          <span class="setting-label">{{ ls.t('settings.connStatus') }}</span>
          <span
            class="iot-status-tag"
            :class="mqttInfo.is_connected ? 'iot-status-tag--online' : 'iot-status-tag--offline'"
          >
            <span
              class="iot-status-dot"
              :class="mqttInfo.is_connected ? 'iot-status-dot--online' : 'iot-status-dot--offline'"
            ></span>
            {{ mqttInfo.is_connected ? ls.t('settings.connected') : ls.t('settings.disconnected') }}
          </span>
        </div>
      </div>
    </div>

    <!-- ==================== 可用命令 ==================== -->
    <div v-if="isSuperuser" class="iot-card iot-mb-lg">
      <div class="iot-card__header">
        <span class="section-title">{{ ls.t('settings.commands') }}</span>
      </div>
      <div class="iot-card__body">
        <div class="command-item">
          <div class="command-item__info">
            <span class="command-item__name">{{ ls.t('settings.cleanupData') }}</span>
            <span class="command-item__desc">{{ ls.t('settings.cleanupDesc') }}</span>
          </div>
          <el-button
            type="primary"
            :icon="VideoPlay"
            :loading="cleanupLoading"
            @click="handleCleanupOldData"
          >
            {{ ls.t('settings.execute') }}
          </el-button>
        </div>
      </div>
    </div>

    <!-- ==================== 平台配置 ==================== -->
    <div class="iot-card iot-mb-lg">
      <div class="iot-card__header">
        <span class="section-title">{{ ls.t('settings.platformConfig') }}</span>
        <div class="header-actions">
          <el-button
            v-if="isSuperuser"
            :icon="Refresh"
            size="small"
            :loading="reloadLoading"
            @click="handleReloadConfig"
          >
            {{ ls.t('settings.applyConfig') }}
          </el-button>
          <el-button
            v-if="isSuperuser"
            type="primary"
            :icon="Plus"
            size="small"
            @click="openConfigDialog(null)"
          >
            {{ ls.t('settings.addConfig') }}
          </el-button>
        </div>
      </div>
      <div class="iot-card__body">
        <el-table :data="platformConfigs" v-loading="configsLoading" stripe>
          <el-table-column prop="key" :label="ls.t('settings.configKey')" width="200" />
          <el-table-column prop="category" :label="ls.t('settings.category')" width="100" />
          <el-table-column :label="ls.t('settings.configValue')" min-width="200">
            <template #default="{ row }">
              <span class="config-value">{{ formatValue(row.value) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="description" :label="ls.t('settings.configDesc')" min-width="120" show-overflow-tooltip />
          <el-table-column v-if="isSuperuser" :label="ls.t('common.edit')" width="140" align="center" fixed="right">
            <template #default="{ row }">
              <div class="config-actions">
                <el-button plain type="primary" size="small" @click="openConfigDialog(row)">
                  {{ ls.t('common.edit') }}
                </el-button>
                <el-popconfirm
                  :title="ls.t('settings.deleteConfigConfirm')"
                  :confirm-button-text="ls.t('common.delete')"
                  :cancel-button-text="ls.t('common.cancel')"
                  @confirm="handleDeleteConfig(row.key)"
                >
                  <template #reference>
                    <el-button plain type="danger" size="small">{{ ls.t('common.delete') }}</el-button>
                  </template>
                </el-popconfirm>
              </div>
            </template>
          </el-table-column>
        </el-table>
        <div v-if="!configsLoading && platformConfigs.length === 0" class="empty-hint">
          <el-empty :description="ls.t('settings.noConfig')" />
        </div>
      </div>
    </div>

    <!-- 配置编辑弹窗 -->
    <el-dialog
      v-model="configDialogVisible"
      :title="configForm.id ? ls.t('settings.editConfigTitle') : ls.t('settings.addConfigTitle')"
      width="600px"
      destroy-on-close
    >
      <el-form :model="configForm" label-width="100px" :rules="configRules" ref="configFormRef">
        <el-form-item :label="ls.t('settings.configKey')" prop="key">
          <el-input
            v-model="configForm.key"
            :placeholder="ls.t('settings.configKeyPlaceholder')"
            :disabled="!!configForm.id"
          />
        </el-form-item>
        <el-form-item :label="ls.t('settings.category')" prop="category">
          <el-select v-model="configForm.category" :placeholder="ls.t('settings.selectCategory')" filterable allow-create style="width: 100%">
            <el-option label="mqtt" value="mqtt" />
            <el-option label="devices" value="devices" />
            <el-option label="data_retention" value="data_retention" />
            <el-option label="general" value="general" />
          </el-select>
        </el-form-item>
        <el-form-item :label="ls.t('settings.configValue')" prop="value">
          <el-input
            v-model="configForm.valueJson"
            type="textarea"
            :rows="4"
            :placeholder="ls.t('settings.configValuePlaceholder')"
          />
        </el-form-item>
        <el-form-item :label="ls.t('settings.configDesc')">
          <el-input v-model="configForm.description" :placeholder="ls.t('common.optional')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="configDialogVisible = false">{{ ls.t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="configSaving" @click="handleSaveConfig">{{ ls.t('common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Plus, VideoPlay } from '@element-plus/icons-vue'
import { getMqttStatus } from '@/api/system'
import {
  getPlatformConfigs,
  createPlatformConfig,
  updatePlatformConfig,
  deletePlatformConfig,
  reloadPlatformConfig,
  runCleanupOldData,
} from '@/api/platformConfig'
import { useUserStore } from '@/stores/user'
import { useLocaleStore } from '@/stores/locale'

const ls = useLocaleStore()

// ==================== 权限 ====================
const userStore = useUserStore()
const isSuperuser = computed(() => userStore.userInfo?.is_superuser === true)

// ==================== MQTT 状态 ====================
const mqttInfo = ref({ broker: '', port: '', is_connected: false })
const mqttLoading = ref(false)

async function fetchMqttStatus() {
  mqttLoading.value = true
  try {
    const data = await getMqttStatus()
    mqttInfo.value = data
  } catch {
    mqttInfo.value = { broker: '--', port: '--', is_connected: false }
  } finally {
    mqttLoading.value = false
  }
}

// ==================== 平台配置 ====================
const platformConfigs = ref([])
const configsLoading = ref(false)
const configDialogVisible = ref(false)
const configSaving = ref(false)
const configFormRef = ref(null)
const reloadLoading = ref(false)
const cleanupLoading = ref(false)

const configRules = computed(() => ({
  key: [{ required: true, message: ls.t('settings.configKeyRequired'), trigger: 'blur' }],
}))

const configForm = ref({
  id: null,
  key: '',
  value: null,
  valueJson: '',
  category: 'general',
  description: '',
})

function formatValue(val) {
  if (val === null || val === undefined) return '-'
  if (typeof val === 'object') return JSON.stringify(val)
  return String(val)
}

async function fetchPlatformConfigs() {
  configsLoading.value = true
  try {
    const data = await getPlatformConfigs()
    platformConfigs.value = data.results || data
  } catch {
    ElMessage.error(ls.t('settings.fetchFailed'))
  } finally {
    configsLoading.value = false
  }
}

function openConfigDialog(row) {
  if (row) {
    configForm.value = {
      id: row.id,
      key: row.key,
      value: row.value,
      valueJson: typeof row.value === 'object' ? JSON.stringify(row.value, null, 2) : String(row.value ?? ''),
      category: row.category || 'general',
      description: row.description || '',
    }
  } else {
    configForm.value = {
      id: null,
      key: '',
      value: null,
      valueJson: '',
      category: 'general',
      description: '',
    }
  }
  configDialogVisible.value = true
}

async function handleSaveConfig() {
  const formEl = configFormRef.value
  if (formEl) {
    const valid = await formEl.validate().catch(() => false)
    if (!valid) return
  }

  let value
  const raw = configForm.value.valueJson.trim()
  if (raw === '') {
    value = null
  } else {
    try {
      value = JSON.parse(raw)
    } catch {
      ElMessage.error(ls.t('settings.jsonError'))
      return
    }
  }

  const payload = {
    key: configForm.value.key,
    value,
    category: configForm.value.category,
    description: configForm.value.description,
  }

  configSaving.value = true
  try {
    if (configForm.value.id) {
      await updatePlatformConfig(configForm.value.key, payload)
      ElMessage.success(ls.t('settings.configUpdated'))
    } else {
      await createPlatformConfig(payload)
      ElMessage.success(ls.t('settings.configCreated'))
    }
    configDialogVisible.value = false
    fetchPlatformConfigs()
  } catch (err) {
    const detail = err.response?.data
    const msg = typeof detail === 'object' ? (detail.detail || Object.values(detail).flat().join('；')) : ls.t('settings.saveFailed')
    ElMessage.error(msg)
  } finally {
    configSaving.value = false
  }
}

async function handleDeleteConfig(key) {
  try {
    await deletePlatformConfig(key)
    ElMessage.success(ls.t('settings.deleteSuccess'))
    fetchPlatformConfigs()
  } catch {
    ElMessage.error(ls.t('settings.deleteFailed'))
  }
}

async function handleCleanupOldData() {
  cleanupLoading.value = true
  try {
    const res = await runCleanupOldData()
    const output = res?.output || ''
    ElMessage.success(output || ls.t('settings.cleanupSuccess'))
  } catch (err) {
    const detail = err.response?.data
    const msg = typeof detail === 'object' ? (detail.detail || ls.t('settings.cleanupFailed')) : ls.t('settings.cleanupFailed')
    ElMessage.error(msg)
  } finally {
    cleanupLoading.value = false
  }
}

async function handleReloadConfig() {
  reloadLoading.value = true
  try {
    const res = await reloadPlatformConfig()
    const results = res?.results || {}
    const mqtt = results.mqtt
    if (mqtt === 'reconnected') {
      ElMessage.success(ls.t('settings.mqttReconnected'))
    } else if (mqtt === 'not_running') {
      ElMessage.success(ls.t('settings.mqttNotRunning'))
    } else if (mqtt === 'reconnect_failed') {
      ElMessage.warning(ls.t('settings.mqttReconnectFailed'))
    } else {
      ElMessage.success(ls.t('settings.configApplied'))
    }
    fetchMqttStatus()
  } catch {
    ElMessage.error(ls.t('settings.applyFailed'))
  } finally {
    reloadLoading.value = false
  }
}

// ==================== 初始化 ====================
onMounted(() => {
  fetchMqttStatus()
  fetchPlatformConfigs()
})
</script>

<style scoped>
.section-title {
  font-weight: 600;
  font-size: var(--iot-font-size-md);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--iot-spacing-sm);
}

.setting-item {
  display: flex;
  align-items: center;
  padding: var(--iot-spacing-sm) 0;
  border-bottom: 1px solid var(--iot-border-color-light);
}

.setting-item:last-child {
  border-bottom: none;
}

.setting-label {
  width: 140px;
  color: var(--iot-text-secondary);
  font-size: var(--iot-font-size-sm);
  flex-shrink: 0;
}

.setting-value {
  color: var(--iot-text-primary);
  font-family: 'Courier New', monospace;
}

.config-value {
  font-family: 'Courier New', monospace;
  font-size: var(--iot-font-size-sm);
  word-break: break-all;
}

.config-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--iot-spacing-sm);
}

.empty-hint {
  padding: var(--iot-spacing-lg) 0;
}

.command-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--iot-spacing-md) 0;
  border-bottom: 1px solid var(--iot-border-color-light);
}

.command-item:last-child {
  border-bottom: none;
}

.command-item__info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.command-item__name {
  font-weight: 500;
  color: var(--iot-text-primary);
}

.command-item__desc {
  font-size: var(--iot-font-size-sm);
  color: var(--iot-text-secondary);
}
</style>
