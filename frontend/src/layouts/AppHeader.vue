<template>
  <header class="app-header">
    <!-- 左侧：移动端汉堡按钮 + 面包屑 -->
    <div class="app-header__left">
      <el-icon
        class="mobile-menu-btn"
        :size="20"
        @click="$emit('toggle-drawer')"
      >
        <Operation />
      </el-icon>
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
        <el-breadcrumb-item v-if="currentTitle">
          {{ currentTitle }}
        </el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <!-- 右侧：MQTT 状态 + 主题切换 + 全屏 + 用户菜单 -->
    <div class="app-header__right">
      <!-- MQTT 状态 -->
      <div
        class="mqtt-status"
        :class="mqttConnected ? 'mqtt-status--online' : 'mqtt-status--offline'"
        :title="mqttConnected ? 'MQTT 已连接' : 'MQTT 未连接'"
      >
        <span
          class="iot-status-dot"
          :class="mqttConnected ? 'iot-status-dot--online' : 'iot-status-dot--offline'"
        ></span>
        <span class="mqtt-label">MQTT</span>
      </div>

      <!-- 主题切换 -->
      <el-tooltip :content="isDark ? '切换亮色模式' : '切换暗色模式'" placement="bottom">
        <button class="header-action-btn" @click="appStore.toggleTheme()">
          <el-icon :size="18">
            <Moon v-if="!isDark" />
            <Sunny v-else />
          </el-icon>
        </button>
      </el-tooltip>

      <!-- 全屏切换 -->
      <el-tooltip content="全屏" placement="bottom">
        <button class="header-action-btn" @click="toggleFullscreen">
          <el-icon :size="18"><FullScreen /></el-icon>
        </button>
      </el-tooltip>

      <!-- 用户下拉菜单 -->
      <el-dropdown trigger="click" @command="handleUserCommand">
        <button class="user-menu-btn">
          <el-avatar :size="28" class="user-avatar">
            {{ avatarText }}
          </el-avatar>
          <span class="user-name">{{ userStore.username || '用户' }}</span>
          <el-icon :size="12"><ArrowDown /></el-icon>
        </button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item disabled>
              <el-icon><User /></el-icon>
              {{ userStore.username }}
            </el-dropdown-item>
            <el-dropdown-item divided command="profile">
              <el-icon><Setting /></el-icon>
              个人信息
            </el-dropdown-item>
            <el-dropdown-item command="password">
              <el-icon><Lock /></el-icon>
              修改密码
            </el-dropdown-item>
            <el-dropdown-item divided command="logout">
              <el-icon><SwitchButton /></el-icon>
              退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <!-- 个人信息弹窗 -->
    <el-dialog v-model="profileDialogVisible" title="个人信息" width="460px" destroy-on-close>
      <el-form :model="profileForm" label-width="80px" size="default">
        <el-form-item label="用户名">
          <el-input :model-value="profileForm.username" disabled />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="profileForm.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="姓">
          <el-input v-model="profileForm.last_name" placeholder="请输入姓" />
        </el-form-item>
        <el-form-item label="名">
          <el-input v-model="profileForm.first_name" placeholder="请输入名" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="profileDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="profileLoading" @click="handleUpdateProfile">
          保存
        </el-button>
      </template>
    </el-dialog>

    <!-- 修改密码弹窗 -->
    <el-dialog v-model="passwordDialogVisible" title="修改密码" width="460px" destroy-on-close>
      <el-form ref="pwdFormRef" :model="passwordForm" :rules="passwordRules" label-width="100px" size="default">
        <el-form-item label="当前密码" prop="old_password">
          <el-input v-model="passwordForm.old_password" type="password" show-password placeholder="请输入当前密码" />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="passwordForm.new_password" type="password" show-password placeholder="请输入新密码（至少8位）" />
        </el-form-item>
        <el-form-item label="确认新密码" prop="new_password2">
          <el-input v-model="passwordForm.new_password2" type="password" show-password placeholder="请再次输入新密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="passwordLoading" @click="handleChangePassword">
          确认修改
        </el-button>
      </template>
    </el-dialog>
  </header>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useUserStore } from '@/stores/user'
import {
  Operation, Moon, Sunny, FullScreen, ArrowDown,
  User, Setting, Lock, SwitchButton,
} from '@element-plus/icons-vue'
import { getMqttStatus } from '@/api/system'
import { updateUserProfile, changePassword } from '@/api/auth'
import { ElMessage, ElMessageBox } from 'element-plus'

defineEmits(['toggle-drawer'])

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const userStore = useUserStore()

const isDark = computed(() => appStore.theme === 'dark')
const currentTitle = computed(() => route.meta.title || '')
const avatarText = computed(() => (userStore.username || 'U').charAt(0).toUpperCase())

// ==================== MQTT 状态轮询 ====================
const mqttConnected = ref(false)
let pollTimer = null

async function fetchMqttStatus() {
  try {
    const data = await getMqttStatus()
    mqttConnected.value = !!data.is_connected
  } catch {
    mqttConnected.value = false
  }
}

