import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

// 支持的配色方案: 'claude' | 'classic'
// 亮暗模式: 'light' | 'dark'

export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)
  const theme = ref(localStorage.getItem('iot-theme') || 'light')
  const colorTheme = ref(localStorage.getItem('iot-color-theme') || 'claude')
  const sidebarDrawerVisible = ref(false)

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function toggleTheme() {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
  }

  function setTheme(newTheme) {
    theme.value = newTheme
  }

  function setColorTheme(name) {
    colorTheme.value = name
    localStorage.setItem('iot-color-theme', name)
    applyTheme()
  }

  function applyTheme() {
    const root = document.documentElement
    // 亮暗模式
    if (theme.value === 'dark') {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }
    localStorage.setItem('iot-theme', theme.value)

    // 配色方案
    root.classList.remove('theme-classic', 'theme-claude')
    if (colorTheme.value !== 'claude') {
      root.classList.add(`theme-${colorTheme.value}`)
    }
  }

  watch(theme, () => { applyTheme() }, { immediate: true })
  watch(colorTheme, () => { applyTheme() }, { immediate: false })

  return {
    sidebarCollapsed,
    theme,
    colorTheme,
    sidebarDrawerVisible,
    toggleSidebar,
    toggleTheme,
    setTheme,
    setColorTheme,
    applyTheme,
  }
})
