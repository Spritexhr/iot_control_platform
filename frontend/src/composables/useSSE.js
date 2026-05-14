import { onScopeDispose, ref } from 'vue'

/**
 * 通用 EventSource 封装。
 *
 * @param {string} url             SSE 端点 URL
 * @param {Object} handlers        事件类型 → 回调 { snapshot, sample, alert, ... }
 * @param {Object} options
 * @param {boolean} options.autoStart 是否立即连接,默认 true
 * @param {number}  options.retryDelay 断开后重连延迟(ms),默认 3000
 *
 * 用法:
 *   const { status, start, stop } = useSSE('/api/plugins/eb_plant/stream', {
 *     snapshot: (data) => store.applySnapshot(data),
 *     sample:   (data) => store.applySample(data),
 *   })
 */
export function useSSE(url, handlers = {}, { autoStart = true, retryDelay = 3000 } = {}) {
  const status = ref('idle') // idle | connecting | open | closed | error
  let source = null
  let retryTimer = null

  function start() {
    stop()
    status.value = 'connecting'
    try {
      source = new EventSource(url, { withCredentials: false })
    } catch (e) {
      status.value = 'error'
      console.error('[SSE] 创建 EventSource 失败', e)
      scheduleRetry()
      return
    }

    source.onopen = () => {
      status.value = 'open'
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
      status.value = 'error'
      console.warn('[SSE] 连接异常,准备重连', e)
      // EventSource 会自动重连,但若被服务器主动关闭,需要手动重启
      if (source && source.readyState === EventSource.CLOSED) {
        scheduleRetry()
      }
    }
  }

  function stop() {
    if (retryTimer) {
      clearTimeout(retryTimer)
      retryTimer = null
    }
    if (source) {
      source.close()
      source = null
    }
    status.value = 'closed'
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

  return { status, start, stop }
}
