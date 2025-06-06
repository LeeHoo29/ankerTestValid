<template>
  <el-dialog
    v-model="visible"
    :title="dialogTitle"
    width="90%"
    :before-close="handleClose"
    destroy-on-close
  >
    <div class="details-container">
      <!-- 加载状态 -->
      <div v-if="loading" class="loading-container">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>正在加载详细数据...</span>
      </div>
      
      <!-- 按表分组展示数据 -->
      <div v-else-if="Object.keys(tableData).length > 0">
        <div class="summary-info">
          <span class="data-info">
            共查询 {{ Object.keys(tableData).length }} 个表，
            总计 {{ totalRecords }} 条记录
          </span>
        </div>
        
        <!-- 每个表的数据 -->
        <div v-for="(data, tableName) in tableData" :key="tableName" class="table-section">
          <el-card style="margin-bottom: 20px;">
            <template #header>
              <div class="table-header">
                <span class="table-title">📊 {{ tableName.toUpperCase() }}</span>
                <div class="table-header-actions">
                  <span class="table-count">{{ data.details.length }} 条记录</span>
                  <el-button 
                    v-if="props.detailType === 'failed' && getRecrawlableCount(data.details) > 0"
                    type="warning" 
                    size="small"
                    :icon="Refresh"
                    @click="handleBatchRecrawl(data.details, tableName)"
                    style="margin-left: 10px;"
                  >
                    🕷️ 一键重爬 ({{ getRecrawlableCount(data.details) }})
                  </el-button>
                </div>
              </div>
            </template>
            
            <!-- 表格数据 -->
            <el-table 
              v-if="data.details.length > 0"
              :data="data.details" 
              stripe 
              border
              style="width: 100%"
              max-height="400"
              :default-sort="{ prop: 'created_at', order: 'descending' }"
            >
              <el-table-column prop="req_ssn" label="请求SSN" width="200" show-overflow-tooltip />
              <el-table-column prop="status" label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="getStatusType(row.status)">{{ row.status }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="Result" width="180" show-overflow-tooltip>
                <template #default="{ row }">
                  <div class="result-display" :class="getResultDisplayClass(row)">
                    {{ formatResultDisplay(row) }}
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="log_state" label="日志状态" width="120" />
              <el-table-column prop="created_at" label="创建时间" width="160" sortable />
              <el-table-column prop="break_at" label="到期时间" width="160" />
              <el-table-column prop="ext_ssn" label="Task ID" width="200" show-overflow-tooltip />
              <el-table-column label="操作" width="120" fixed="right">
                <template #default="{ row }">
                  <el-button 
                    type="primary" 
                    size="small" 
                    @click="viewPayload(row)"
                    :icon="View"
                    circle
                    title="查看详细信息"
                  />
                  <el-button 
                    v-if="row.show_recrawl_button && props.detailType === 'failed'"
                    type="warning" 
                    size="small"
                    :icon="Refresh"
                    @click="handleRecrawl(row)"
                    circle
                    title="🕷️ 重新提交爬虫任务"
                    style="margin-left: 8px;"
                  />
                </template>
              </el-table-column>
            </el-table>
            
            <!-- 无数据提示 -->
            <div v-else class="no-data">
              <el-empty description="该表暂无数据" />
            </div>
          </el-card>
        </div>
      </div>
      
      <!-- 无数据 -->
      <div v-else class="no-data">
        <el-empty description="暂无数据" />
      </div>
    </div>
    
    <!-- 详情对话框 -->
    <el-dialog
      v-model="payloadDialogVisible"
      title="详细信息"
      width="80%"
      append-to-body
      destroy-on-close
    >
      <div v-if="currentRecord">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="创建时间">{{ currentRecord.created_at }}</el-descriptions-item>
          <el-descriptions-item label="到期时间">{{ currentRecord.break_at || '无' }}</el-descriptions-item>
          <el-descriptions-item label="交付时间">{{ currentRecord.deliver_at || '无' }}</el-descriptions-item>
          <el-descriptions-item label="请求SSN">{{ currentRecord.req_ssn }}</el-descriptions-item>
          <el-descriptions-item label="Task ID">{{ currentRecord.ext_ssn || '无' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(currentRecord.status)">{{ currentRecord.status }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="日志状态">{{ currentRecord.log_state || '无' }}</el-descriptions-item>
          <el-descriptions-item label="来源表">{{ currentRecord.source_table }}</el-descriptions-item>
        </el-descriptions>
        
        <!-- Payload 数据 -->
        <el-divider>
          <span>Payload 数据</span>
          <el-button 
            v-if="currentRecord.payload" 
            type="primary" 
            size="small" 
            style="margin-left: 10px;"
            @click="copyToClipboard(currentRecord.payload, 'Payload')"
          >
            复制
          </el-button>
        </el-divider>
        <div v-if="currentRecord.payload" class="json-container">
          <pre class="json-content">{{ formatJson(currentRecord.payload) }}</pre>
        </div>
        <div v-else class="no-data-text">
          <el-text type="info">无 Payload 数据</el-text>
        </div>
        
        <!-- Analysis Response 数据 -->
        <el-divider>
          <span>Analysis Response 数据</span>
          <el-button 
            v-if="currentRecord.analysis_response" 
            type="primary" 
            size="small" 
            style="margin-left: 10px;"
            @click="copyToClipboard(currentRecord.analysis_response, 'Analysis Response')"
          >
            复制
          </el-button>
        </el-divider>
        <div v-if="currentRecord.analysis_response" class="json-container">
          <pre class="json-content">{{ formatJson(currentRecord.analysis_response) }}</pre>
        </div>
        <div v-else class="no-data-text">
          <el-text type="info">无 Analysis Response 数据</el-text>
        </div>
        
        <!-- Result 数据 -->
        <el-divider>
          <span>Result 数据 (Job表)</span>
          <el-button 
            v-if="currentRecord.result && currentRecord.result.raw" 
            type="primary" 
            size="small" 
            style="margin-left: 10px;"
            @click="copyToClipboard(currentRecord.result.raw, 'Result')"
          >
            复制原始数据
          </el-button>
          <el-button 
            v-if="currentRecord.result && currentRecord.result.formatted" 
            type="success" 
            size="small" 
            style="margin-left: 5px;"
            @click="copyToClipboard(currentRecord.result.formatted, 'Result (格式化)')"
          >
            复制格式化数据
          </el-button>
        </el-divider>
        <div v-if="currentRecord.result && currentRecord.result.raw" class="json-container">
          <div v-if="!currentRecord.result.is_valid_json" class="json-error">
            <el-alert 
              title="JSON格式错误" 
              :description="currentRecord.result.error"
              type="warning"
              show-icon
              :closable="false"
              style="margin-bottom: 10px;"
            />
          </div>
          <pre class="json-content">{{ currentRecord.result.is_valid_json ? currentRecord.result.formatted : currentRecord.result.raw }}</pre>
        </div>
        <div v-else class="no-data-text">
          <el-text type="info">无 Result 数据</el-text>
        </div>
        
        <!-- Response 数据 -->
        <el-divider>
          <span>Response 数据 (Log表)</span>
          <el-button 
            v-if="currentRecord.response && currentRecord.response.raw" 
            type="primary" 
            size="small" 
            style="margin-left: 10px;"
            @click="copyToClipboard(currentRecord.response.raw, 'Response')"
          >
            复制原始数据
          </el-button>
          <el-button 
            v-if="currentRecord.response && currentRecord.response.formatted" 
            type="success" 
            size="small" 
            style="margin-left: 5px;"
            @click="copyToClipboard(currentRecord.response.formatted, 'Response (格式化)')"
          >
            复制格式化数据
          </el-button>
        </el-divider>
        <div v-if="currentRecord.response && currentRecord.response.raw" class="json-container">
          <div v-if="!currentRecord.response.is_valid_json" class="json-error">
            <el-alert 
              title="JSON格式错误" 
              :description="currentRecord.response.error"
              type="warning"
              show-icon
              :closable="false"
              style="margin-bottom: 10px;"
            />
          </div>
          <pre class="json-content">{{ currentRecord.response.is_valid_json ? currentRecord.response.formatted : currentRecord.response.raw }}</pre>
        </div>
        <div v-else class="no-data-text">
          <el-text type="info">无 Response 数据</el-text>
        </div>
      </div>
    </el-dialog>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage, ElMessageBox, ElLoading } from 'element-plus'
import { Loading, View, Refresh } from '@element-plus/icons-vue'
import { getStatisticsDetails } from '@/api/statistics'

// Props
const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  filterParams: {
    type: Object,
    required: true
  },
  detailType: {
    type: String,
    required: true
  },
  targetDate: {
    type: String,
    required: true
  },
  count: {
    type: Number,
    default: 0
  }
})

