<template>
  <el-container class="app-container">
    <el-header class="app-header">
      <div class="header-content">
        <div class="header-left">
          <el-button
            v-if="userStore.isLoggedIn"
            @click="toggleSidebar"
            class="sidebar-toggle"
            circle
            plain
          >
            <el-icon><Menu /></el-icon>
          </el-button>
          <h1>生草系统</h1>
        </div>
        <div class="user-info" v-if="userStore.isLoggedIn">
          <el-tag type="success">{{ userStore.userInfo?.name || userStore.userInfo?.qq }}</el-tag>
          <el-button @click="logout" text>
            <el-icon><SwitchButton /></el-icon>
            <span class="logout-text">退出</span>
          </el-button>
        </div>
      </div>
    </el-header>
    <el-container class="app-body">
      <el-aside
        v-if="userStore.isLoggedIn"
        class="app-sidebar"
        :class="{ 'sidebar-collapsed': isSidebarCollapsed }"
      >
        <el-menu
          :default-active="activeMenu"
          class="sidebar-menu"
          :collapse="isSidebarCollapsed"
          @select="handleMenuSelect"
        >
          <el-menu-item index="warehouse">
            <el-icon><House /></el-icon>
            <template #title>仓库</template>
          </el-menu-item>
          <el-menu-item index="ability">
            <el-icon><Star /></el-icon>
            <template #title>能力</template>
          </el-menu-item>
          <el-menu-item index="farm">
            <el-icon><TrendCharts /></el-icon>
            <template #title>生草</template>
          </el-menu-item>
          <el-menu-item index="shop">
            <el-icon><ShoppingCart /></el-icon>
            <template #title>商店</template>
          </el-menu-item>
          <el-menu-item index="gmarket">
            <el-icon><DataLine /></el-icon>
            <template #title>G市</template>
          </el-menu-item>
          <el-menu-item index="statistics">
            <el-icon><PieChart /></el-icon>
            <template #title>统计</template>
          </el-menu-item>
          <el-menu-item index="lottery">
            <el-icon><Present /></el-icon>
            <template #title>抽奖</template>
          </el-menu-item>
          <el-menu-item index="about">
            <el-icon><InfoFilled /></el-icon>
            <template #title>关于</template>
          </el-menu-item>
        </el-menu>
      </el-aside>
      <!-- 侧边栏遮罩层 -->
      <div
        v-if="userStore.isLoggedIn && !isSidebarCollapsed && windowWidth < 768"
        class="sidebar-overlay active"
        @click="toggleSidebar"
      ></div>
      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import { House, TrendCharts, ShoppingCart, DataLine, Star, PieChart, Present, Menu, SwitchButton, InfoFilled } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

// 侧边栏折叠状态
const isSidebarCollapsed = ref(false)
// 窗口宽度
const windowWidth = ref(window.innerWidth)

const activeMenu = computed(() => {
  const path = route.path
  if (path.startsWith('/warehouse')) return 'warehouse'
  if (path.startsWith('/farm')) return 'farm'
  if (path.startsWith('/shop')) return 'shop'
  if (path.startsWith('/gmarket')) return 'gmarket'
  if (path.startsWith('/statistics')) return 'statistics'
  if (path.startsWith('/lottery')) return 'lottery'
  if (path.startsWith('/ability')) return 'ability'
  if (path.startsWith('/about')) return 'about'
  return ''
})

// 切换侧边栏折叠状态
const toggleSidebar = () => {
  isSidebarCollapsed.value = !isSidebarCollapsed.value
}

const handleMenuSelect = (index: string) => {
  router.push(`/${index}`)
  // 在移动设备上，点击菜单后自动折叠侧边栏
  if (windowWidth.value < 768) {
    isSidebarCollapsed.value = true
  }
}

const logout = () => {
  userStore.logout()
  ElMessage.success('已退出登录')
  router.push('/login')
}

