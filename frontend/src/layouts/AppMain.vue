<template>
  <main class="app-main">
    <router-view v-slot="{ Component }">
      <transition name="fade-transform" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </main>
</template>

<script setup>
</script>

<style scoped>
.app-main {
  padding: var(--iot-spacing-lg);
  min-height: calc(100vh - var(--iot-header-height));
  transition: padding var(--iot-transition-base);
}

@media (max-width: 767px) {
  .app-main {
    padding: var(--iot-spacing-md);
  }
}
</style>