// Emits
const emit = defineEmits(['update:modelValue'])

// 响应式数据
const loading = ref(false)
const tableData = ref({}) // 按表分组的数据
const payloadDialogVisible = ref(false)
const currentRecord = ref(null)

// 计算属性
const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const dialogTitle = computed(() => {
  const typeMap = {
    'failed': '失败',
    'timeout': '超时', 
    'failed_timeout': '失败或超时',
    'succeed': '已完成',
    'timeout_but_succeed': '延期完成',
    'succeed_not_timeout': '按时完成',
    'timeout_not_succeed': '超时未完成'
  }
  return `${typeMap[props.detailType] || '详细'}数据 - ${props.targetDate} (${props.count}条)`
})

const totalRecords = computed(() => {
  return Object.values(tableData.value).reduce((total, data) => total + data.details.length, 0)
})

// 方法
const handleClose = () => {
  visible.value = false
  tableData.value = {}
}

const getStatusType = (status) => {
  const typeMap = {
    'FAILED': 'danger',
    'SUCCESS': 'success',
    'RUNNING': 'warning',
    'PENDING': 'info'
  }
  return typeMap[status] || 'info'
}

const viewPayload = (record) => {
  currentRecord.value = record
  payloadDialogVisible.value = true
}

// JSON格式化方法
const formatJson = (jsonString) => {
  if (!jsonString) return ''
  
  try {
    // 尝试解析JSON并格式化
    const parsed = JSON.parse(jsonString)
    return JSON.stringify(parsed, null, 2)
  } catch (error) {
    // 如果不是有效的JSON，直接返回原字符串
    return jsonString
  }
}

