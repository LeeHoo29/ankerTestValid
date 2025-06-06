<template>
  <el-dialog
    v-model="visible"
    :title="`任务文件 - ${task?.job_id || ''}`"
    width="90%"
    :close-on-click-modal="false"
    class="file-dialog"
  >
    <div v-if="task" class="file-content">
      <!-- 文件列表 -->
      <div class="file-list-section">
        <div class="section-header">
          <h4>文件列表</h4>
          <el-button 
            type="primary" 
            :icon="View" 
            @click="openCompareView"
            :disabled="!hasCompareFiles"
          >
            对比查看
          </el-button>
        </div>
        
        <el-table 
          :data="fileList" 
          v-loading="loading"
          @row-click="previewFile"
          class="file-table"
        >
          <el-table-column prop="name" label="文件名" min-width="200">
            <template #default="{ row }">
              <div class="file-name">
                <el-icon class="file-icon">
                  <component :is="getFileIcon(row.name)" />
                </el-icon>
                {{ row.name }}
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="size" label="大小" width="100">
            <template #default="{ row }">
              {{ formatFileSize(row.size) }}
            </template>
          </el-table-column>
          <el-table-column prop="modified" label="修改时间" width="180">
            <template #default="{ row }">
              {{ formatTime(row.modified) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200">
            <template #default="{ row }">
              <el-button 
                type="primary" 
                :icon="View" 
                size="small"
                @click.stop="previewFile(row)"
              >
                预览
              </el-button>
              <el-button 
                type="success" 
                :icon="Download" 
                size="small"
                @click.stop="downloadFile(row)"
              >
                下载
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 文件预览 -->
      <div v-if="selectedFile" class="preview-section">
        <div class="section-header">
          <h4>文件预览 - {{ selectedFile.name }}</h4>
          <el-button 
            link
            :icon="Close" 
            @click="selectedFile = null"
          />
        </div>
        
        <div class="preview-content" v-loading="previewLoading">
          <!-- HTML 预览 -->
          <div v-if="isHtmlFile(selectedFile.name)" class="html-preview">
            <iframe 
              :srcdoc="fileContent" 
              class="html-frame"
              sandbox="allow-same-origin"
            />
          </div>
          
          <!-- JSON 预览 -->
          <div v-else-if="isJsonFile(selectedFile.name)" class="json-preview">
            <JsonViewer :data="jsonData" />
          </div>
          
          <!-- 文本预览 -->
          <div v-else class="text-preview">
            <el-input
              v-model="fileContent"
              type="textarea"
              :rows="20"
              readonly
              class="text-content"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- 对比查看对话框 -->
    <CompareViewDialog 
      v-model="showCompareDialog"
      :task="task"
      :file-list="fileList"
    />

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="visible = false">关闭</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  View, Download, Close, Document, 
  Picture, VideoPlay, Folder 
} from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { getFileList, getFileContent, downloadFile as apiDownloadFile } from '@/api/tasks'
import JsonViewer from './JsonViewer.vue'
import CompareViewDialog from './CompareViewDialog.vue'

const props = defineProps({
  modelValue: Boolean,
  task: Object
})

const emit = defineEmits(['update:modelValue'])

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const loading = ref(false)
const previewLoading = ref(false)
const fileList = ref([])
const selectedFile = ref(null)
const fileContent = ref('')
const jsonData = ref(null)
const showCompareDialog = ref(false)

// 是否有可对比的文件
const hasCompareFiles = computed(() => {
  return Array.isArray(fileList.value) && fileList.value.some(file => 
    file.name.endsWith('.html') || file.name.endsWith('.json')
  )
})

// 获取文件图标
const getFileIcon = (fileName) => {
  const ext = fileName.split('.').pop()?.toLowerCase()
  switch (ext) {
    case 'html':
    case 'htm':
      return 'Document'
    case 'json':
      return 'Document'
    case 'txt':
      return 'Document'
    case 'jpg':
    case 'jpeg':
    case 'png':
    case 'gif':
      return 'Picture'
    case 'mp4':
    case 'avi':
      return 'VideoPlay'
    default:
      return 'Document'
  }
}

// 判断是否为HTML文件
const isHtmlFile = (fileName) => {
  return /\.(html|htm)$/i.test(fileName)
}

// 判断是否为JSON文件
const isJsonFile = (fileName) => {
  return /\.json$/i.test(fileName)
}

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (!bytes) return '-'
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
}

// 格式化时间
const formatTime = (timestamp) => {
  if (!timestamp) return '-'
  return dayjs(timestamp).format('MM-DD HH:mm')
}

// 加载文件列表
const loadFileList = async () => {
  if (!props.task) return
  
  loading.value = true
  try {
    const response = await getFileList(props.task.full_path)
    fileList.value = response.files || []
  } catch (error) {
    console.error('加载文件列表失败:', error)
    ElMessage.error('加载文件列表失败')
    fileList.value = []
  } finally {
    loading.value = false
  }
}

// 预览文件
const previewFile = async (file) => {
  selectedFile.value = file
  previewLoading.value = true
  
  try {
    const response = await getFileContent(`${props.task.full_path}/${file.name}`)
    fileContent.value = response.content || ''
    
    // 如果是JSON文件，解析数据
    if (isJsonFile(file.name)) {
      try {
        jsonData.value = JSON.parse(response.content || '{}')
      } catch (error) {
        console.error('JSON解析失败:', error)
        jsonData.value = { error: 'JSON格式错误' }
      }
    }
  } catch (error) {
    console.error('加载文件内容失败:', error)
    ElMessage.error('加载文件内容失败')
  } finally {
    previewLoading.value = false
  }
}

// 下载文件
const downloadFile = async (file) => {
  try {
    const blob = await apiDownloadFile(`${props.task.full_path}/${file.name}`)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = file.name
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
    
    ElMessage.success('文件下载成功')
  } catch (error) {
    console.error('下载文件失败:', error)
    ElMessage.error('下载文件失败')
  }
}

// 打开对比查看
const openCompareView = () => {
  showCompareDialog.value = true
}

// 监听对话框显示状态
watch(visible, (newVal) => {
  if (newVal && props.task) {
    loadFileList()
  } else {
    selectedFile.value = null
    fileContent.value = ''
    jsonData.value = null
  }
})
</script>

<style scoped>
.file-dialog {
  --el-dialog-content-font-size: 14px;
}

.file-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
  height: 70vh;
}

.file-list-section {
  flex: 0 0 auto;
}

.preview-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.section-header h4 {
  margin: 0;
  color: #2c3e50;
  font-size: 16px;
  font-weight: 600;
}

.file-table {
  max-height: 300px;
}

.file-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-icon {
  color: #409EFF;
}

.preview-content {
  flex: 1;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  overflow: hidden;
}

.html-preview {
  height: 100%;
}

.html-frame {
  width: 100%;
  height: 100%;
  border: none;
}

.json-preview {
  height: 100%;
  overflow: auto;
}

.text-preview {
  height: 100%;
}

.text-content {
  height: 100%;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 12px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .file-content {
    height: 60vh;
  }
  
  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
}
</style>