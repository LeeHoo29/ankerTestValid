<template>
  <el-container class="layout-container">
    <!-- 左侧菜单栏 -->
    <el-aside :width="isCollapse ? '64px' : '200px'" class="sidebar">
      <div class="logo-container">
        <el-icon class="logo-icon" :size="24">
          <Monitor />
        </el-icon>
        <span v-show="!isCollapse" class="logo-text">Task Dashboard</span>
      </div>
      
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapse"
        :unique-opened="true"
        router
        class="sidebar-menu"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
      >
        <el-menu-item index="/dashboard">
          <el-icon><House /></el-icon>
          <span>仪表板</span>
        </el-menu-item>
        
        <el-menu-item index="/tasks">
          <el-icon><List /></el-icon>
          <span>任务管理</span>
        </el-menu-item>
        
        <el-menu-item index="/statistics">
          <el-icon><DataAnalysis /></el-icon>
          <span>任务统计</span>
        </el-menu-item>
      </el-menu>
      
      <div class="sidebar-footer">
        <el-button 
          :icon="isCollapse ? 'Expand' : 'Fold'" 
          @click="toggleCollapse"
          link
          class="collapse-btn"
        />
      </div>
    </el-aside>

    <!-- 主内容区域 -->
    <el-container>
      <!-- 顶部导航 -->
      <el-header class="header">
        <div class="header-left">
          <h1 class="page-title">
            <el-icon class="title-icon">
              <Monitor />
            </el-icon>
            任务检查工具看板
          </h1>
          <span class="page-subtitle">统一的任务管理和监控平台</span>
        </div>
        
        <div class="header-right">
          <el-badge :value="completedTasksCount" class="task-badge">
            <el-button 
              type="primary" 
              :icon="Refresh" 
              @click="refreshTasks"
              circle
            />
          </el-badge>
          
          <el-dropdown>
            <el-avatar :size="32" class="user-avatar">
              <el-icon><User /></el-icon>
            </el-avatar>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item>管理员</el-dropdown-item>
                <el-dropdown-item divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 主内容 -->
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Monitor, Download, List, Refresh, User, Expand, Fold, House, DataAnalysis } from '@element-plus/icons-vue'
import { getCompletedTasks } from '@/api/tasks'

const route = useRoute()
const router = useRouter()

const isCollapse = ref(false)
const completedTasksCount = ref(0)

// 路由配置
const routes = [
  {
    path: '/dashboard',
    meta: { title: 'Azure Resource', icon: 'Download' }
  },
  {
    path: '/tasks',
    meta: { title: '任务历史', icon: 'List' }
  }
]

// 当前激活的菜单
const activeMenu = computed(() => {
  return route.path
})

// 切换侧边栏折叠状态
const toggleCollapse = () => {
  isCollapse.value = !isCollapse.value
}

// 刷新任务数据
const refreshTasks = async () => {
  // 如果当前在统计页面，不需要刷新任务数据
  if (route.path === '/statistics') {
    return
  }
  
  try {
    const response = await getCompletedTasks()
    completedTasksCount.value = response.tasks?.length || 0
  } catch (error) {
    console.error('刷新任务失败:', error)
  }
}

// 初始化
onMounted(() => {
  // 只在非统计页面时刷新任务
  if (route.path !== '/statistics') {
    refreshTasks()
  }
})
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.sidebar {
  background-color: #304156;
  transition: width 0.3s;
  display: flex;
  flex-direction: column;
}

.logo-container {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 16px;
  border-bottom: 1px solid #434a50;
}

.logo-icon {
  color: #409EFF;
  margin-right: 8px;
}

.logo-text {
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  white-space: nowrap;
}

.sidebar-menu {
  flex: 1;
  border: none;
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid #434a50;
  display: flex;
  justify-content: center;
}

.collapse-btn {
  color: #bfcbd9;
}

.header {
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 1px 4px rgba(0,21,41,.08);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.page-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #2c3e50;
  font-size: 20px;
  font-weight: 600;
  margin: 0;
}

.title-icon {
  color: #409EFF;
}

.page-subtitle {
  color: #909399;
  font-size: 14px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.task-badge {
  margin-right: 8px;
}

.user-avatar {
  cursor: pointer;
  background-color: #409EFF;
}

.main-content {
  background-color: #f5f7fa;
  padding: 24px;
  overflow-y: auto;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    z-index: 1000;
    height: 100vh;
  }
  
  .header-left {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
  
  .page-title {
    font-size: 18px;
  }
  
  .page-subtitle {
    font-size: 12px;
  }
}
</style> 