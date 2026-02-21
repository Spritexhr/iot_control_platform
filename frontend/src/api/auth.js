import request from './index'

/** 用户登录 —— 获取 JWT Token */
export function login(data) {
  return request.post('/auth/login/', data)
}

/** 刷新 Access Token */
export function refreshToken(refreshToken) {
  return request.post('/auth/refresh/', { refresh: refreshToken })
}

/** 用户注册 */
export function register(data) {
  return request.post('/auth/register/', data)
}

/** 获取当前用户信息 */
export function getUserProfile() {
  return request.get('/auth/profile/')
}

/** 更新当前用户信息 */
export function updateUserProfile(data) {
  return request.put('/auth/profile/', data)
}

/** 修改密码 */
export function changePassword(data) {
  return request.post('/auth/change-password/', data)
}
