<template>
  <div class="auth-page">
    <div class="auth-card">
      <!-- Logo 区域 -->
      <div class="auth-header">
        <div class="auth-logo">
          <svg viewBox="0 0 40 40" width="40" height="40">
            <rect x="2" y="2" width="36" height="36" rx="8" fill="var(--iot-color-primary)" />
            <path d="M12 20h16M20 12v16M12 14l4 4-4 4M24 14l4 4-4 4" stroke="#fff" stroke-width="2"
              stroke-linecap="round" fill="none" />
          </svg>
        </div>
        <h1 class="auth-title">IoT 控制平台</h1>
        <p class="auth-subtitle">登录您的账号以继续</p>
      </div>

      <!-- 登录表单 -->
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        size="large"
        @submit.prevent="handleLogin"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
            :prefix-icon="User"
            clearable
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            :prefix-icon="Lock"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            :loading="loading"
            class="auth-submit-btn"
            @click="handleLogin"
          >
            登 录
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 底部链接 -->
      <div class="auth-footer">
        <span>还没有账号？</span>
        <router-link to="/register" class="auth-link">立即注册</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleLogin() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await userStore.login({
      username: form.username,
      password: form.password,
    })
    ElMessage.success('登录成功')
    const redirect = router.currentRoute.value.query.redirect || '/'
    router.push(redirect)
  } catch (error) {
    const detail = error.response?.data?.detail
    ElMessage.error(detail || '登录失败，请检查用户名和密码')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: var(--iot-spacing-lg);
}

.auth-card {
  width: 100%;
  max-width: 420px;
  background: var(--iot-bg-card);
  border-radius: var(--iot-radius-xl);
  padding: 40px 36px;
  box-shadow: var(--iot-shadow-lg);
}

.auth-header {
  text-align: center;
  margin-bottom: 32px;
}

.auth-logo {
  display: flex;
  justify-content: center;
  margin-bottom: 16px;
}

.auth-title {
  font-size: var(--iot-font-size-xl);
  font-weight: 700;
  color: var(--iot-text-primary);
  margin: 0 0 8px;
}

.auth-subtitle {
  font-size: var(--iot-font-size-base);
  color: var(--iot-text-secondary);
  margin: 0;
}

.auth-submit-btn {
  width: 100%;
  height: 44px;
  font-size: var(--iot-font-size-md);
  border-radius: var(--iot-radius-base);
  margin-top: 8px;
}

.auth-footer {
  text-align: center;
  margin-top: 24px;
  font-size: var(--iot-font-size-sm);
  color: var(--iot-text-secondary);
}

.auth-link {
  color: var(--iot-color-primary);
  text-decoration: none;
  font-weight: 500;
  margin-left: 4px;
}

.auth-link:hover {
  text-decoration: underline;
}

/* 暗色主题适配 */
:global(html.dark) .auth-page {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
}
</style>
