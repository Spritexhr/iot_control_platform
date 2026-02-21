<template>
  <div class="app-layout">
    <!-- 侧边栏 - 桌面端 -->
    <AppSidebar
      v-if="!isMobile"
      :collapsed="appStore.sidebarCollapsed"
      @toggle="appStore.toggleSidebar()"
    />

    <!-- 侧边栏 - 移动端抽屉 -->
    <el-drawer
      v-model="appStore.sidebarDrawerVisible"
      direction="ltr"
      :size="220"
      :show-close="false"
      :with-header="false"
      class="mobile-sidebar-drawer"
    >
      <AppSidebar
        :collapsed="false"
        @toggle="appStore.sidebarDrawerVisible = false"
      />
    </el-drawer>

    <!-- 右侧内容区 -->
    <div
      class="app-layout__content"
      :style="contentStyle"
    >
      <AppHeader @toggle-drawer="appStore.sidebarDrawerVisible = true" />
      <AppMain />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '@/stores/app'
import AppSidebar from './AppSidebar.vue'
import AppHeader from './AppHeader.vue'
import AppMain from './AppMain.vue'

const appStore = useAppStore()
const windowWidth = ref(window.innerWidth)

const isMobile = computed(() => windowWidth.value < 768)

const contentStyle = computed(() => {
  if (isMobile.value) {
    return { marginLeft: '0px' }
  }
  const width = appStore.sidebarCollapsed
    ? 'var(--iot-sidebar-collapsed-width)'
    : 'var(--iot-sidebar-width)'
  return { marginLeft: width }
})

function onResize() {
  windowWidth.value = window.innerWidth
  // 中等屏幕自动折叠
  if (windowWidth.value < 1200 && windowWidth.value >= 768) {
    appStore.sidebarCollapsed = true
  }
}

onMounted(() => {
  window.addEventListener('resize', onResize)
  onResize()
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
})
</script>

<style scoped>
.app-layout {
  min-height: 100vh;
}

.app-layout__content {
  transition: margin-left var(--iot-transition-base);
  min-height: 100vh;
}

/* 移动端抽屉内侧边栏样式修正 */
:deep(.mobile-sidebar-drawer .el-drawer__body) {
  padding: 0;
}
</style>
