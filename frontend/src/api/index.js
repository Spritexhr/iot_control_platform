import axios from 'axios'
import { ElMessage } from 'element-plus'
import { staticT } from '@/stores/locale'

const request = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 主动 refresh 阈值：access token 距离过期不足 30s 就提前换
const ACCESS_REFRESH_BUFFER_SECONDS = 30

// 解析 JWT 拿到 exp 秒（解析失败返回 null）
function decodeJwtExp(token) {
  try {
    const payload = token.split('.')[1]
    if (!payload) return null
    const json = atob(payload.replace(/-/g, '+').replace(/_/g, '/'))
    const data = JSON.parse(json)
    return typeof data.exp === 'number' ? data.exp : null
  } catch {
    return null
  }
}

function accessTokenAboutToExpire(token) {
  const exp = decodeJwtExp(token)
  if (exp === null) return false
  const now = Math.floor(Date.now() / 1000)
  return exp - now <= ACCESS_REFRESH_BUFFER_SECONDS
}

// 主动 refresh，刷新成功返回新 access token
async function refreshAccessToken() {
  const refreshToken = localStorage.getItem('iot-refresh-token')
  if (!refreshToken) return null
  try {
    const { data } = await axios.post('/api/auth/refresh/', { refresh: refreshToken })
    localStorage.setItem('iot-access-token', data.access)
    if (data.refresh) {
      localStorage.setItem('iot-refresh-token', data.refresh)
    }
    return data.access
  } catch {
    return null
  }
}

// ==================== 请求拦截器：自动携带 JWT Token + 主动续期 ====================
let proactiveRefreshing = null
request.interceptors.request.use(
  async (config) => {
    let token = localStorage.getItem('iot-access-token')

    // 不对 login / refresh 请求做主动续期，避免循环
    const url = config.url || ''
    const skipRefresh = url.includes('/auth/login') || url.includes('/auth/refresh')

    if (token && !skipRefresh && accessTokenAboutToExpire(token)) {
      // 多个并发请求共享同一个 refresh promise，避免重复刷新
      if (!proactiveRefreshing) {
        proactiveRefreshing = refreshAccessToken().finally(() => {
          proactiveRefreshing = null
        })
      }
      const newToken = await proactiveRefreshing
      if (newToken) token = newToken
    }

    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// ==================== 响应拦截器：统一错误处理 + Token 过期自动刷新 ====================
let isRefreshing = false
let pendingRequests = []

function onRefreshed(newToken) {
  pendingRequests.forEach((cb) => cb(newToken))
  pendingRequests = []
}

request.interceptors.response.use(
  (response) => response.data,
  async (error) => {
    const originalRequest = error.config

    // 401 且不是登录/刷新请求 → 尝试刷新 Token
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url.includes('/auth/login') &&
      !originalRequest.url.includes('/auth/refresh')
    ) {
      const refreshToken = localStorage.getItem('iot-refresh-token')
      if (!refreshToken) {
        redirectToLogin()
        return Promise.reject(error)
      }

      if (isRefreshing) {
        // 如果已在刷新中，排队等待
        return new Promise((resolve) => {
          pendingRequests.push((newToken) => {
            originalRequest.headers.Authorization = `Bearer ${newToken}`
            resolve(request(originalRequest))
          })
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const { data } = await axios.post('/api/auth/refresh/', { refresh: refreshToken })
        const newAccess = data.access
        localStorage.setItem('iot-access-token', newAccess)
        if (data.refresh) {
          localStorage.setItem('iot-refresh-token', data.refresh)
        }
        originalRequest.headers.Authorization = `Bearer ${newAccess}`
        onRefreshed(newAccess)
        return request(originalRequest)
      } catch {
        redirectToLogin()
        return Promise.reject(error)
      } finally {
        isRefreshing = false
      }
    }

    // 其他错误
    const message = error.response?.data?.detail || error.message || staticT('api.requestFailed')
    console.error('[API Error]', message)
    return Promise.reject(error)
  },
)

function redirectToLogin() {
  localStorage.removeItem('iot-access-token')
  localStorage.removeItem('iot-refresh-token')
  // 如果当前不在登录页，则跳转
  if (window.location.pathname !== '/login') {
    ElMessage.warning(staticT('api.sessionExpired'))
    window.location.href = '/login'
  }
}

export default request
