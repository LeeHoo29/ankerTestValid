<template>
  <div class="database-manager">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>📊 数据库管理</span>
          <el-button 
            type="primary" 
            @click="refreshData"
            :loading="loading"
            size="small"
          >
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>

      <!-- 数据库状态信息 -->
      <el-row :gutter="20" style="margin-bottom: 20px;">
        <el-col :span="6">
          <el-statistic 
            title="数据库状态" 
            :value="dbStatus.connected ? '已连接' : '未连接'"
            :value-style="{ color: dbStatus.connected ? '#67c23a' : '#f56c6c' }"
          />
        </el-col>
        <el-col :span="6">
          <el-statistic 
            title="总记录数" 
            :value="statistics.total_mappings || 0"
            suffix="条"
          />
        </el-col>
        <el-col :span="6">
          <el-statistic 
            title="商品任务" 
            :value="getTaskTypeCount('AmazonListingJob')"
            suffix="条"
          />
        </el-col>
        <el-col :span="6">
          <el-statistic 
            title="评论任务" 
            :value="getTaskTypeCount('AmazonReviewStarJob')"
            suffix="条"
          />
        </el-col>
      </el-row>

      <!-- 搜索和过滤 -->
      <el-row :gutter="10" style="margin-bottom: 20px;">
        <el-col :span="8">
          <el-input
            v-model="searchQuery"
            placeholder="搜索 Job ID 或任务类型"
            clearable
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-col>
        <el-col :span="4">
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
        </el-col>
        <el-col :span="4">
          <el-select v-model="taskTypeFilter" placeholder="任务类型筛选" clearable>
            <el-option label="全部" value="" />
            <el-option label="商品任务" value="AmazonListingJob" />
            <el-option label="评论任务" value="AmazonReviewStarJob" />
          </el-select>
        </el-col>
      </el-row>

      <!-- 数据表格 -->
      <el-table 
        :data="mappings" 
        style="width: 100%"
        :loading="loading"
        empty-text="暂无数据"
      >
        <el-table-column prop="job_id" label="Job ID" width="120" />
        <el-table-column prop="task_type" label="任务类型" width="150">
          <template #default="scope">
            <el-tag 
              :type="scope.row.task_type === 'AmazonListingJob' ? 'success' : 'warning'"
              size="small"
            >
              {{ scope.row.task_type === 'AmazonListingJob' ? '商品任务' : '评论任务' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="actual_task_id" label="实际任务ID" width="200" show-overflow-tooltip />
        <el-table-column prop="file_count" label="文件数量" width="80" align="center" />
        <el-table-column prop="has_parse_file" label="解析文件" width="80" align="center">
          <template #default="scope">
            <el-tag 
              :type="scope.row.has_parse_file ? 'success' : 'info'"
              size="small"
            >
              {{ scope.row.has_parse_file ? '有' : '无' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80" align="center">
          <template #default="scope">
            <el-tag 
              :type="scope.row.status === 'success' ? 'success' : 'danger'"
              size="small"
            >
              {{ scope.row.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="160" show-overflow-tooltip>
          <template #default="scope">
            {{ formatDate(scope.row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="scope">
            <el-button 
              type="primary" 
              size="small" 
              @click="viewDetails(scope.row)"
            >
              <el-icon><View /></el-icon>
              详情
            </el-button>
            <el-button 
              type="success" 
              size="small" 
              @click="openFiles(scope.row)"
              v-if="scope.row.file_count > 0"
            >
              <el-icon><Document /></el-icon>
              文件
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        v-if="pagination.total > 0"
        style="margin-top: 20px; text-align: center;"
        :current-page="pagination.page"
        :page-size="pagination.per_page"
        :total="pagination.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="任务映射详情"
      width="60%"
      destroy-on-close
    >
      <div v-if="selectedMapping">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="Job ID">{{ selectedMapping.job_id }}</el-descriptions-item>
          <el-descriptions-item label="任务类型">{{ selectedMapping.task_type }}</el-descriptions-item>
          <el-descriptions-item label="实际任务ID">{{ selectedMapping.actual_task_id }}</el-descriptions-item>
          <el-descriptions-item label="相对路径">{{ selectedMapping.relative_path }}</el-descriptions-item>
          <el-descriptions-item label="完整路径">{{ selectedMapping.full_path }}</el-descriptions-item>
          <el-descriptions-item label="文件数量">{{ selectedMapping.file_count }}</el-descriptions-item>
          <el-descriptions-item label="解析文件">
            <el-tag :type="selectedMapping.has_parse_file ? 'success' : 'info'" size="small">
              {{ selectedMapping.has_parse_file ? '有' : '无' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="下载方式">{{ selectedMapping.download_method || 'azure_storage' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="selectedMapping.status === 'success' ? 'success' : 'danger'" size="small">
              {{ selectedMapping.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDate(selectedMapping.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ formatDate(selectedMapping.updated_at) }}</el-descriptions-item>
          <el-descriptions-item label="数据源">
            <el-tag :type="selectedMapping.source === 'database' ? 'primary' : 'warning'" size="small">
              {{ selectedMapping.source === 'database' ? '数据库' : 'JSON文件' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <!-- 文件列表 -->
        <div style="margin-top: 20px;" v-if="selectedMapping.files && selectedMapping.files.length > 0">
          <h4>文件列表</h4>
          <el-table :data="selectedMapping.files" size="small">
            <el-table-column prop="file_name" label="文件名" show-overflow-tooltip />
            <el-table-column prop="file_type" label="类型" width="80">
              <template #default="scope">
                <el-tag :type="scope.row.file_type === 'parse' ? 'primary' : 'info'" size="small">
                  {{ scope.row.file_type === 'parse' ? '解析' : '原始' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="file_size" label="大小" width="100">
              <template #default="scope">
                {{ formatFileSize(scope.row.file_size) }}
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="160">
              <template #default="scope">
                {{ formatDate(scope.row.created_at) }}
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Search, View, Document } from '@element-plus/icons-vue'
import axios from 'axios'

// 响应式数据
const loading = ref(false)
const detailDialogVisible = ref(false)
const selectedMapping = ref(null)
const searchQuery = ref('')
const taskTypeFilter = ref('')

const dbStatus = reactive({
  available: false,
  connected: false,
  reason: ''
})

const statistics = reactive({
  total_mappings: 0,
  task_type_distribution: [],
  last_updated: null
})

const mappings = ref([])
const pagination = reactive({
  page: 1,
  per_page: 20,
  total: 0,
  pages: 0
})

// 计算属性
const getTaskTypeCount = computed(() => {
  return (taskType) => {
    const distribution = statistics.task_type_distribution || []
    const item = distribution.find(d => d.task_type === taskType)
    return item ? item.count : 0
  }
})

// 方法
const fetchDatabaseStatus = async () => {
  try {
    const response = await axios.get('/api/database_status')
    if (response.data.success) {
      Object.assign(dbStatus, response.data.data)
      if (response.data.data.statistics) {
        Object.assign(statistics, response.data.data.statistics)
      }
    }
  } catch (error) {
    console.error('获取数据库状态失败:', error)
    ElMessage.error('获取数据库状态失败')
  }
}

const fetchMappings = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      per_page: pagination.per_page
    }
    
    if (searchQuery.value) {
      params.search = searchQuery.value
    }

    const response = await axios.get('/api/task_mappings', { params })
    
    if (response.data.success) {
      mappings.value = response.data.data
      Object.assign(pagination, response.data.pagination)
      
      ElMessage.success(`成功加载 ${mappings.value.length} 条记录 (来源: ${response.data.source === 'database' ? '数据库' : 'JSON文件'})`)
    } else {
      ElMessage.error('获取任务映射失败')
    }
  } catch (error) {
    console.error('获取任务映射失败:', error)
    ElMessage.error('获取任务映射失败')
  } finally {
    loading.value = false
  }
}

const refreshData = async () => {
  await fetchDatabaseStatus()
  await fetchMappings()
}

const handleSearch = () => {
  pagination.page = 1
  fetchMappings()
}

const handleSizeChange = (size) => {
  pagination.per_page = size
  pagination.page = 1
  fetchMappings()
}

const handleCurrentChange = (page) => {
  pagination.page = page
  fetchMappings()
}

const viewDetails = async (row) => {
  try {
    const response = await axios.get(`/api/task_mapping/${row.job_id}`)
    if (response.data.success) {
      selectedMapping.value = response.data.data
      detailDialogVisible.value = true
    } else {
      ElMessage.error('获取详情失败')
    }
  } catch (error) {
    console.error('获取详情失败:', error)
    ElMessage.error('获取详情失败')
  }
}

const openFiles = (row) => {
  // 这里可以实现打开文件浏览器的逻辑
  ElMessage.info(`打开任务 ${row.job_id} 的文件目录: ${row.relative_path}`)
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`
}

// 生命周期
onMounted(() => {
  refreshData()
})
</script>

<style scoped>
.database-manager {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.el-statistic {
  text-align: center;
}

.el-table {
  font-size: 12px;
}
</style> 