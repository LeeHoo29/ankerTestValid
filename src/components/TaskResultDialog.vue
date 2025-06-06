<template>
  <el-dialog
    v-model="visible"
    title="任务执行结果"
    width="800px"
    :close-on-click-modal="false"
  >
    <div v-if="taskResult" class="result-content">
      <!-- 任务信息 -->
      <el-descriptions :column="2" border>
        <el-descriptions-item label="任务ID">
          {{ taskResult.task_id }}
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(taskResult.status)">
            {{ getStatusText(taskResult.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="开始时间">
          {{ formatTime(taskResult.start_time) }}
        </el-descriptions-item>
        <el-descriptions-item label="执行时长">
          {{ taskResult.duration || '计算中...' }}
        </el-descriptions-item>
      </el-descriptions>

      <!-- 执行进度 -->
      <div v-if="taskResult.status === 'running'" class="progress-section">
        <h4>执行进度</h4>
        <el-progress 
          :percentage="getProgress()" 
          :status="getProgressStatus()"
          :stroke-width="8"
        />
        <p class="progress-text">{{ getProgressText() }}</p>
      </div>

      <!-- 命令输出 -->
      <div class="output-section">
        <h4>命令输出</h4>
        <el-input
          v-model="taskResult.output"
          type="textarea"
          :rows="12"
          readonly
          class="output-textarea"
        />
      </div>

      <!-- 错误信息 -->
      <div v-if="taskResult.status === 'failed' && taskResult.error" class="error-section">
        <h4>错误信息</h4>
        <el-alert
          :title="taskResult.error"
          type="error"
          :closable="false"
          show-icon
        />
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="visible = false">关闭</el-button>
        <el-button 
          v-if="taskResult?.status === 'completed'" 
          type="primary"
          @click="viewResults"
        >
          查看结果
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import dayjs from 'dayjs'

const props = defineProps({
  modelValue: Boolean,
  taskResult: Object
})

const emit = defineEmits(['update:modelValue', 'viewResults'])

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

// 获取状态类型
const getStatusType = (status) => {
  const statusMap = {
    'pending': 'info',
    'running': 'warning',
    'completed': 'success',
    'failed': 'danger'
  }
  return statusMap[status] || 'info'
}

// 获取状态文本
const getStatusText = (status) => {
  const statusMap = {
    'pending': '等待中',
    'running': '执行中',
    'completed': '已完成',
    'failed': '执行失败'
  }
  return statusMap[status] || status
}

// 获取进度百分比
const getProgress = () => {
  if (!props.taskResult) return 0
  
  const { status, start_time } = props.taskResult
  if (status === 'completed') return 100
  if (status === 'failed') return 100
  if (status === 'pending') return 0
  
  // 根据执行时间估算进度
  if (start_time) {
    const elapsed = dayjs().diff(dayjs(start_time), 'second')
    return Math.min(Math.floor(elapsed / 30 * 100), 95) // 假设30秒完成，最多95%
  }
  
  return 10
}

// 获取进度状态
const getProgressStatus = () => {
  if (!props.taskResult) return ''
  
  const { status } = props.taskResult
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'exception'
  return ''
}

// 获取进度文本
const getProgressText = () => {
  if (!props.taskResult) return ''
  
  const { status } = props.taskResult
  if (status === 'running') return '正在执行任务，请稍候...'
  if (status === 'completed') return '任务执行完成'
  if (status === 'failed') return '任务执行失败'
  return '准备执行任务'
}

// 格式化时间
const formatTime = (timestamp) => {
  if (!timestamp) return '-'
  return dayjs(timestamp).format('YYYY-MM-DD HH:mm:ss')
}

// 查看结果
const viewResults = () => {
  emit('viewResults', props.taskResult)
}
</script>

<style scoped>
.result-content {
  padding: 16px 0;
}

.progress-section,
.output-section,
.error-section {
  margin-top: 24px;
}

.progress-section h4,
.output-section h4,
.error-section h4 {
  margin: 0 0 12px 0;
  color: #2c3e50;
  font-size: 16px;
  font-weight: 600;
}

.progress-text {
  margin-top: 8px;
  color: #606266;
  font-size: 14px;
  text-align: center;
}

.output-textarea {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 12px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style> 