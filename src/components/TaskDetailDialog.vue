<template>
  <el-dialog
    v-model="visible"
    title="任务详情"
    width="80%"
    destroy-on-close
    :close-on-click-modal="false"
  >
    <div v-if="task" class="task-detail-container">
      <!-- 基本信息 -->
      <el-card class="detail-card">
        <template #header>
          <div class="card-header">
            <el-icon><InfoFilled /></el-icon>
            <span>基本信息</span>
          </div>
        </template>
        
        <el-descriptions :column="2" border>
          <el-descriptions-item label="任务ID">
            <el-tag type="primary">{{ task.job_id }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="实际任务ID">
            <el-tag>{{ task.actual_task_id }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="任务类型">
            <el-tag :type="getTaskTypeColor(task.task_type)">
              {{ task.task_type }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="task.status === 'success' ? 'success' : 'warning'">
              {{ task.status }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="文件数量">
            <el-tag>{{ task.file_count }} 个</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="解析文件">
            <el-tag :type="task.has_parse_file ? 'success' : 'info'">
              {{ task.has_parse_file ? '已生成' : '未生成' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="存储路径">
            <el-text class="path-text">{{ task.relative_path }}</el-text>
          </el-descriptions-item>
          <el-descriptions-item label="数据来源">
            <el-tag :type="task.source === 'database' ? 'success' : 'warning'">
              {{ task.source === 'database' ? '数据库' : 'JSON文件' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 文件详情 -->
      <el-card class="detail-card">
        <template #header>
          <div class="card-header">
            <el-icon><Document /></el-icon>
            <span>文件详情</span>
          </div>
        </template>
        
        <div v-if="task.files && task.files.length > 0">
          <el-collapse v-model="activeFile" accordion>
            <el-collapse-item 
              v-for="(file, index) in task.files" 
              :key="index"
              :title="file.file_name"
              :name="index"
            >
              <template #title>
                <div class="file-title">
                  <el-icon>
                    <component :is="getFileIcon(file.file_name)" />
                  </el-icon>
                  <span class="file-name">{{ file.file_name }}</span>
                  <el-tag 
                    size="small" 
                    :type="file.file_type === 'parse' ? 'success' : 'primary'"
                  >
                    {{ file.file_type === 'parse' ? '解析文件' : '原始文件' }}
                  </el-tag>
                  <el-tag size="small" type="info">
                    {{ formatFileSize(file.file_size) }}
                  </el-tag>
                </div>
              </template>
              
              <div class="file-content">
                <div class="file-path">
                  <el-text size="small" type="info">
                    路径: {{ file.file_path }}
                  </el-text>
                </div>
                
                <div class="file-preview">
                  <div class="preview-header">
                    <span>文件预览</span>
                    <el-button 
                      size="small" 
                      type="primary" 
                      @click="downloadFile(file.file_path)"
                    >
                      下载文件
                    </el-button>
                  </div>
                  
                  <div class="preview-content">
                    <el-alert
                      v-if="file.preview_type === 'error'"
                      :title="file.preview"
                      type="error"
                      show-icon
                      :closable="false"
                    />
                    
                    <pre 
                      v-else-if="file.preview_type === 'json'"
                      class="json-preview"
                    >{{ file.preview }}</pre>
                    
                    <div 
                      v-else-if="file.preview_type === 'html'"
                      class="html-preview"
                      v-html="file.preview"
                    ></div>
                    
                    <pre 
                      v-else
                      class="text-preview"
                    >{{ file.preview }}</pre>
                  </div>
                </div>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
        
        <el-empty v-else description="暂无文件信息" />
      </el-card>
    </div>
    
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="visible = false">关闭</el-button>
        <el-button type="primary" @click="openFolder">
          <el-icon><Folder /></el-icon>
          打开文件夹
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  InfoFilled, Document, Folder, 
  Document as DocumentIcon, 
  VideoPlay, Picture 
} from '@element-plus/icons-vue'
import { downloadFile as apiDownloadFile } from '@/api/tasks'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  task: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:modelValue'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const activeFile = ref(0)

// 获取任务类型颜色
const getTaskTypeColor = (type) => {
  return type === 'AmazonReviewStarJob' ? 'primary' : 'success'
}

// 获取文件图标
const getFileIcon = (filename) => {
  const ext = filename.split('.').pop()?.toLowerCase()
  switch (ext) {
    case 'json':
      return DocumentIcon
    case 'html':
    case 'htm':
      return VideoPlay
    case 'png':
    case 'jpg':
    case 'jpeg':
    case 'gif':
    case 'svg':
      return Picture
    default:
      return DocumentIcon
  }
}

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 下载文件
const downloadFile = async (filePath) => {
  try {
    const response = await apiDownloadFile(filePath)
    const url = window.URL.createObjectURL(new Blob([response]))
    const link = document.createElement('a')
    link.href = url
    link.download = filePath.split('/').pop()
    link.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('下载成功')
  } catch (error) {
    console.error('下载失败:', error)
    ElMessage.error('下载失败')
  }
}

// 打开文件夹
const openFolder = () => {
  if (props.task?.full_path) {
    // 在新窗口中打开文件夹路径
    ElMessage.info(`文件夹路径: ${props.task.full_path}`)
  }
}
</script>

<style scoped>
.task-detail-container {
  max-height: 70vh;
  overflow-y: auto;
}

.detail-card {
  margin-bottom: 16px;
}

.detail-card:last-child {
  margin-bottom: 0;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.path-text {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 12px;
  color: #666;
}

.file-title {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.file-name {
  flex: 1;
  font-weight: 500;
}

.file-content {
  padding: 8px 0;
}

.file-path {
  margin-bottom: 12px;
  padding: 8px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.file-preview {
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  overflow: hidden;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background-color: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
  font-weight: 500;
}

.preview-content {
  max-height: 300px;
  overflow-y: auto;
}

.json-preview {
  margin: 0;
  padding: 12px;
  background-color: #f8f9fa;
  border: none;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 12px;
  line-height: 1.4;
  color: #333;
}

.html-preview {
  padding: 12px;
  font-size: 12px;
  line-height: 1.4;
  color: #333;
}

.text-preview {
  margin: 0;
  padding: 12px;
  background-color: #f8f9fa;
  border: none;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 12px;
  line-height: 1.4;
  color: #333;
  white-space: pre-wrap;
  word-break: break-all;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.el-descriptions {
  --el-descriptions-item-bordered-label-background: #f5f7fa;
}
</style> 