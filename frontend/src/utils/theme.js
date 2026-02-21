/**
 * 初始化主题（在 Vue 挂载前调用，防止白屏闪烁）
 */
export function initTheme() {
  const saved = localStorage.getItem('iot-theme')
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  const theme = saved || (prefersDark ? 'dark' : 'light')

  if (theme === 'dark') {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }

  if (!saved) {
    localStorage.setItem('iot-theme', theme)
  }
}