// 复制到剪贴板
const copyToClipboard = async (text, type) => {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success(`${type} 数据已复制到剪贴板`)
  } catch (error) {
    console.error('复制失败:', error)
    ElMessage.error('复制失败，请手动选择复制')
  }
}

// 格式化Result显示
const formatResultDisplay = (row) => {
  // 首先检查是否是特殊的408 IO超时错误
  if (row.status === 'FAILED' && row.result && row.result.raw) {
    try {
      const resultData = typeof row.result.raw === 'string' 
        ? JSON.parse(row.result.raw) 
        : row.result.raw
      
      if (resultData && resultData.E3001) {
        const errorMsg = resultData.E3001
        if (errorMsg.includes('408 IORuntimeException - SocketTimeoutException: connect timed out')) {
          return '408 IO超时'
        }
      }
    } catch (error) {
      // JSON解析失败，继续后续处理
    }
  }
  
  // 尝试显示Result数据
  if (row.result && row.result.raw) {
    const resultText = row.result.is_valid_json ? row.result.formatted : row.result.raw
    // 如果内容太长，截取前100个字符
    if (resultText.length > 100) {
      return resultText.substring(0, 100) + '...'
    }
    return resultText
  }
  
  // 如果没有Result数据，尝试显示Response数据
  if (row.response && row.response.raw) {
    const responseText = row.response.is_valid_json ? row.response.formatted : row.response.raw
    // 如果内容太长，截取前100个字符
    if (responseText.length > 100) {
      return responseText.substring(0, 100) + '...'
    }
    return responseText
  }
  
  return '无数据'
}

