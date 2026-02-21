import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ==================== 请求拦截器：自动携带 JWT Token ====================
request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('iot-access-token')
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
    const message = error.response?.data?.detail || error.message || '请求失败'
    console.error('[API Error]', message)
    return Promise.reject(error)
  },
)

function redirectToLogin() {
  localStorage.removeItem('iot-access-token')
  localStorage.removeItem('iot-refresh-token')
  // 如果当前不在登录页，则跳转
  if (window.location.pathname !== '/login') {
    ElMessage.warning('登录已过期，请重新登录')
    window.location.href = '/login'
  }
}

export default request
