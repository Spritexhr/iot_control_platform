<template>
  <div class="app-sidebar" :class="{ 'app-sidebar--collapsed': collapsed }">
    <!-- Logo 区域 -->
    <div class="app-sidebar__logo">
      <div class="logo-icon">
        <svg viewBox="0 0 32 32" width="28" height="28" fill="none">
          <rect width="32" height="32" rx="8" fill="currentColor" opacity="0.15"/>
          <circle cx="16" cy="13" r="4" stroke="currentColor" stroke-width="2" fill="none"/>
          <path d="M8 25c0-4.4 3.6-8 8-8s8 3.6 8 8" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/>
          <circle cx="24" cy="8" r="3" fill="currentColor" opacity="0.6"/>
          <line x1="24" y1="5" x2="24" y2="3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          <line x1="27" y1="8" x2="29" y2="8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
      </div>
      <transition name="fade">
        <span v-show="!collapsed" class="logo-text">IoT 控制平台</span>
      </transition>
    </div>

    <!-- 导航菜单 -->
    <el-menu
      :default-active="activeMenu"
      :collapse="collapsed"
      :collapse-transition="false"
      router
      class="app-sidebar__menu"
    >
      <el-menu-item index="/">
        <el-icon><Odometer /></el-icon>
        <template #title>仪表盘</template>
      </el-menu-item>

      <el-menu-item index="/sensors">
        <el-icon><Cpu /></el-icon>
        <template #title>传感器管理</template>
      </el-menu-item>

      <el-menu-item index="/devices">
        <el-icon><Monitor /></el-icon>
        <template #title>设备管理</template>
      </el-menu-item>

      <el-menu-item index="/automation">
        <el-icon><SetUp /></el-icon>
        <template #title>自动化规则</template>
      </el-menu-item>

      <el-menu-item index="/settings">
        <el-icon><Setting /></el-icon>
        <template #title>系统设置</template>
      </el-menu-item>
    </el-menu>

    <!-- 底部折叠按钮 -->
    <div class="app-sidebar__footer">
      <div class="collapse-btn" @click="$emit('toggle')">
        <el-icon :size="18">
          <Fold v-if="!collapsed" />
          <Expand v-else />
        </el-icon>
        <transition name="fade">
          <span v-show="!collapsed" class="collapse-text">收起菜单</span>
        </transition>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  Odometer,
  Cpu,
  Monitor,
  SetUp,
  Setting,
  Fold,
  Expand,
} from '@element-plus/icons-vue'

defineProps({
  collapsed: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['toggle'])

const route = useRoute()

const activeMenu = computed(() => {
  return route.path === '/' ? '/' : '/' + route.path.split('/')[1]
})
</script>

<style scoped>
.app-sidebar {
  width: var(--iot-sidebar-width);
  height: 100vh;
  background: var(--iot-bg-sidebar);
  display: flex;
  flex-direction: column;
  transition: width var(--iot-transition-base);
  overflow: hidden;
  position: fixed;
  left: 0;
  top: 0;
  z-index: 1001;
}

.app-sidebar--collapsed {
  width: var(--iot-sidebar-collapsed-width);
}

/* Logo */
.app-sidebar__logo {
  height: var(--iot-header-height);
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  flex-shrink: 0;
  overflow: hidden;
}

.logo-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--iot-color-primary);
  flex-shrink: 0;
}

.logo-text {
  font-size: 15px;
  font-weight: 600;
  color: #FFFFFF;
  white-space: nowrap;
}

/* 菜单 */
.app-sidebar__menu {
  flex: 1;
  border-right: none !important;
  background: transparent !important;
  padding: 8px 0;
  overflow-y: auto;
  overflow-x: hidden;
}

/* 覆盖 Element Plus Menu 样式 */
.app-sidebar__menu :deep(.el-menu) {
  background: transparent !important;
  border-right: none !important;
}

.app-sidebar__menu :deep(.el-menu-item) {
  height: 44px;
  line-height: 44px;
  margin: 2px 8px;
  border-radius: var(--iot-radius-base);
  color: var(--iot-sidebar-text);
  transition: all var(--iot-transition-fast);
}

.app-sidebar__menu :deep(.el-menu-item:hover) {
  background: var(--iot-sidebar-item-hover);
  color: var(--iot-sidebar-text-active);
}

.app-sidebar__menu :deep(.el-menu-item.is-active) {
  background: var(--iot-sidebar-item-active);
  color: var(--iot-sidebar-text-active);
  font-weight: 500;
}

.app-sidebar__menu :deep(.el-menu-item .el-icon) {
  font-size: 18px;
  margin-right: 8px;
}

.app-sidebar__menu :deep(.el-menu--collapse .el-menu-item) {
  margin: 2px 8px;
  padding: 0 !important;
  justify-content: center;
}

.app-sidebar__menu :deep(.el-menu--collapse .el-menu-item .el-icon) {
  margin-right: 0;
}

/* 底部折叠按钮 */
.app-sidebar__footer {
  padding: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  flex-shrink: 0;
}

.collapse-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: var(--iot-radius-base);
  color: var(--iot-sidebar-text);
  cursor: pointer;
  transition: all var(--iot-transition-fast);
  overflow: hidden;
}

.collapse-btn:hover {
  background: var(--iot-sidebar-item-hover);
  color: var(--iot-sidebar-text-active);
}

.collapse-text {
  font-size: 13px;
  white-space: nowrap;
}

/* Fade 过渡 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
