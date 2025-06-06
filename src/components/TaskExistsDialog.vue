<template>
  <el-dialog
    v-model="visible"
    title="任务已存在"
    width="500px"
    :close-on-click-modal="false"
  >
    <div class="exists-content">
      <el-alert
        title="检测到重复任务"
        type="warning"
        :closable="false"
        show-icon
      >
        <template #default>
          <p>任务ID <strong>{{ existingTask?.job_id }}</strong> 已经存在。</p>
          <p>上次执行时间: {{ formatTime(existingTask?.last_updated) }}</p>
        </template>
      </el-alert>

      <div class="task-info" v-if="existingTask">
        <h4>现有任务信息</h4>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="任务类型">
            {{ existingTask.task_type }}
          </el-descriptions-item>
          <el-descriptions-item label="Job ID">
            {{ existingTask.job_id }}
          </el-descriptions-item>
          <el-descriptions-item label="Task ID">
            {{ existingTask.actual_task_id }}
          </el-descriptions-item>
          <el-descriptions-item label="文件数量">
            {{ existingTask.file_count }} 个文件
          </el-descriptions-item>
          <el-descriptions-item label="最后更新">
            {{ formatTime(existingTask.last_updated) }}
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <div class="action-options">
        <h4>请选择操作</h4>
        <el-radio-group v-model="selectedAction">
          <el-radio value="view">查看现有任务结果</el-radio>
          <el-radio value="continue">继续执行（覆盖现有结果）</el-radio>
          <el-radio value="cancel">取消操作</el-radio>
        </el-radio-group>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleAction('cancel')">取消</el-button>
        <el-button 
          type="primary" 
          @click="handleAction(selectedAction)"
          :disabled="!selectedAction"
        >
          确定
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import dayjs from 'dayjs'

const props = defineProps({
  modelValue: Boolean,
  existingTask: Object
})

const emit = defineEmits(['update:modelValue', 'confirm'])

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const selectedAction = ref('view')

// 格式化时间
const formatTime = (timestamp) => {
  if (!timestamp) return '-'
  return dayjs(timestamp).format('YYYY-MM-DD HH:mm:ss')
}

// 处理操作
const handleAction = (action) => {
  if (action === 'cancel') {
    visible.value = false
    return
  }
  
  emit('confirm', action)
  visible.value = false
}
</script>

<style scoped>
.exists-content {
  padding: 16px 0;
}

.task-info {
  margin: 24px 0;
}

.task-info h4 {
  margin: 0 0 12px 0;
  color: #2c3e50;
  font-size: 16px;
  font-weight: 600;
}

.action-options {
  margin-top: 24px;
}

.action-options h4 {
  margin: 0 0 12px 0;
  color: #2c3e50;
  font-size: 16px;
  font-weight: 600;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style> 