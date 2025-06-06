<template>
  <div class="dashboard">
    <!-- 页面头部 -->
    <div class="page-header">
      <el-card shadow="never" class="header-card">
        <div class="header-content">
          <div class="header-left">
            <el-icon class="module-icon" :size="32">
              <Download />
            </el-icon>
            <div class="module-info">
              <h2 class="module-title">Azure Resource Reader</h2>
              <p class="module-description">Azure资源数据获取和分析工具</p>
            </div>
          </div>
          <div class="header-right">
            <el-statistic title="已完成任务" :value="completedTasksCount" />
          </div>
        </div>
      </el-card>
    </div>

    <!-- 主要内容区域 -->
    <el-row :gutter="24">
      <!-- 左侧：任务表单 -->
      <el-col :lg="14" :md="24">
        <el-card shadow="hover" class="form-card">
          <template #header>
            <div class="card-header">
              <el-icon><Setting /></el-icon>
              <span>任务配置</span>
            </div>
          </template>

          <el-form 
            ref="taskFormRef" 
            :model="taskForm" 
            :rules="taskRules" 
            label-width="120px"
            class="task-form"
          >
            <el-form-item label="任务类型" prop="task_type">
              <el-select 
                v-model="taskForm.task_type" 
                placeholder="请选择任务类型"
                style="width: 100%"
              >
                <el-option 
                  label="AmazonReviewStarJob" 
                  value="AmazonReviewStarJob" 
                />
                <el-option 
                  label="AmazonListingJob" 
                  value="AmazonListingJob" 
                />
              </el-select>
            </el-form-item>

            <el-form-item label="任务ID" prop="task_id">
              <el-input 
                v-model="taskForm.task_id" 
                placeholder="例如: 2829160972"
                clearable
              >
                <template #append>
                  <el-button 
                    :icon="Search" 
                    @click="checkTaskExists"
                    :loading="checking"
                  />
                </template>
              </el-input>
              <div class="form-help">支持长任务ID或Job ID（系统会自动转换）</div>
            </el-form-item>

            <el-form-item label="输出类型" prop="output_type">
              <el-radio-group v-model="taskForm.output_type">
                <el-radio value="html">HTML (自动解压)</el-radio>
                <el-radio value="txt">TXT (自动解压)</el-radio>
                <el-radio value="json">JSON (自动解压)</el-radio>
                <el-radio value="raw">RAW (不解压)</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item label="解析模式">
              <el-switch 
                v-model="taskForm.use_parse"
                active-text="启用解析模式"
                inactive-text="关闭解析模式"
              />
              <div class="form-help">同时获取原始数据和解析数据，使用优化算法</div>
            </el-form-item>

            <el-form-item>
              <el-button 
                type="primary" 
                :icon="ArrowRight" 
                @click="submitTask"
                :loading="submitting"
                size="large"
              >
                执行任务
              </el-button>
              <el-button @click="resetForm">重置</el-button>
            </el-form-item>
          </el-form>

          <!-- 命令预览 -->
          <el-divider content-position="left">命令预览</el-divider>
          <el-input 
            v-model="commandPreview" 
            readonly 
            type="textarea" 
            :rows="2"
            class="command-preview"
          />
        </el-card>
      </el-col>

      <!-- 右侧：已完成任务列表 -->
      <el-col :lg="10" :md="24">
        <el-card shadow="hover" class="tasks-card">
          <template #header>
            <div class="card-header">
              <el-icon><List /></el-icon>
              <span>已完成任务</span>
              <el-button 
                link
                :icon="Refresh" 
                @click="refreshCompletedTasks"
                :loading="refreshing"
                class="refresh-btn"
              />
            </div>
          </template>

          <div class="completed-tasks" v-loading="loading">
            <el-empty 
              v-if="!completedTasks.length" 
              description="暂无已完成任务"
              :image-size="100"
            />
            
            <div v-else class="task-list">
              <div 
                v-for="task in completedTasks" 
                :key="task.job_id"
                class="task-item"
                @click="viewTaskFiles(task)"
              >
                <div class="task-header">
                  <el-tag :type="getTaskTypeColor(task.task_type)" size="small">
                    {{ task.task_type }}
                  </el-tag>
                  <span class="job-id">{{ task.job_id }}</span>
                </div>
                
                <div class="task-details">
                  <div class="detail-row">
                    <el-icon><Key /></el-icon>
                    <span>{{ task.actual_task_id }}</span>
                  </div>
                  <div class="detail-row">
                    <el-icon><Clock /></el-icon>
                    <span>{{ formatTime(task.last_updated) }}</span>
                  </div>
                  <div class="detail-row">
                    <el-icon><Document /></el-icon>
                    <span>{{ task.file_count }} 文件</span>
                  </div>
                </div>

                <div class="task-actions">
                  <el-button 
                    type="primary" 
                    :icon="View" 
                    size="small"
                    @click.stop="viewTaskFiles(task)"
                  >
                    查看
                  </el-button>
                  <el-button 
                    type="success" 
                    :icon="Refresh" 
                    size="small"
                    @click.stop="rerunTask(task)"
                  >
                    重跑
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 任务执行结果对话框 -->
    <TaskResultDialog 
      v-model="showResultDialog"
      :task-result="currentTaskResult"
    />

    <!-- 文件查看对话框 -->
    <FileViewDialog 
      v-model="showFileDialog"
      :task="selectedTask"
    />

    <!-- 任务存在确认对话框 -->
    <TaskExistsDialog 
      v-model="showExistsDialog"
      :existing-task="existingTask"
      @confirm="handleExistsConfirm"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Download, Setting, Search, ArrowRight, List, Refresh, 
  View, Key, Clock, Document 
} from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { 
  getCompletedTasks, 
  submitTask as apiSubmitTask, 
  checkTaskExists as apiCheckTaskExists,
  getTaskStatus
} from '@/api/tasks'
import TaskResultDialog from '@/components/TaskResultDialog.vue'
import FileViewDialog from '@/components/FileViewDialog.vue'
import TaskExistsDialog from '@/components/TaskExistsDialog.vue'

