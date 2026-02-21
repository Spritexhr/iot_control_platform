import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi, getUserProfile } from '@/api/auth'

const TOKEN_KEY = 'iot-access-token'
const REFRESH_KEY = 'iot-refresh-token'

export const useUserStore = defineStore('user', () => {
  // ==================== 状态 ====================
  const accessToken = ref(localStorage.getItem(TOKEN_KEY) || '')
  const refreshToken = ref(localStorage.getItem(REFRESH_KEY) || '')
  const userInfo = ref(null)

  // ==================== 计算属性 ====================
  const isLoggedIn = computed(() => !!accessToken.value)
  const username = computed(() => userInfo.value?.username || '')

  // ==================== 操作 ====================

  /**
   * 用户登录
   * @param {{ username: string, password: string }} credentials
   */
  async function login(credentials) {
    const data = await loginApi(credentials)
    accessToken.value = data.access
    refreshToken.value = data.refresh
    localStorage.setItem(TOKEN_KEY, data.access)
    localStorage.setItem(REFRESH_KEY, data.refresh)
    // 登录成功后获取用户信息
    await fetchUserInfo()
  }

  /** 获取当前用户信息 */
  async function fetchUserInfo() {
    try {
      const data = await getUserProfile()
      userInfo.value = data
    } catch {
      // Token 无效则清除登录状态
      logout()
    }
  }

  /** 更新 Token（用于刷新场景） */
  function setTokens(access, refresh) {
    accessToken.value = access
    if (refresh) {
      refreshToken.value = refresh
      localStorage.setItem(REFRESH_KEY, refresh)
    }
    localStorage.setItem(TOKEN_KEY, access)
  }

  /** 退出登录 */
  function logout() {
    accessToken.value = ''
    refreshToken.value = ''
    userInfo.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_KEY)
  }

  return {
    accessToken,
    refreshToken,
    userInfo,
    isLoggedIn,
    username,
    login,
    fetchUserInfo,
    setTokens,
    logout,
  }
})
