import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export const useAppStore = defineStore('app', () => {
  // 侧边栏折叠状态
  const sidebarCollapsed = ref(false)

  // 主题：'light' | 'dark'
  const theme = ref(localStorage.getItem('iot-theme') || 'light')

  // 移动端侧边栏抽屉
  const sidebarDrawerVisible = ref(false)

  /**
   * 切换侧边栏折叠
   */
  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  /**
   * 切换主题
   */
  function toggleTheme() {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
  }

  /**
   * 设置主题
   */
  function setTheme(newTheme) {
    theme.value = newTheme
  }

  /**
   * 将主题同步到 HTML 根元素
   */
  function applyTheme() {
    const root = document.documentElement
    if (theme.value === 'dark') {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }
    localStorage.setItem('iot-theme', theme.value)
  }

  // 监听主题变化自动应用
  watch(theme, () => {
    applyTheme()
  }, { immediate: true })

  return {
    sidebarCollapsed,
    theme,
    sidebarDrawerVisible,
    toggleSidebar,
    toggleTheme,
    setTheme,
    applyTheme,
  }
})