// 获取Result显示的样式类
const getResultDisplayClass = (row) => {
  // 检查是否是408 IO超时错误
  if (row.status === 'FAILED' && row.result && row.result.raw) {
    try {
      const resultData = typeof row.result.raw === 'string' 
        ? JSON.parse(row.result.raw) 
        : row.result.raw
      
      if (resultData && resultData.E3001) {
        const errorMsg = resultData.E3001
        if (errorMsg.includes('408 IORuntimeException - SocketTimeoutException: connect timed out')) {
          return 'timeout-highlight'
        }
      }
    } catch (error) {
      // JSON解析失败，返回默认样式
    }
  }
  
  return ''
}

// 重爬处理函数
const handleRecrawl = async (record) => {
  try {
    // 确认对话框
    await ElMessageBox.confirm(
      `确定要重新提交爬虫任务吗？\n\n任务ID: ${record.req_ssn}\n状态: ${record.status}`,
      '确认重爬',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    // 发送重爬请求
    const response = await fetch('/api/resubmit_crawler', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        req_ssn: record.req_ssn
      })
    })
    
    const result = await response.json()
    
    if (result.success) {
      ElMessage.success(`重爬任务提交成功！任务ID: ${result.job_id}`)
      console.log('重爬命令执行:', result.command)
    } else {
      ElMessage.error(`重爬任务提交失败: ${result.message}`)
      console.error('重爬失败:', result)
    }
    
  } catch (error) {
    if (error !== 'cancel') {
      console.error('重爬操作失败:', error)
      ElMessage.error('重爬操作失败，请稍后重试')
    }
  }
}

// 获取可重爬记录数量
const getRecrawlableCount = (details) => {
  return details.filter(row => row.show_recrawl_button).length
}

// 批量重爬处理函数
const handleBatchRecrawl = async (details, tableName) => {
  try {
    // 获取所有可重爬的记录
    const recrawlableRecords = details.filter(row => row.show_recrawl_button)
    
    if (recrawlableRecords.length === 0) {
      ElMessage.warning('没有可重爬的记录')
      return
    }
    
    // 确认对话框
    await ElMessageBox.confirm(
      `确定要批量重新提交爬虫任务吗？\n\n表: ${tableName.toUpperCase()}\n任务数量: ${recrawlableRecords.length} 个\n\n这将对所有满足重爬条件的失败任务进行重新提交。`,
      '确认批量重爬',
      {
        confirmButtonText: '确定执行',
        cancelButtonText: '取消',
        type: 'warning',
        dangerouslyUseHTMLString: true
      }
    )
    
    // 显示进度提示
    const loading = ElLoading.service({
      lock: true,
      text: `正在批量提交重爬任务... (0/${recrawlableRecords.length})`,
      background: 'rgba(0, 0, 0, 0.7)'
    })
    
    let successCount = 0
    let failureCount = 0
    const results = []
    
    // 逐个提交重爬请求
    for (let i = 0; i < recrawlableRecords.length; i++) {
      const record = recrawlableRecords[i]
      
      // 更新进度
      loading.setText(`正在批量提交重爬任务... (${i + 1}/${recrawlableRecords.length})`)
      
      try {
        const response = await fetch('/api/resubmit_crawler', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            req_ssn: record.req_ssn
          })
        })
        
        const result = await response.json()
        
        if (result.success) {
          successCount++
          results.push({
            req_ssn: record.req_ssn,
            status: 'success',
            message: result.message
          })
          console.log(`✅ 重爬成功: ${record.req_ssn}`)
        } else {
          failureCount++
          results.push({
            req_ssn: record.req_ssn,
            status: 'error',
            message: result.message
          })
          console.error(`❌ 重爬失败: ${record.req_ssn} - ${result.message}`)
        }
        
        // 添加延迟避免请求过于频繁
        if (i < recrawlableRecords.length - 1) {
          await new Promise(resolve => setTimeout(resolve, 200))
        }
        
      } catch (error) {
        failureCount++
        results.push({
          req_ssn: record.req_ssn,
          status: 'error',
          message: error.message
        })
        console.error(`💥 重爬请求异常: ${record.req_ssn}`, error)
      }
    }
    
    loading.close()
    
    // 显示结果
    const successRate = ((successCount / recrawlableRecords.length) * 100).toFixed(1)
    if (successCount === recrawlableRecords.length) {
      ElMessage.success(`🎉 批量重爬完成！成功提交 ${successCount} 个任务`)
    } else {
      ElMessage.warning(`批量重爬完成！成功 ${successCount} 个，失败 ${failureCount} 个 (成功率: ${successRate}%)`)
    }
    
    console.log('📊 批量重爬结果汇总:', {
      total: recrawlableRecords.length,
      success: successCount,
      failure: failureCount,
      successRate: `${successRate}%`,
      results: results
    })
    
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量重爬操作失败:', error)
      ElMessage.error('批量重爬操作失败，请稍后重试')
    }
  }
}

