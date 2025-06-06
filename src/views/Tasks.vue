<template>
  <div class="tasks-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <el-card shadow="never" class="header-card">
        <div class="header-content">
          <div class="header-left">
            <el-icon class="page-icon" :size="32">
              <List />
            </el-icon>
            <div class="page-info">
              <h2 class="page-title">任务历史</h2>
              <p class="page-description">查看所有已执行的任务记录</p>
            </div>
          </div>
          <div class="header-right">
            <el-button 
              type="danger" 
              :icon="Delete" 
              @click="clearAllTasks"
              :disabled="!tasks.length"
            >
              清空历史
            </el-button>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 任务列表 -->
    <el-card shadow="hover" class="tasks-card">
      <template #header>
        <div class="card-header">
          <span>任务列表 ({{ tasks.length }})</span>
          <el-button 
            link
            :icon="Refresh" 
            @click="loadTasks"
            :loading="loading"
          />
        </div>
      </template>

      <div v-loading="loading">
        <el-empty 
          v-if="!tasks.length" 
          description="暂无任务历史"
          :image-size="120"
        >
          <el-button type="primary" @click="$router.push('/dashboard')">
            去执行任务
          </el-button>
        </el-empty>

        <div v-else class="tasks-grid">
          <div 
            v-for="task in tasks" 
            :key="task.job_id"
            class="task-card"
            @click="viewTaskDetails(task)"
          >
            <div class="task-header">
              <el-tag :type="getTaskTypeColor(task.task_type)" size="large">
                {{ task.task_type }}
              </el-tag>
              <el-dropdown @command="handleTaskAction">
                <el-button link :icon="MoreFilled" />
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item 
                      :command="{ action: 'view', task }"
                      :icon="View"
                    >
                      查看文件
                    </el-dropdown-item>
                    <el-dropdown-item 
                      :command="{ action: 'rerun', task }"
                      :icon="Refresh"
                    >
                      重新运行
                    </el-dropdown-item>
                    <el-dropdown-item 
                      :command="{ action: 'download', task }"
                      :icon="Download"
                      divided
                    >
                      下载结果
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>

            <div class="task-content">
              <div class="task-title">
                Job ID: {{ task.job_id }}
              </div>
              <div class="task-id">
                Task ID: {{ task.actual_task_id }}
              </div>
              
              <div class="task-meta">
                <div class="meta-item">
                  <el-icon><Clock /></el-icon>
                  <span>{{ formatTime(task.last_updated) }}</span>
                </div>
                <div class="meta-item">
                  <el-icon><Document /></el-icon>
                  <span>{{ task.file_count }} 文件</span>
                </div>
                <div class="meta-item">
                  <el-icon><FolderOpened /></el-icon>
                  <span>{{ formatFileSize(task.total_size) }}</span>
                </div>
              </div>

              <div class="task-status">
                <el-badge 
                  :value="task.directory_exists ? '✓' : '✗'" 
                  :type="task.directory_exists ? 'success' : 'danger'"
                  class="status-badge"
                >
                  <span>目录状态</span>
                </el-badge>
                <el-badge 
                  v-if="task.has_parse_file"
                  value="解析"
                  type="info"
                  class="status-badge"
                >
                  <span>包含解析</span>
                </el-badge>
              </div>
            </div>

            <div class="task-actions">
              <el-button 
                type="primary" 
                :icon="View" 
                size="small"
                @click.stop="viewTaskDetails(task)"
              >
                查看详情
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 任务详情对话框 -->
    <FileViewDialog 
      v-model="showDetailDialog"
      :task="selectedTask"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  List, Delete, Refresh, View, Download, MoreFilled,
  Clock, Document, FolderOpened
} from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { getCompletedTasks, clearTasks } from '@/api/tasks'
import FileViewDialog from '@/components/FileViewDialog.vue'

const router = useRouter()

const loading = ref(false)
const tasks = ref([])
const showDetailDialog = ref(false)
const selectedTask = ref(null)

// 获取任务类型颜色
const getTaskTypeColor = (type) => {
  return type === 'AmazonReviewStarJob' ? 'primary' : 'success'
}

// 格式化时间
const formatTime = (timestamp) => {
  return dayjs(timestamp).format('YYYY-MM-DD HH:mm:ss')
}

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
}

// 加载任务列表
const loadTasks = async () => {
  loading.value = true
  try {
    const response = await getCompletedTasks()
    tasks.value = response.tasks || []
  } catch (error) {
    console.error('加载任务失败:', error)
    ElMessage.error('加载任务失败')
  } finally {
    loading.value = false
  }
}

// 查看任务详情
const viewTaskDetails = (task) => {
  selectedTask.value = task
  showDetailDialog.value = true
}

// 处理任务操作
const handleTaskAction = ({ action, task }) => {
  switch (action) {
    case 'view':
      viewTaskDetails(task)
      break
    case 'rerun':
      rerunTask(task)
      break
    case 'download':
      downloadTaskResults(task)
      break
  }
}

// 重新运行任务
const rerunTask = (task) => {
  router.push({
    path: '/dashboard',
    query: {
      task_type: task.task_type,
      task_id: task.job_id
    }
  })
  ElMessage.success('已跳转到任务配置页面')
}

// 下载任务结果
const downloadTaskResults = (task) => {
  // 这里可以实现批量下载功能
  ElMessage.info('批量下载功能开发中...')
}

// 清空所有任务
const clearAllTasks = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要清空所有任务历史吗？此操作不可恢复。',
      '确认清空',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await clearTasks()
    tasks.value = []
    ElMessage.success('任务历史已清空')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('清空任务失败:', error)
      ElMessage.error('清空任务失败')
    }
  }
}

// 初始化
onMounted(() => {
  loadTasks()
})
</script>

<style scoped>
.tasks-page {
  height: 100%;
}

.page-header {
  margin-bottom: 24px;
}

.header-card {
  border: none;
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.page-icon {
  color: #409EFF;
}

.page-title {
  margin: 0 0 4px 0;
  color: #2c3e50;
  font-size: 20px;
  font-weight: 600;
}

.page-description {
  margin: 0;
  color: #909399;
  font-size: 14px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}

.tasks-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 20px;
}

.task-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s;
  background: #fff;
}

.task-card:hover {
  border-color: #409EFF;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.15);
  transform: translateY(-2px);
}

.task-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.task-content {
  margin-bottom: 16px;
}

.task-title {
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 4px;
}

.task-id {
  font-size: 14px;
  color: #606266;
  margin-bottom: 12px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
}

.task-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 12px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #606266;
  font-size: 14px;
}

.task-status {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.status-badge {
  font-size: 12px;
}

.task-actions {
  display: flex;
  justify-content: flex-end;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
  
  .tasks-grid {
    grid-template-columns: 1fr;
  }
  
  .task-card {
    padding: 16px;
  }
  
  .task-meta {
    flex-direction: column;
    gap: 8px;
  }
}
</style> 