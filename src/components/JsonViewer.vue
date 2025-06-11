<template>
  <div class="json-viewer">
    <div class="json-toolbar">
      <el-button 
        link
        :icon="DocumentCopy" 
        @click="copyJson"
        size="small"
        :disabled="isEmpty"
      >
        复制
      </el-button>
      <el-button 
        link
        :icon="isExpanded ? 'Minus' : 'Plus'" 
        @click="toggleExpand"
        size="small"
        :disabled="isEmpty"
      >
        {{ isExpanded ? '收缩' : '展开' }}
      </el-button>
    </div>
    
    <div class="json-content" :class="{ expanded: isExpanded }">
      <!-- 空数据状态 -->
      <div v-if="isEmpty" class="empty-state">
        <div class="empty-icon">📄</div>
        <div class="empty-title">无JSON数据</div>
        <div class="empty-description">此文件包含{{ emptyTypeDescription }}，没有可显示的内容</div>
      </div>
      
      <!-- 正常JSON显示 -->
      <pre v-else><code>{{ formattedJson }}</code></pre>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { DocumentCopy } from '@element-plus/icons-vue'

const props = defineProps({
  data: {
    type: [Object, Array, String],
    default: () => ({})
  }
})

const isExpanded = ref(true)

// 格式化JSON
const formattedJson = computed(() => {
  try {
    if (typeof props.data === 'string') {
      return JSON.stringify(JSON.parse(props.data), null, 2)
    }
    return JSON.stringify(props.data, null, 2)
  } catch (error) {
    return props.data || 'Invalid JSON'
  }
})

// 切换展开/收缩
const toggleExpand = () => {
  isExpanded.value = !isExpanded.value
}

// 复制JSON
const copyJson = async () => {
  try {
    await navigator.clipboard.writeText(formattedJson.value)
    ElMessage.success('JSON已复制到剪贴板')
  } catch (error) {
    console.error('复制失败:', error)
    ElMessage.error('复制失败')
  }
}

// 检测是否为空数据
const isEmpty = computed(() => {
  return formattedJson.value === null
})

// 获取空数据类型描述
const emptyTypeDescription = computed(() => {
  try {
    const parsedData = typeof props.data === 'string' ? JSON.parse(props.data) : props.data
    if (parsedData === "") return "空字符串"
    if (parsedData === null) return "null值"
    if (Array.isArray(parsedData) && parsedData.length === 0) return "空数组"
    if (typeof parsedData === 'object' && Object.keys(parsedData).length === 0) return "空对象"
    return "无数据"
  } catch {
    return "无效数据"
  }
})
</script>

<style scoped>
.json-viewer {
  height: 100%;
  display: flex;
  flex-direction: column;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  overflow: hidden;
}

.json-toolbar {
  background: #f5f7fa;
  padding: 8px 12px;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.json-content {
  flex: 1;
  overflow: auto;
  background: #fff;
  padding: 16px;
}

.json-content.expanded {
  max-height: none;
}

.json-content pre {
  margin: 0;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 12px;
  line-height: 1.5;
  color: #2c3e50;
}

.json-content code {
  background: none;
  padding: 0;
  border-radius: 0;
  color: inherit;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
  color: #909399;
  min-height: 200px;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.6;
}

.empty-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #606266;
}

.empty-description {
  font-size: 14px;
  color: #909399;
  line-height: 1.4;
}
</style> 