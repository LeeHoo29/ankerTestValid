<template>
  <el-dialog
    v-model="visible"
    title="对比查看"
    width="95%"
    :close-on-click-modal="false"
    class="compare-dialog"
  >
    <div class="compare-content">
      <el-row :gutter="16">
        <!-- HTML预览 -->
        <el-col :span="14">
          <div class="panel">
            <div class="panel-header">
              <h4>HTML预览</h4>
              <el-select 
                v-model="selectedHtmlFile" 
                placeholder="选择HTML文件"
                @change="loadHtmlFile"
                style="width: 200px"
              >
                <el-option
                  v-for="file in htmlFiles"
                  :key="file.name"
                  :label="file.name"
                  :value="file.name"
                />
              </el-select>
            </div>
            <div class="panel-content">
              <iframe 
                v-if="htmlContent"
                :srcdoc="htmlContent" 
                class="html-frame"
                sandbox="allow-same-origin"
              />
              <el-empty v-else description="请选择HTML文件" />
            </div>
          </div>
        </el-col>

        <!-- JSON预览 -->
        <el-col :span="10">
          <div class="panel">
            <div class="panel-header">
              <h4>JSON数据</h4>
              <el-select 
                v-model="selectedJsonFile" 
                placeholder="选择JSON文件"
                @change="loadJsonFile"
                style="width: 200px"
              >
                <el-option
                  v-for="file in jsonFiles"
                  :key="file.name"
                  :label="file.name"
                  :value="file.name"
                />
              </el-select>
            </div>
            <div class="panel-content">
              <JsonViewer 
                v-if="jsonData"
                :data="jsonData" 
              />
              <el-empty v-else description="请选择JSON文件" />
            </div>
          </div>
        </el-col>
      </el-row>
    </div>

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
import { getFileContent } from '@/api/tasks'
import JsonViewer from './JsonViewer.vue'

const props = defineProps({
  modelValue: Boolean,
  task: Object,
  fileList: Array
})

const emit = defineEmits(['update:modelValue'])

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const selectedHtmlFile = ref('')
const selectedJsonFile = ref('')
const htmlContent = ref('')
const jsonData = ref(null)

// 过滤HTML文件
const htmlFiles = computed(() => {
  return props.fileList?.filter(file => 
    /\.(html|htm)$/i.test(file.name)
  ) || []
})

// 过滤JSON文件
const jsonFiles = computed(() => {
  return props.fileList?.filter(file => 
    /\.json$/i.test(file.name)
  ) || []
})

// 加载HTML文件
const loadHtmlFile = async () => {
  if (!selectedHtmlFile.value || !props.task) return
  
  try {
    const response = await getFileContent(`${props.task.full_path}/${selectedHtmlFile.value}`)
    htmlContent.value = response.content || ''
  } catch (error) {
    console.error('加载HTML文件失败:', error)
    ElMessage.error('加载HTML文件失败')
  }
}

// 加载JSON文件
const loadJsonFile = async () => {
  if (!selectedJsonFile.value || !props.task) return
  
  try {
    const response = await getFileContent(`${props.task.full_path}/${selectedJsonFile.value}`)
    jsonData.value = JSON.parse(response.content || '{}')
  } catch (error) {
    console.error('加载JSON文件失败:', error)
    ElMessage.error('加载JSON文件失败')
    jsonData.value = { error: 'JSON格式错误' }
  }
}

// 监听对话框显示状态
watch(visible, (newVal) => {
  if (newVal) {
    // 自动选择第一个文件
    if (htmlFiles.value.length > 0) {
      selectedHtmlFile.value = htmlFiles.value[0].name
      loadHtmlFile()
    }
    if (jsonFiles.value.length > 0) {
      selectedJsonFile.value = jsonFiles.value[0].name
      loadJsonFile()
    }
  } else {
    // 清理数据
    selectedHtmlFile.value = ''
    selectedJsonFile.value = ''
    htmlContent.value = ''
    jsonData.value = null
  }
})
</script>

<style scoped>
.compare-dialog {
  --el-dialog-content-font-size: 14px;
}

.compare-content {
  height: 80vh;
}

.panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
}

.panel-header {
  background: #f5f7fa;
  padding: 12px 16px;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.panel-header h4 {
  margin: 0;
  color: #2c3e50;
  font-size: 16px;
  font-weight: 600;
}

.panel-content {
  flex: 1;
  overflow: hidden;
  background: #fff;
}

.html-frame {
  width: 100%;
  height: 100%;
  border: none;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
}
</style> 