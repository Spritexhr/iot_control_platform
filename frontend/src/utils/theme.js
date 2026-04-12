/**
 * 初始化主题（在 Vue 挂载前调用，防止白屏闪烁）
 */
export function initTheme() {
  const root = document.documentElement

  // 亮暗模式
  const savedTheme = localStorage.getItem('iot-theme')
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  const theme = savedTheme || (prefersDark ? 'dark' : 'light')
  if (theme === 'dark') {
    root.classList.add('dark')
  } else {
    root.classList.remove('dark')
  }
  if (!savedTheme) {
    localStorage.setItem('iot-theme', theme)
  }

  // 配色方案
  const colorTheme = localStorage.getItem('iot-color-theme') || 'claude'
  root.classList.remove('theme-classic', 'theme-claude')
  if (colorTheme !== 'claude') {
    root.classList.add(`theme-${colorTheme}`)
  }
}
