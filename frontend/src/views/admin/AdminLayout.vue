<template>
  <div class="admin-layout">
    <el-card class="admin-card" shadow="never">
      <template #header>
        <div class="admin-header">
          <div class="admin-title">
            <el-icon><Setting /></el-icon>
            <span>管理后台</span>
          </div>
          <el-button circle size="default" style="width: 32px; height: 32px;" @click="handleRefresh">
            <el-icon><Refresh /></el-icon>
          </el-button>
        </div>
      </template>

      <el-tabs v-model="activeTab" class="admin-tabs">
        <el-tab-pane label="用户管理" name="users">
          <UserManage v-if="activeTab === 'users'" ref="userManageRef" />
        </el-tab-pane>
        <el-tab-pane label="数据看板" name="dashboard">
          <Dashboard v-if="activeTab === 'dashboard'" ref="dashboardRef" />
        </el-tab-pane>
        <el-tab-pane label="图片审核" name="pic-review">
          <PicReview v-if="activeTab === 'pic-review'" ref="picReviewRef" />
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { Refresh, Setting } from '@element-plus/icons-vue'
import { ref } from 'vue'
import Dashboard from './Dashboard.vue'
import PicReview from './PicReview.vue'
import UserManage from './UserManage.vue'

const activeTab = ref<'users' | 'dashboard' | 'pic-review'>('users')
const userManageRef = ref()
const dashboardRef = ref()
const picReviewRef = ref()

const handleRefresh = () => {
  const refMap: Record<string, typeof userManageRef> = {
    users: userManageRef,
    dashboard: dashboardRef,
    'pic-review': picReviewRef,
  }
  const currentRef = refMap[activeTab.value]
  if (currentRef.value?.refresh) {
    currentRef.value.refresh()
  }
}
</script>

<style scoped>
.admin-layout {
  max-width: 1000px;
  margin: 0 auto;
}

.admin-card {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.admin-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.admin-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.admin-tabs {
  min-height: 500px;
}

.admin-tabs :deep(.el-tabs__content) {
  padding-top: 12px;
}
</style>