// 响应式数据
const taskFormRef = ref()
const loading = ref(false)
const refreshing = ref(false)
const submitting = ref(false)
const checking = ref(false)
const completedTasks = ref([])
const completedTasksCount = ref(0)
const showResultDialog = ref(false)
const showFileDialog = ref(false)
const showExistsDialog = ref(false)
const currentTaskResult = ref(null)
const selectedTask = ref(null)
const existingTask = ref(null)

// 表单数据
const taskForm = reactive({
  task_type: 'AmazonReviewStarJob',
  task_id: '',
  output_type: 'html',
  use_parse: true
})

// 表单验证规则
const taskRules = {
  task_type: [
    { required: true, message: '请选择任务类型', trigger: 'change' }
  ],
  task_id: [
    { required: true, message: '请输入任务ID', trigger: 'blur' },
    { pattern: /^\d+$/, message: '任务ID只能包含数字', trigger: 'blur' }
  ],
  output_type: [
    { required: true, message: '请选择输出类型', trigger: 'change' }
  ]
}

// 命令预览
const commandPreview = computed(() => {
  const { task_type, task_id, output_type, use_parse } = taskForm
  let cmd = `python3 src/azure_resource_reader.py ${task_type} ${task_id} ${output_type}`
  if (use_parse) {
    cmd += ' --with-parse'
  }
  return cmd
})

// 获取任务类型颜色
const getTaskTypeColor = (type) => {
  return type === 'AmazonReviewStarJob' ? 'primary' : 'success'
}

// 格式化时间
const formatTime = (timestamp) => {
  return dayjs(timestamp).format('MM-DD HH:mm')
}

// 检查任务是否存在
const checkTaskExists = async () => {
  if (!taskForm.task_id) {
    ElMessage.warning('请先输入任务ID')
    return
  }

  checking.value = true
  try {
    const result = await apiCheckTaskExists(taskForm.task_id)
    if (result.exists) {
      existingTask.value = result.task
      showExistsDialog.value = true
    } else {
      ElMessage.success('任务ID可用')
    }
  } catch (error) {
    console.error('检查任务失败:', error)
  } finally {
    checking.value = false
  }
}

// 处理任务存在确认
const handleExistsConfirm = (action) => {
  if (action === 'continue') {
    executeTask()
  }
  showExistsDialog.value = false
}

