<template>
  <div class="json-viewer">
    <div class="json-toolbar">
      <el-button 
        link
        :icon="DocumentCopy" 
        @click="copyJson"
        size="small"
      >
        复制
      </el-button>
      <el-button 
        link
        :icon="isExpanded ? 'Minus' : 'Plus'" 
        @click="toggleExpand"
        size="small"
      >
        {{ isExpanded ? '收缩' : '展开' }}
      </el-button>
    </div>
    
    <div class="json-content" :class="{ expanded: isExpanded }">
      <pre><code>{{ formattedJson }}</code></pre>
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
</style> 