// 监听窗口大小变化，实现响应式布局
const handleResize = () => {
  windowWidth.value = window.innerWidth
  if (windowWidth.value < 768) {
    isSidebarCollapsed.value = true
  } else {
    isSidebarCollapsed.value = false
  }
}

onMounted(() => {
  handleResize()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})

watch(() => route.path, (newPath) => {
  if (!userStore.isLoggedIn && newPath !== '/login') {
    router.push('/login')
  }
})
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.app-header {
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  padding: 0 16px;
  height: 60px;
}

.header-content {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.sidebar-toggle {
  display: none;
}

.header-content h1 {
  margin: 0;
  font-size: 24px;
  color: #333;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logout-text {
  display: inline-block;
  margin-left: 4px;
}

.app-body {
  display: flex;
  height: calc(100vh - 60px);
}

.app-sidebar {
  width: 200px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
  transition: width 0.3s ease;
}

.app-sidebar.sidebar-collapsed {
  width: 64px;
}

.sidebar-menu {
  border: none;
  height: 100%;
}

.sidebar-menu .el-menu-item {
  font-size: 16px;
  height: 50px;
  line-height: 50px;
}

.app-main {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

/* 响应式布局 */
@media screen and (max-width: 768px) {
  .sidebar-toggle {
    display: inline-block;
  }
  
  .header-content h1 {
    font-size: 20px;
  }
  
  .app-sidebar {
    position: fixed;
    left: 0;
    top: 60px;
    height: calc(100vh - 60px);
    z-index: 1000;
    width: 200px;
    box-shadow: 2px 0 10px rgba(0, 0, 0, 0.15);
    transform: translateX(0);
    transition: transform 0.3s ease;
  }
  
  .app-sidebar.sidebar-collapsed {
    transform: translateX(-100%);
    width: 200px;
  }
  
  .app-main {
    padding: 16px;
  }
  
  .logout-text {
    display: none;
  }
  
  .user-info {
    gap: 8px;
  }
  
  /* 添加侧边栏遮罩层 */
  .sidebar-overlay {
    position: fixed;
    top: 60px;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.5);
    z-index: 999;
    opacity: 0;
    visibility: hidden;
    transition: opacity 0.3s ease, visibility 0.3s ease;
  }
  
  .sidebar-overlay.active {
    opacity: 1;
    visibility: visible;
  }
}

@media screen and (max-width: 480px) {
  .app-header {
    padding: 0 12px;
  }
  
  .header-content h1 {
    font-size: 18px;
  }
  
  .app-main {
    padding: 12px;
  }
  
  .user-info {
    gap: 4px;
  }
  
  .el-tag {
    font-size: 12px;
    padding: 0 8px;
  }
}
</style>

<style>
/* 全局响应式样式 - 小屏幕下el-descriptions改为单栏布局 */
@media screen and (max-width: 600px) {
  .el-descriptions {
    --el-descriptions-column: 1 !important;
  }
  
  .el-descriptions__body .el-descriptions__table {
    table-layout: fixed;
    width: 100%;
  }
  
  .el-descriptions__body .el-descriptions__table colgroup {
    display: none;
  }
  
  .el-descriptions__body .el-descriptions__table tbody {
    display: block;
  }
  
  .el-descriptions__body .el-descriptions__table tr {
    display: block;
    margin-bottom: 8px;
    border: 1px solid var(--el-border-color-lighter);
    border-radius: var(--el-border-radius-base);
    overflow: hidden;
  }
  
  .el-descriptions__body .el-descriptions__table td {
    display: block;
    width: 100% !important;
  }
  
  .el-descriptions__body .el-descriptions__table th {
    display: block;
    width: 100% !important;
    background-color: var(--el-fill-color-light);
    border-bottom: 1px solid var(--el-border-color-lighter);
  }
}

/* 修复弹窗打开时页面宽度变化问题 */
html {
  overflow-y: scroll;
}

body {
  overflow-y: scroll !important;
}

body.el-popup-parent--hidden {
  overflow-y: scroll !important;
  padding-right: 0 !important;
}
</style>