// 提交任务
const submitTask = async () => {
  if (!taskFormRef.value) return
  
  const valid = await taskFormRef.value.validate().catch(() => false)
  if (!valid) return

  // 先检查任务是否存在
  checking.value = true
  try {
    const result = await apiCheckTaskExists(taskForm.task_id)
    if (result.exists) {
      existingTask.value = result.task
      showExistsDialog.value = true
      return
    }
  } catch (error) {
    console.error('检查任务失败:', error)
  } finally {
    checking.value = false
  }

  executeTask()
}

// 执行任务
const executeTask = async () => {
  submitting.value = true
  try {
    const result = await apiSubmitTask(taskForm)
    
    // 初始化任务结果数据
    currentTaskResult.value = {
      task_id: result.task_id,
      command: result.command,
      status: 'pending',
      output: '',
      start_time: new Date().toISOString(),
      created_time: new Date().toISOString()
    }
    
    showResultDialog.value = true
    
    // 开始轮询任务状态
    if (result.task_id) {
      pollTaskStatus(result.task_id)
    }
    
    ElMessage.success('任务提交成功')
  } catch (error) {
    console.error('提交任务失败:', error)
    ElMessage.error('任务提交失败')
  } finally {
    submitting.value = false
  }
}

// 轮询任务状态
const pollTaskStatus = async (taskId) => {
  const poll = async () => {
    try {
      const response = await getTaskStatus(taskId)
      
      // 更新任务结果数据
      currentTaskResult.value = {
        ...currentTaskResult.value,
        status: response.status,
        output: response.output || '',
        duration: response.duration,
        return_code: response.return_code,
        error: response.error
      }
      
      if (response.status === 'completed' || response.status === 'failed') {
        refreshCompletedTasks()
        return
      }
      
      setTimeout(poll, 2000) // 增加轮询间隔到2秒
    } catch (error) {
      console.error('获取任务状态失败:', error)
    }
  }
  
  poll()
}

// 重置表单
const resetForm = () => {
  if (taskFormRef.value) {
    taskFormRef.value.resetFields()
  }
  Object.assign(taskForm, {
    task_type: 'AmazonReviewStarJob',
    task_id: '',
    output_type: 'html',
    use_parse: true
  })
}

// 查看任务文件
const viewTaskFiles = (task) => {
  selectedTask.value = task
  showFileDialog.value = true
}

// 重新运行任务
const rerunTask = (task) => {
  Object.assign(taskForm, {
    task_type: task.task_type,
    task_id: task.job_id,
    output_type: 'html',
    use_parse: true
  })
  ElMessage.success('已填充任务参数，可以重新执行')
}

// 刷新已完成任务
const refreshCompletedTasks = async () => {
  refreshing.value = true
  try {
    const response = await getCompletedTasks()
    completedTasks.value = response.tasks || []
    completedTasksCount.value = response.tasks?.length || 0
  } catch (error) {
    console.error('获取已完成任务失败:', error)
  } finally {
    refreshing.value = false
  }
}

// 初始化
onMounted(() => {
  refreshCompletedTasks()
})
</script>

<style scoped>
.dashboard {
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

.module-icon {
  color: #409EFF;
}

.module-title {
  margin: 0 0 4px 0;
  color: #2c3e50;
  font-size: 20px;
  font-weight: 600;
}

.module-description {
  margin: 0;
  color: #909399;
  font-size: 14px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.form-card, .tasks-card {
  height: fit-content;
}

.task-form {
  margin-top: 16px;
}

.form-help {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
}

.command-preview {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
}

.refresh-btn {
  margin-left: auto;
}

.task-list {
  max-height: 600px;
  overflow-y: auto;
}

.task-item {
  padding: 16px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  margin-bottom: 12px;
  cursor: pointer;
  transition: all 0.3s;
}

.task-item:hover {
  border-color: #409EFF;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.1);
}

.task-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.job-id {
  font-weight: 600;
  color: #2c3e50;
}

.task-details {
  margin-bottom: 12px;
}

.detail-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  color: #606266;
  font-size: 14px;
}

.task-actions {
  display: flex;
  gap: 8px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
  
  .task-form {
    margin-top: 0;
  }
  
  .task-item {
    padding: 12px;
  }
}
</style> 