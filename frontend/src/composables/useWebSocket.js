import { onScopeDispose, ref } from 'vue'

const ACCESS_KEY = 'iot-access-token'
const REFRESH_KEY = 'iot-refresh-token'

/**
 * 通用 WebSocket 封装。
 *
 * 暴露 { status, displayStatus, start, stop, send }。
 * URL 通过函数注入，便于动态拼装；token 自动从 localStorage 读取并附到查询串
 * （浏览器 WebSocket 不支持自定义 Authorization header）。
 *
 * @param {() => string} buildUrl  返回 ws:// 或 wss:// 完整 URL（不含 token）
 * @param {Object} handlers        事件名 → 回调，对齐后端 send_json 的 {event, data}
 * @param {Object} options
 *   - autoStart: 是否立即连接，默认 true
 *   - heartbeatMs: 心跳间隔，默认 25000（发 {"action":"ping"}，后端回 pong）
 *   - retryBaseMs: 重连指数退避基数，默认 1000
 *   - retryMaxMs:  重连退避上限，默认 30000
 *   - transientMs: connecting/error 持续多久才显示给 UI，默认 2000
 *
 * 状态语义：
 *   idle | connecting | open | closed | error | unauthorized
 *   unauthorized 表示 token 失败且 refresh 也失败，由调用方决定跳登录
 */
export function useWebSocket(
  buildUrl,
  handlers = {},
  {
    autoStart = true,
    heartbeatMs = 25000,
    retryBaseMs = 1000,
    retryMaxMs = 30000,
    transientMs = 2000,
  } = {},
) {
  const status = ref('idle')
  const displayStatus = ref('idle')
  let ws = null
  let retryTimer = null
  let transientTimer = null
  let heartbeatTimer = null
  let retryDelay = retryBaseMs
  let manualClosed = false
  let unauthorizedRetry = 0

  function setStatus(next) {
    status.value = next
    if (transientTimer) {
      clearTimeout(transientTimer)
      transientTimer = null
    }
    if (next === 'open' || next === 'idle' || next === 'closed' || next === 'unauthorized') {
      displayStatus.value = next
      return
    }
    transientTimer = setTimeout(() => {
      transientTimer = null
      if (status.value === next) displayStatus.value = next
    }, transientMs)
  }

  function _withToken(rawUrl) {
    const token = localStorage.getItem(ACCESS_KEY) || ''
    if (!token) return rawUrl
    const sep = rawUrl.includes('?') ? '&' : '?'
    return `${rawUrl}${sep}token=${encodeURIComponent(token)}`
  }

  async function _refreshToken() {
    const refresh = localStorage.getItem(REFRESH_KEY)
    if (!refresh) return false
    try {
      const r = await fetch('/api/auth/refresh/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh }),
      })
      if (!r.ok) return false
      const data = await r.json()
      if (data.access) {
        localStorage.setItem(ACCESS_KEY, data.access)
        if (data.refresh) localStorage.setItem(REFRESH_KEY, data.refresh)
        return true
      }
      return false
    } catch (_) {
      return false
    }
  }

  function _cleanup() {
    if (retryTimer) {
      clearTimeout(retryTimer)
      retryTimer = null
    }
    if (transientTimer) {
      clearTimeout(transientTimer)
      transientTimer = null
    }
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
    if (ws) {
      try {
        ws.close()
      } catch (_) { /* ignore */ }
      ws = null
    }
  }

  function _scheduleRetry() {
    if (manualClosed || retryTimer) return
    retryTimer = setTimeout(() => {
      retryTimer = null
      start()
    }, retryDelay)
    retryDelay = Math.min(retryDelay * 2, retryMaxMs)
  }

  function start() {
    manualClosed = false
    _cleanup()
    setStatus('connecting')

    let socket
    try {
      socket = new WebSocket(_withToken(buildUrl()))
    } catch (e) {
      console.error('[WS] 创建 WebSocket 失败', e)
      setStatus('error')
      _scheduleRetry()
      return
    }
    ws = socket

    ws.onopen = () => {
      retryDelay = retryBaseMs
      unauthorizedRetry = 0
      setStatus('open')
      heartbeatTimer = setInterval(() => {
        try {
          ws?.readyState === WebSocket.OPEN && ws.send(JSON.stringify({ action: 'ping' }))
        } catch (_) { /* ignore */ }
      }, heartbeatMs)
    }

    ws.onmessage = (evt) => {
      let msg
      try {
        msg = JSON.parse(evt.data)
      } catch (_) {
        return
      }
      const ev = msg?.event || msg?.action
      if (ev === 'pong') return
      const cb = handlers[ev]
      if (cb) {
        try {
          cb(msg.data, msg)
        } catch (err) {
          console.error(`[WS] 处理器 ${ev} 抛错`, err)
        }
      }
    }

    ws.onerror = () => {
      // onclose 必然跟上，不在这里改状态避免重复触发
    }

    ws.onclose = async (evt) => {
      if (manualClosed) {
        setStatus('closed')
        return
      }
      // 4001 = token 无效/未认证；尝试 refresh 后重连，连续 2 次失败置 unauthorized
      if (evt.code === 4001 && unauthorizedRetry < 2) {
        unauthorizedRetry += 1
        const ok = await _refreshToken()
        if (ok) {
          start()
          return
        }
        setStatus('unauthorized')
        return
      }
      if (evt.code === 4001) {
        setStatus('unauthorized')
        return
      }
      setStatus('error')
      _scheduleRetry()
    }
  }

  function stop() {
    manualClosed = true
    _cleanup()
    setStatus('closed')
  }

  function send(payload) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(typeof payload === 'string' ? payload : JSON.stringify(payload))
    }
  }

  if (autoStart) start()
  onScopeDispose(stop)

  return { status, displayStatus, start, stop, send }
}

/** 根据当前 location 推导 ws:// 或 wss:// 完整 URL（含 host）。path 须以 / 开头。 */
export function buildWsUrl(path) {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${location.host}${path}`
}