onMounted(() => {
  fetchMqttStatus()
  pollTimer = setInterval(fetchMqttStatus, 15000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

// ==================== 全屏 ====================
function toggleFullscreen() {
  if (document.fullscreenElement) {
    document.exitFullscreen()
  } else {
    document.documentElement.requestFullscreen()
  }
}

// ==================== 用户菜单命令 ====================
function handleUserCommand(command) {
  if (command === 'profile') {
    openProfileDialog()
  } else if (command === 'password') {
    openPasswordDialog()
  } else if (command === 'logout') {
    handleLogout()
  }
}

// ==================== 个人信息 ====================
const profileDialogVisible = ref(false)
const profileLoading = ref(false)
const profileForm = reactive({
  username: '',
  email: '',
  first_name: '',
  last_name: '',
})

function openProfileDialog() {
  const info = userStore.userInfo
  if (info) {
    profileForm.username = info.username
    profileForm.email = info.email || ''
    profileForm.first_name = info.first_name || ''
    profileForm.last_name = info.last_name || ''
  }
  profileDialogVisible.value = true
}

async function handleUpdateProfile() {
  profileLoading.value = true
  try {
    await updateUserProfile({
      email: profileForm.email,
      first_name: profileForm.first_name,
      last_name: profileForm.last_name,
    })
    await userStore.fetchUserInfo()
    ElMessage.success('信息更新成功')
    profileDialogVisible.value = false
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '更新失败')
  } finally {
    profileLoading.value = false
  }
}

// ==================== 修改密码 ====================
const passwordDialogVisible = ref(false)
const passwordLoading = ref(false)
const pwdFormRef = ref(null)
const passwordForm = reactive({
  old_password: '',
  new_password: '',
  new_password2: '',
})

const passwordRules = {
  old_password: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, message: '密码至少 8 个字符', trigger: 'blur' },
  ],
  new_password2: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== passwordForm.new_password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
}

function openPasswordDialog() {
  passwordForm.old_password = ''
  passwordForm.new_password = ''
  passwordForm.new_password2 = ''
  passwordDialogVisible.value = true
}

async function handleChangePassword() {
  const valid = await pwdFormRef.value.validate().catch(() => false)
  if (!valid) return

  passwordLoading.value = true
  try {
    await changePassword({
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password,
      new_password2: passwordForm.new_password2,
    })
    ElMessage.success('密码修改成功，请重新登录')
    passwordDialogVisible.value = false
    userStore.logout()
    router.push('/login')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '修改失败')
  } finally {
    passwordLoading.value = false
  }
}

// ==================== 退出登录 ====================
async function handleLogout() {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    userStore.logout()
    router.push('/login')
    ElMessage.success('已退出登录')
  } catch {
    // 取消退出
  }
}
</script>

<style scoped>
.app-header {
  height: var(--iot-header-height);
  background: var(--iot-bg-header);
  border-bottom: 1px solid var(--iot-border-color-light);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--iot-spacing-lg);
  position: sticky;
  top: 0;
  z-index: 999;
  transition: background-color var(--iot-transition-base);
}

.app-header__left {
  display: flex;
  align-items: center;
  gap: var(--iot-spacing-md);
}

.mobile-menu-btn {
  display: none;
  cursor: pointer;
  color: var(--iot-text-regular);
  padding: 4px;
  border-radius: var(--iot-radius-sm);
  transition: color var(--iot-transition-fast);
}

.mobile-menu-btn:hover {
  color: var(--iot-color-primary);
}

.app-header__right {
  display: flex;
  align-items: center;
  gap: var(--iot-spacing-sm);
}

/* MQTT 状态 */
.mqtt-status {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 12px;
  background: var(--iot-bg-page);
  font-size: var(--iot-font-size-xs);
  cursor: default;
}

.mqtt-label {
  font-weight: 500;
  transition: color var(--iot-transition-fast);
}

.mqtt-status--online .mqtt-label {
  color: var(--iot-color-success);
}

.mqtt-status--offline .mqtt-label {
  color: var(--iot-text-secondary);
}

/* 操作按钮 */
.header-action-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  border-radius: var(--iot-radius-base);
  color: var(--iot-text-regular);
  cursor: pointer;
  transition: all var(--iot-transition-fast);
}

.header-action-btn:hover {
  background: var(--iot-bg-page);
  color: var(--iot-color-primary);
}

/* 用户菜单按钮 */
.user-menu-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px 4px 4px;
  border: 1px solid var(--iot-border-color-light);
  background: transparent;
  border-radius: 20px;
  cursor: pointer;
  color: var(--iot-text-regular);
  transition: all var(--iot-transition-fast);
}

.user-menu-btn:hover {
  border-color: var(--iot-color-primary);
  color: var(--iot-color-primary);
}

.user-avatar {
  background-color: var(--iot-color-primary);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
}

.user-name {
  font-size: var(--iot-font-size-sm);
  font-weight: 500;
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 响应式：移动端 */
@media (max-width: 767px) {
  .mobile-menu-btn {
    display: flex;
  }

  .user-name {
    display: none;
  }
}
</style>
