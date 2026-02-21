<template>
  <div class="command-panel">
    <div v-if="!commandEntries.length" class="iot-text-secondary" style="text-align: center; padding: 12px;">
      暂无可用命令
    </div>
    <div v-for="entry in commandEntries" :key="entry.name" class="command-row">
      <div class="command-info">
        <span class="command-desc">{{ entry.info.description || entry.name }}</span>
      </div>
      <!-- 有参数的命令 -->
      <div v-if="entry.info.params && entry.info.params.length" class="command-params">
        <div v-for="param in entry.info.params" :key="param" class="param-input">
          <el-input
            v-model="paramValues[entry.name + '.' + param]"
            :placeholder="param"
            size="small"
            style="width: 120px"
          />
        </div>
      </div>
      <el-button
        type="primary"
        size="small"
        :loading="loadingMap[entry.name]"
        @click="handleSend(entry)"
      >
        {{ resultMap[entry.name] === true ? '已确认' : resultMap[entry.name] === false ? '失败' : '执行' }}
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  commands: { type: Object, default: () => ({}) },
  deviceId: { type: String, required: true },
  /** 发送命令的函数，签名: (deviceId, commandName, params, makeSure) => Promise */
  sendFn: { type: Function, required: true },
})

const emit = defineEmits(['command-sent', 'command-failed'])

const paramValues = ref({})
const loadingMap = ref({})
const resultMap = ref({})

const commandEntries = computed(() => {
  if (!props.commands || typeof props.commands !== 'object') return []
  return Object.entries(props.commands).map(([name, info]) => ({ name, info }))
})

// commands 变化时清空状态
watch(() => props.commands, () => {
  paramValues.value = {}
  loadingMap.value = {}
  resultMap.value = {}
})

async function handleSend(entry) {
  const cmdName = entry.name
  loadingMap.value[cmdName] = true
  resultMap.value[cmdName] = undefined

  // 收集参数
  const params = {}
  if (entry.info.params && entry.info.params.length) {
    for (const p of entry.info.params) {
      params[p] = paramValues.value[cmdName + '.' + p] || ''
    }
  }

  try {
    const res = await props.sendFn(props.deviceId, cmdName, params, false)
    if (res.success || res.data?.success) {
      resultMap.value[cmdName] = true
      emit('command-sent', { command: cmdName, params })
    } else {
      resultMap.value[cmdName] = false
      emit('command-failed', { command: cmdName })
    }
  } catch {
    resultMap.value[cmdName] = false
    emit('command-failed', { command: cmdName })
  } finally {
    loadingMap.value[cmdName] = false
    // 2 秒后恢复按钮文字
    setTimeout(() => {
      resultMap.value[cmdName] = undefined
    }, 2000)
  }
}
</script>

<style scoped>
.command-row {
  display: flex;
  align-items: center;
  gap: var(--iot-spacing-sm);
  padding: 8px 0;
  border-bottom: 1px solid var(--iot-border-color-lighter);
  flex-wrap: wrap;
}

.command-row:last-child {
  border-bottom: none;
}

.command-info {
  flex: 1;
  min-width: 100px;
}

.command-desc {
  font-size: var(--iot-font-size-sm);
  color: var(--iot-text-primary);
}

.command-params {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
</style>