// 加载详细数据
const loadDetails = async () => {
  if (!props.filterParams || !props.detailType || !props.targetDate) {
    return
  }
  
  loading.value = true
  tableData.value = {}
  
  try {
    // 定义要查询的表
    const tables = ['job_a', 'job_b', 'job_c', 'job_d']
    
    // 并行查询所有表
    const promises = tables.map(table => 
      getStatisticsDetails({
        ...props.filterParams,
        detail_type: props.detailType,
        date: props.targetDate,
        table: table, // 指定查询的表
        page: 1,
        page_size: 50 // 每个表最多显示50条
      }).catch(error => {
        console.error(`查询表 ${table} 失败:`, error)
        return { data: { details: [] } }
      })
    )
    
    const results = await Promise.all(promises)
    
    // 处理结果
    results.forEach((result, index) => {
      const tableName = tables[index]
      const details = result.data?.details || []
      
      tableData.value[tableName] = {
        details: details,
        total: details.length
      }
    })
    
  } catch (error) {
    console.error('加载详细数据失败:', error)
    ElMessage.error('加载详细数据失败')
  } finally {
    loading.value = false
  }
}

// 监听对话框打开
watch(visible, (newValue) => {
  if (newValue) {
    loadDetails()
  }
})
</script>

<style scoped>
.details-container {
  max-height: 70vh;
  overflow-y: auto;
}

.loading-container {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  font-size: 16px;
  color: #666;
}

.loading-container .el-icon {
  margin-right: 10px;
  font-size: 20px;
}

.summary-info {
  margin-bottom: 20px;
  padding: 10px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.data-info {
  font-size: 14px;
  color: #606266;
}

.table-section {
  margin-bottom: 20px;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.table-header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.table-title {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
}

.table-count {
  font-size: 14px;
  color: #909399;
}

.no-data {
  text-align: center;
  padding: 40px;
}

.json-container {
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  background-color: #f8f9fa;
  margin-bottom: 20px;
}

.json-content {
  padding: 15px;
  margin: 0;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 12px;
  line-height: 1.5;
  color: #2c3e50;
  background-color: transparent;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.no-data-text {
  padding: 20px;
  text-align: center;
  background-color: #f8f9fa;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  margin-bottom: 20px;
}

.json-error {
  margin-bottom: 10px;
}

.no-recrawl {
  color: #c0c4cc;
  font-size: 12px;
}

.result-display {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 12px;
  line-height: 1.4;
  max-width: 100%;
  overflow: hidden;
  white-space: pre-wrap;
  word-break: break-all;
}

.timeout-highlight {
  background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
  color: #e17055;
  font-weight: bold;
  padding: 4px 8px;
  border-radius: 4px;
  border: 1px solid #fdcb6e;
  box-shadow: 0 1px 3px rgba(253, 203, 110, 0.3);
  position: relative;
}

.timeout-highlight::before {
  content: "⚠️";
  margin-right: 4px;
  font-size: 10px;
}
</style> 