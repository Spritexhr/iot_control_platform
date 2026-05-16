import { onScopeDispose, ref } from 'vue'

/**
 * 通用 EventSource 封装。
 *
 * @param {string} url             SSE 端点 URL
 * @param {Object} handlers        事件类型 → 回调 { snapshot, sample, alert, ... }
 * @param {Object} options
 * @param {boolean} options.autoStart 是否立即连接,默认 true
 * @param {number}  options.retryDelay 断开后重连延迟(ms),默认 3000
 * @param {number}  options.transientMs error/connecting 持续多久才显示给 UI,默认 2000
 *
 * 返回:
 * - status:        原始状态 (idle/connecting/open/closed/error)，即时变化
 * - displayStatus: UI 显示用的防抖状态。open 立刻显示；error/connecting 必须持续超过
 *                  transientMs 才显示——避免浏览器内置自动重连的瞬时抖动让用户感觉
 *                  SSE 一直异常。
 */
export function useSSE(
  url,
  handlers = {},
  { autoStart = true, retryDelay = 3000, transientMs = 2000 } = {},
) {
  const status = ref('idle') // idle | connecting | open | closed | error
  const displayStatus = ref('idle')
  let source = null
  let retryTimer = null
  let transientTimer = null

  function setStatus(next) {
    status.value = next
    if (transientTimer) {
      clearTimeout(transientTimer)
      transientTimer = null
    }
    if (next === 'open' || next === 'idle' || next === 'closed') {
      displayStatus.value = next
      return
    }
    // error / connecting：等 transientMs 之后再写到 displayStatus；
    // 若期间被 open 抢先就不会闪
    transientTimer = setTimeout(() => {
      transientTimer = null
      if (status.value === next) {
        displayStatus.value = next
      }
    }, transientMs)
  }

  function cleanup() {
    // 内部清理：仅关闭旧 source / 计时器，**不写状态**。
    // 避免重连时 UI 闪一下"已断开"。
    if (retryTimer) {
      clearTimeout(retryTimer)
      retryTimer = null
    }
    if (transientTimer) {
      clearTimeout(transientTimer)
      transientTimer = null
    }
    if (source) {
      source.close()
      source = null
    }
  }

  function start() {
    cleanup()
    setStatus('connecting')
    try {
      source = new EventSource(url, { withCredentials: false })
    } catch (e) {
      setStatus('error')
      console.error('[SSE] 创建 EventSource 失败', e)
      scheduleRetry()
      return
    }

    source.onopen = () => {
      setStatus('open')
    }

    // 注册命名事件
    for (const [eventName, cb] of Object.entries(handlers)) {
      source.addEventListener(eventName, (e) => {
        let data = e.data
        try {
          data = JSON.parse(e.data)
        } catch (_) {
          /* 保留原始字符串 */
        }
        try {
          cb(data, e)
        } catch (err) {
          console.error(`[SSE] 处理器 ${eventName} 抛错`, err)
        }
      })
    }

    source.onerror = (e) => {
      // 浏览器自动重连期间也会触发 onerror（此时 readyState=CONNECTING），
      // 不能把它当成真正的异常 —— 否则状态会被一直钉在 error。
      if (!source) return
      if (source.readyState === EventSource.CONNECTING) {
        setStatus('connecting')
      } else if (source.readyState === EventSource.CLOSED) {
        setStatus('error')
        console.warn('[SSE] 连接被关闭,准备重连', e)
        scheduleRetry()
      }
    }
  }

  function stop() {
    cleanup()
    setStatus('closed')
  }

  function scheduleRetry() {
    if (retryTimer) return
    retryTimer = setTimeout(() => {
      retryTimer = null
      start()
    }, retryDelay)
  }

  if (autoStart) start()
  onScopeDispose(stop)

  return { status, displayStatus, start, stop }
}
