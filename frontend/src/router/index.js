import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'

const routes = [
  // ==================== 认证页面（无需登录） ====================
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/LoginView.vue'),
    meta: { title: '登录', guest: true },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/auth/RegisterView.vue'),
    meta: { title: '注册', guest: true },
  },

  // ==================== 业务页面（需要登录） ====================
  {
    path: '/',
    component: AppLayout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/DashboardView.vue'),
        meta: { title: '仪表盘' },
      },
      {
        path: 'sensors',
        name: 'Sensors',
        component: () => import('@/views/sensors/SensorsView.vue'),
        meta: { title: '传感器管理' },
      },
      {
        path: 'sensors/:sensorId',
        name: 'SensorDetail',
        component: () => import('@/views/sensors/SensorDetailView.vue'),
        meta: { title: '传感器详情' },
      },
      {
        path: 'devices',
        name: 'Devices',
        component: () => import('@/views/devices/DevicesView.vue'),
        meta: { title: '设备管理' },
      },
      {
        path: 'devices/:deviceId',
        name: 'DeviceDetail',
        component: () => import('@/views/devices/DeviceDetailView.vue'),
        meta: { title: '设备详情' },
      },
      {
        path: 'automation',
        name: 'Automation',
        component: () => import('@/views/automation/AutomationView.vue'),
        meta: { title: '自动化规则' },
      },
      {
        path: 'automation/:id',
        name: 'AutomationDetail',
        component: () => import('@/views/automation/AutomationDetailView.vue'),
        meta: { title: '规则详情' },
      },
      {
        path: 'plugins',
        name: 'Plugins',
        component: () => import('@/views/plugins/PluginsListView.vue'),
        meta: { title: '插件中心' },
      },
      {
        path: 'plugins/data_viz',
        name: 'PluginDataViz',
        component: () => import('@/views/plugins/DataVizView.vue'),
        meta: {
          title: '数据可视化',
          breadcrumb: [
            { title: '插件中心', to: '/plugins' },
            { title: '数据可视化' },
          ],
        },
      },
      {
        path: 'plugins/eb_plant',
        name: 'PluginEBPlant',
        component: () => import('@/views/plugins/eb_plant/EBPlantView.vue'),
        meta: {
          title: '全厂设备辅助监控大屏',
          breadcrumb: [
            { title: '插件中心', to: '/plugins' },
            { title: '全厂设备辅助监控大屏' },
          ],
        },
      },
      {
        path: 'plugins/eb_plant/config',
        name: 'PluginEBPlantConfig',
        component: () => import('@/views/plugins/eb_plant/EBPlantConfigView.vue'),
        meta: {
          title: '配置面板',
          breadcrumb: [
            { title: '插件中心', to: '/plugins' },
            { title: '全厂设备辅助监控大屏', to: '/plugins/eb_plant' },
            { title: '配置面板' },
          ],
        },
      },
      {
        path: 'plugins/plant_diagram',
        name: 'PluginPlantDiagramHome',
        component: () => import('@/views/plugins/plant_diagram/PlantDiagramListView.vue'),
        meta: {
          title: 'P&ID 画板',
          breadcrumb: [
            { title: '插件中心', to: '/plugins' },
            { title: '全厂设备辅助监控大屏', to: '/plugins/eb_plant' },
            { title: 'P&ID 画板' },
          ],
        },
      },
      {
        path: 'plugins/plant_diagram/list/:plantCode',
        name: 'PluginPlantDiagramList',
        component: () => import('@/views/plugins/plant_diagram/PlantDiagramListView.vue'),
        meta: {
          title: 'P&ID 画板列表',
          breadcrumb: [
            { title: '插件中心', to: '/plugins' },
            { title: '全厂设备辅助监控大屏', to: '/plugins/eb_plant' },
            { title: 'P&ID 画板', to: '/plugins/plant_diagram' },
          ],
        },
      },
      {
        path: 'plugins/plant_diagram/:id',
        name: 'PluginPlantDiagram',
        component: () => import('@/views/plugins/plant_diagram/PlantDiagramView.vue'),
        meta: {
          title: 'P&ID 画板',
          breadcrumb: [
            { title: '插件中心', to: '/plugins' },
            { title: '全厂设备辅助监控大屏', to: '/plugins/eb_plant' },
            { title: 'P&ID 画板', to: '/plugins/plant_diagram' },
            { title: '画板编辑' },
          ],
        },
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/settings/SettingsView.vue'),
        meta: { title: '系统设置' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// ==================== 路由守卫 ====================
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('iot-access-token')

  // 需要登录但未登录 → 跳转登录页
  if (to.matched.some((r) => r.meta.requiresAuth) && !token) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
    return
  }

  // 已登录却访问登录/注册页 → 跳转首页
  if (to.meta.guest && token) {
    next({ path: '/' })
    return
  }

  next()
})

// 路由后置守卫 - 更新页面标题
router.afterEach((to) => {
  document.title = to.meta.title
    ? `${to.meta.title} - IoT 控制平台`
    : 'IoT 控制平台'
})

export default router
