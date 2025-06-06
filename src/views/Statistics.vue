<template>
  <div class="statistics-container">
    <el-card class="page-header">
      <h2>📊 任务统计</h2>
      <p>查看各任务类型的执行统计数据</p>
    </el-card>

    <!-- 筛选条件 -->
    <el-card class="filter-card">
      <template #header>
        <span>筛选条件</span>
      </template>
      
      <div v-if="configLoading" class="config-loading">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>正在加载配置...</span>
      </div>
      
      <el-form v-else :model="filterForm" label-width="120px" inline>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            @change="onDateRangeChange"
          />
        </el-form-item>
        
        <el-form-item label="租户">
          <el-select
            v-model="filterForm.tenant_ids"
            multiple
            placeholder="请选择租户"
            style="width: 300px"
            :disabled="tenants.length === 0"
          >
            <el-option
              v-for="tenant in tenants"
              :key="tenant.id"
              :label="tenant.display_name"
              :value="tenant.id"
            />
          </el-select>
          <span v-if="tenants.length === 0" class="empty-hint">暂无租户数据</span>
        </el-form-item>
        
        <el-form-item label="任务类型">
          <el-select
            v-model="filterForm.task_type"
            placeholder="请选择任务类型"
            style="width: 300px"
            :disabled="taskTypes.length === 0"
          >
            <el-option
              v-for="taskType in taskTypes"
              :key="taskType"
              :label="taskType"
              :value="taskType"
            />
          </el-select>
          <span v-if="taskTypes.length === 0" class="empty-hint">暂无任务类型数据</span>
        </el-form-item>
        
        <el-form-item>
          <el-button 
            type="primary" 
            :icon="Search" 
            @click="loadStatistics"
            :loading="loading"
            :disabled="tenants.length === 0 || taskTypes.length === 0"
          >
            查询
          </el-button>
          <el-button 
            :icon="Refresh" 
            @click="resetFilter"
            :disabled="tenants.length === 0 || taskTypes.length === 0"
          >
            重置
          </el-button>
          <el-button 
            :icon="Refresh" 
            @click="loadConfig"
            :loading="configLoading"
          >
            重新加载配置
          </el-button>
          <span v-if="loading" class="loading-hint">
            📊 正在查询统计数据，请耐心等待（可能需要1-2分钟）...
          </span>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 数据状态信息 -->
    <div class="data-status" v-if="cacheTime">
      <div class="cache-info">
        <div class="cache-time">
          <el-icon><Clock /></el-icon>
          <span>数据时间: {{ cacheTime }}</span>
          <el-tag v-if="fromCache" type="success" size="small">来自缓存</el-tag>
          <el-tag v-else type="info" size="small">最新数据</el-tag>
        </div>
        <el-button 
          type="primary" 
          size="small" 
          :icon="Refresh" 
          @click="refreshData"
          :loading="refreshing"
          plain
        >
          刷新数据
        </el-button>
      </div>
      <el-divider style="margin: 10px 0;">
        <span style="color: #909399; font-size: 12px;">以下数据基于上述时间</span>
      </el-divider>
    </div>

    <!-- 汇总数据 -->
    <el-card class="summary-card" v-if="summaryData && Object.keys(summaryData).length > 0">
      <template #header>
        <span>📈 汇总统计</span>
      </template>
      
      <!-- 新的布局：左侧饼图，右侧统计卡片 -->
      <el-row :gutter="30">
        <!-- 左侧：饼图 -->
        <el-col :span="10">
          <div class="chart-container">
            <h4 class="chart-title">任务状态分布</h4>
            <div ref="pieChart" style="height: 400px;"></div>
          </div>
        </el-col>
        
        <!-- 右侧：统计卡片 -->
        <el-col :span="14">
          <div class="summary-cards-container">
            <div 
              class="summary-card-item" 
              v-for="(data, taskType) in summaryData" 
              :key="taskType"
            >
              <div class="card-header">
                <h4>{{ taskType }}</h4>
                <div class="success-rate">
                  完成率: {{ calculateSuccessRate(data) }}%
                </div>
              </div>
              
              <div class="summary-stats-grid">
                <!-- 第一行：总数和已完成 -->
                <div class="stat-row">
                  <div class="stat-item total">
                    <span class="label">总数</span>
                    <span class="value">{{ data.total_count }}</span>
                  </div>
                  <div class="stat-item success">
                    <span class="label">已完成</span>
                    <span class="value">{{ data.succeed_count }}</span>
                    <span class="sub-label">({{ calculatePercentage(data.succeed_count, data.total_count) }}%)</span>
                  </div>
                </div>
                
                <!-- 第二行：已完成的细分 -->
                <div class="stat-row sub-stats">
                  <div class="stat-item success-detail">
                    <span class="label">按时完成</span>
                    <span class="value">{{ data.succeed_not_timeout }}</span>
                    <span class="sub-label">({{ calculatePercentage(data.succeed_not_timeout, data.total_count) }}%)</span>
                  </div>
                  <div class="stat-item warning">
                    <span class="label">延期完成</span>
                    <span class="value">{{ data.timeout_but_succeed }}</span>
                    <span class="sub-label">({{ calculatePercentage(data.timeout_but_succeed, data.total_count) }}%)</span>
                  </div>
                </div>
                
                <!-- 第三行：未完成和失败 -->
                <div class="stat-row">
                  <div class="stat-item incomplete">
                    <span class="label">未完成</span>
                    <span class="value">{{ data.total_count - data.succeed_count }}</span>
                    <span class="sub-label">({{ calculatePercentage(data.total_count - data.succeed_count, data.total_count) }}%)</span>
                  </div>
                  <div class="stat-item failed">
                    <span class="label">失败</span>
                    <span class="value">{{ data.failed_count }}</span>
                    <span class="sub-label">({{ calculatePercentage(data.failed_count, data.total_count) }}%)</span>
                  </div>
                </div>
                
                <!-- 第四行：未完成的细分 -->
                <div class="stat-row sub-stats">
                  <div class="stat-item danger">
                    <span class="label">超时未完成</span>
                    <span class="value">{{ data.timeout_not_succeed }}</span>
                    <span class="sub-label">({{ calculatePercentage(data.timeout_not_succeed, data.total_count) }}%)</span>
                  </div>
                  <div class="stat-item processing">
                    <span class="label">正常进行中</span>
                    <span class="value">{{ calculateProcessingCount(data) }}</span>
                    <span class="sub-label">({{ calculatePercentage(calculateProcessingCount(data), data.total_count) }}%)</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 详细统计图表 -->
    <el-card v-if="statisticsData" style="margin-bottom: 20px;">
      <template #header>
        <span>📈 {{ filterForm.task_type || 'AmazonListingJob' }} 趋势分析</span>
      </template>
      <div ref="trendChart" style="height: 500px;"></div>
    </el-card>

    <!-- 详细数据 -->
    <el-card v-if="statisticsData" style="margin-top: 20px;">
      <template #header>
        <span>📋 详细数据</span>
      </template>
      
      <el-table 
        :data="mergedTableData" 
        stripe 
        border
        style="width: 100%"
        :default-sort="{ prop: 'date', order: 'descending' }"
      >
        <el-table-column 
          prop="date" 
          label="日期" 
          width="120"
          sortable
        />
        
        <el-table-column 
          label="失败" 
          width="150"
          align="center"
        >
          <template #default="{ row }">
            <div class="stat-cell">
              <el-tag :type="getTagType(row.failed_count)" size="small">
                {{ row.failed_count }}
              </el-tag>
              <span class="percentage">{{ calculatePercentage(row.failed_count, row.total_count) }}%</span>
              <el-button 
                link 
                :icon="View" 
                size="small"
                @click="viewDetails('failed', row.date, row.failed_count)"
                title="查看详情"
              />
            </div>
          </template>
        </el-table-column>
        
        <el-table-column 
          label="超时" 
          width="150"
          align="center"
        >
          <template #default="{ row }">
            <div class="stat-cell">
              <el-tag :type="getTagType(row.timeout_count)" size="small">
                {{ row.timeout_count }}
              </el-tag>
              <span class="percentage">{{ calculatePercentage(row.timeout_count, row.total_count) }}%</span>
              <el-button 
                link 
                :icon="View" 
                size="small"
                @click="viewDetails('timeout', row.date, row.timeout_count)"
                title="查看详情"
              />
            </div>
          </template>
        </el-table-column>
        
        <el-table-column 
          label="延期完成" 
          width="180"
          align="center"
        >
          <template #default="{ row }">
            <div class="stat-cell">
              <el-tag :type="getTagType(row.timeout_but_succeed)" size="small">
                {{ row.timeout_but_succeed }}
              </el-tag>
              <span class="percentage">{{ calculatePercentage(row.timeout_but_succeed, row.total_count) }}%</span>
              <el-button 
                link 
                :icon="View" 
                size="small"
                @click="viewDetails('timeout_but_succeed', row.date, row.timeout_but_succeed)"
                title="查看详情"
              />
            </div>
          </template>
        </el-table-column>
        
        <el-table-column 
          label="按时完成" 
          width="180"
          align="center"
        >
          <template #default="{ row }">
            <div class="stat-cell">
              <el-tag type="success" size="small">
                {{ row.succeed_not_timeout }}
              </el-tag>
              <span class="percentage">{{ calculatePercentage(row.succeed_not_timeout, row.total_count) }}%</span>
              <el-button 
                link 
                :icon="View" 
                size="small"
                @click="viewDetails('succeed_not_timeout', row.date, row.succeed_not_timeout)"
                title="查看详情"
              />
            </div>
          </template>
        </el-table-column>
        
        <el-table-column 
          label="超时未完成" 
          width="180"
          align="center"
        >
          <template #default="{ row }">
            <div class="stat-cell">
              <el-tag type="danger" size="small">
                {{ row.timeout_not_succeed }}
              </el-tag>
              <span class="percentage">{{ calculatePercentage(row.timeout_not_succeed, row.total_count) }}%</span>
              <el-button 
                link 
                :icon="View" 
                size="small"
                @click="viewDetails('timeout_not_succeed', row.date, row.timeout_not_succeed)"
                title="查看详情"
              />
            </div>
          </template>
        </el-table-column>
        
        <el-table-column 
          label="已完成" 
          width="150"
          align="center"
        >
          <template #default="{ row }">
            <div class="stat-cell">
              <el-tag type="success" size="small">
                {{ row.succeed_count }}
              </el-tag>
              <span class="percentage">{{ calculatePercentage(row.succeed_count, row.total_count) }}%</span>
              <el-button 
                link 
                :icon="View" 
                size="small"
                @click="viewDetails('succeed', row.date, row.succeed_count)"
                title="查看详情"
              />
            </div>
          </template>
        </el-table-column>
        
        <el-table-column 
          label="总数" 
          width="120"
          align="center"
          sortable
          prop="total_count"
        >
          <template #default="{ row }">
            <el-tag type="info" size="small">
              {{ row.total_count }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div class="pagination-container" v-if="mergedTableData.length > pageSize">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="mergedTableData.length"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 调试信息 -->
    <el-card v-if="debugInfo.length > 0" style="margin-top: 20px;">
      <template #header>
        <div style="display: flex; align-items: center; justify-content: space-between;">
          <span>🔧 调试信息</span>
          <el-button 
            size="small" 
            @click="showDebugInfo = !showDebugInfo"
            :icon="showDebugInfo ? 'ArrowUp' : 'ArrowDown'"
          >
            {{ showDebugInfo ? '收起' : '展开' }}
          </el-button>
        </div>
      </template>
      
      <div v-show="showDebugInfo">
        <el-collapse v-model="activeDebugItems">
          <el-collapse-item 
            v-for="(debug, index) in debugInfo" 
            :key="index"
            :title="`表: ${debug.table} (查询时间: ${debug.query_time})`"
            :name="index"
          >
            <div class="debug-content">
              <h4>SQL查询:</h4>
              <pre class="sql-code">{{ debug.sql }}</pre>
              <h4>参数:</h4>
              <pre class="params-code">{{ JSON.stringify(debug.params, null, 2) }}</pre>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>
    </el-card>
  </div>
  
  <!-- 详细数据对话框 -->
  <StatisticsDetailsDialog
    v-model="detailsDialogVisible"
    :filter-params="filterForm"
    :detail-type="currentDetailType"
    :target-date="currentDetailDate"
    :count="currentDetailCount"
  />
</template>

<script setup>
import { ref, reactive, onMounted, nextTick, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Refresh, Loading, Clock, View } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { getStatisticsConfig, getStatisticsData, getStatisticsSummary } from '@/api/statistics'
import StatisticsDetailsDialog from '@/components/StatisticsDetailsDialog.vue'

// 响应式数据
const loading = ref(false)
const refreshing = ref(false)
const configLoading = ref(false)
const tenants = ref([])
const taskTypes = ref([])
const dateRange = ref([])
const cacheTime = ref('')
const fromCache = ref(false)
const debugInfo = ref([])
const showDebugInfo = ref(false)
const activeDebugItems = ref([])

// 详细数据对话框相关
const detailsDialogVisible = ref(false)
const currentDetailType = ref('')
const currentDetailDate = ref('')
const currentDetailCount = ref(0)

// 分页相关
const currentPage = ref(1)
const pageSize = ref(20)

// 筛选表单
const filterForm = reactive({
  start_date: '',
  end_date: '',
  tenant_ids: [],
  task_type: ''
})

// 统计数据
const statisticsData = ref(null)
const summaryData = ref(null)

// 合并后的表格数据
const mergedTableData = computed(() => {
  if (!statisticsData.value) return []
  
  // 按日期合并数据
  const dateMap = new Map()
  
  // 处理总数数据
  statisticsData.value.total_count.forEach(item => {
    if (!dateMap.has(item.date)) {
      dateMap.set(item.date, {
        date: item.date,
        total_count: 0,
        failed_count: 0,
        timeout_count: 0,
        timeout_but_succeed: 0,
        succeed_count: 0,
        succeed_not_timeout: 0,
        timeout_not_succeed: 0
      })
    }
    dateMap.get(item.date).total_count += Number(item.count) || 0
  })
  
  // 处理失败数据
  statisticsData.value.failed_count.forEach(item => {
    if (dateMap.has(item.date)) {
      dateMap.get(item.date).failed_count += Number(item.count) || 0
    }
  })
  
  // 处理超时数据
  statisticsData.value.timeout_count.forEach(item => {
    if (dateMap.has(item.date)) {
      dateMap.get(item.date).timeout_count += Number(item.count) || 0
    }
  })
  
  // 处理已超时但已完成数据
  statisticsData.value.timeout_but_succeed.forEach(item => {
    if (dateMap.has(item.date)) {
      dateMap.get(item.date).timeout_but_succeed += Number(item.count) || 0
    }
  })
  
  // 处理已完成数据
  statisticsData.value.succeed_count.forEach(item => {
    if (dateMap.has(item.date)) {
      dateMap.get(item.date).succeed_count += Number(item.count) || 0
    }
  })
  
  // 处理未超时且已完成数据
  statisticsData.value.succeed_not_timeout.forEach(item => {
    if (dateMap.has(item.date)) {
      dateMap.get(item.date).succeed_not_timeout += Number(item.count) || 0
    }
  })
  
  // 处理超时未完成数据
  statisticsData.value.timeout_not_succeed.forEach(item => {
    if (dateMap.has(item.date)) {
      dateMap.get(item.date).timeout_not_succeed += Number(item.count) || 0
    }
  })
  
  // 转换为数组并排序
  const result = Array.from(dateMap.values())
  return result.sort((a, b) => new Date(b.date) - new Date(a.date))
})

// 图表引用
const trendChart = ref(null)
const pieChart = ref(null)

// 图表实例
let charts = {
  trend: null,
  pie: null
}

// 初始化默认时间范围（三天前到今天）
const initDefaultDateRange = () => {
  const today = new Date()
  const threeDaysAgo = new Date(today.getTime() - 3 * 24 * 60 * 60 * 1000)
  
  const formatDate = (date) => {
    return date.toISOString().split('T')[0]
  }
  
  filterForm.start_date = formatDate(threeDaysAgo)
  filterForm.end_date = formatDate(today)
  dateRange.value = [filterForm.start_date, filterForm.end_date]
}

// 日期范围变化处理
const onDateRangeChange = (dates) => {
  if (dates && dates.length === 2) {
    filterForm.start_date = dates[0]
    filterForm.end_date = dates[1]
  } else {
    filterForm.start_date = ''
    filterForm.end_date = ''
  }
}

// 加载配置信息
const loadConfig = async () => {
  configLoading.value = true
  try {
    const response = await getStatisticsConfig()
    
    if (response && response.success && response.data) {
      const { tenants: tenantsData, task_types: taskTypesData } = response.data
      
      if (Array.isArray(tenantsData) && Array.isArray(taskTypesData)) {
        tenants.value = tenantsData
        taskTypes.value = taskTypesData
        
        // 默认选择Anker租户和AmazonListingJob任务类型
        const defaultTenant = tenants.value.find(t => t.id === 'Anker')
        const defaultTaskType = 'AmazonListingJob'
        
        filterForm.tenant_ids = defaultTenant ? [defaultTenant.id] : []
        filterForm.task_type = taskTypes.value.includes(defaultTaskType) ? defaultTaskType : ''
        
        ElMessage.success('配置加载成功')
      } else {
        console.error('配置数据格式错误 - 租户或任务类型不是数组:', { tenantsData, taskTypesData })
        ElMessage.error('配置数据格式错误')
      }
    } else {
      console.error('配置响应格式错误:', response)
      ElMessage.error('配置数据格式错误')
    }
  } catch (error) {
    console.error('加载配置失败:', error)
    
    // 检查是否是网络错误
    if (error.code === 'NETWORK_ERROR' || error.message?.includes('Network Error')) {
      ElMessage.error('网络连接失败，请检查后端服务是否启动')
    } else if (error.response?.status === 404) {
      ElMessage.error('API接口不存在，请检查后端配置')
    } else {
      ElMessage.error(`加载配置失败: ${error.message || error}`)
    }
  } finally {
    configLoading.value = false
  }
}

// 加载统计数据
const loadStatistics = async () => {
  if (!filterForm.start_date || !filterForm.end_date) {
    ElMessage.warning('请选择时间范围')
    return
  }
  
  if (filterForm.tenant_ids.length === 0) {
    ElMessage.warning('请至少选择一个租户')
    return
  }
  
  if (!filterForm.task_type) {
    ElMessage.warning('请选择任务类型')
    return
  }
  
  loading.value = true
  
  try {
    // 并行加载统计数据和汇总数据
    const [statisticsResponse, summaryResponse] = await Promise.all([
      getStatisticsData(filterForm),
      getStatisticsSummary(filterForm)
    ])
    
    if (statisticsResponse.success) {
      statisticsData.value = statisticsResponse.data
      cacheTime.value = statisticsResponse.cache_time
      fromCache.value = statisticsResponse.from_cache || false
      
      // 保存调试信息
      debugInfo.value = statisticsResponse._debug || []
      
      // 输出调试信息到控制台
      if (statisticsResponse._debug) {
        console.log('📊 统计数据查询调试信息:', statisticsResponse._debug)
      }
    }
    
    if (summaryResponse.success) {
      summaryData.value = summaryResponse.data
      
      // 输出调试信息到控制台
      if (summaryResponse._debug) {
        console.log('📈 汇总数据查询调试信息:', summaryResponse._debug)
      }
    }
    
    // 确保数据都加载完成后再渲染图表
    if (statisticsResponse.success && summaryResponse.success) {
      await nextTick()
      renderCharts()
    }
    
  } catch (error) {
    console.error('加载统计数据失败:', error)
    ElMessage.error('加载统计数据失败')
  } finally {
    loading.value = false
  }
}

// 重置筛选条件
const resetFilter = () => {
  initDefaultDateRange()
  
  // 默认选择Anker租户和AmazonListingJob任务类型
  const defaultTenant = tenants.value.find(t => t.id === 'Anker')
  const defaultTaskType = 'AmazonListingJob'
  
  filterForm.tenant_ids = defaultTenant ? [defaultTenant.id] : []
  filterForm.task_type = taskTypes.value.includes(defaultTaskType) ? defaultTaskType : ''
}

// 刷新数据
const refreshData = async () => {
  refreshing.value = true
  fromCache.value = false
  
  try {
    // 强制刷新数据（不使用缓存）
    const timestamp = Date.now()
    const refreshParams = {
      ...filterForm,
      _refresh: timestamp // 添加时间戳参数强制绕过缓存
    }
    
    const [statisticsResponse, summaryResponse] = await Promise.all([
      getStatisticsData(refreshParams),
      getStatisticsSummary(refreshParams)
    ])
    
    if (statisticsResponse.success) {
      statisticsData.value = statisticsResponse.data
      cacheTime.value = statisticsResponse.cache_time
      fromCache.value = statisticsResponse.from_cache || false
      
      // 保存调试信息
      debugInfo.value = statisticsResponse._debug || []
      
      // 输出调试信息到控制台
      if (statisticsResponse._debug) {
        console.log('🔄 刷新统计数据查询调试信息:', statisticsResponse._debug)
      }
    }
    
    if (summaryResponse.success) {
      summaryData.value = summaryResponse.data
      
      // 输出调试信息到控制台
      if (summaryResponse._debug) {
        console.log('🔄 刷新汇总数据查询调试信息:', summaryResponse._debug)
      }
    }
    
    // 确保数据都加载完成后再渲染图表
    if (statisticsResponse.success && summaryResponse.success) {
      await nextTick()
      renderCharts()
    }
    
    ElMessage.success('数据刷新成功')
    
  } catch (error) {
    console.error('刷新数据失败:', error)
    ElMessage.error('刷新数据失败')
  } finally {
    refreshing.value = false
  }
}

// 计算成功率
const calculateSuccessRate = (data) => {
  if (data.total_count === 0) return 0
  return Math.round((data.succeed_count / data.total_count) * 100)
}

// 计算百分比
const calculatePercentage = (count, total) => {
  if (total === 0) return 0
  return Math.round((count / total) * 100)
}

// 获取标签类型
const getTagType = (count) => {
  if (count === 0) return 'success'
  if (count <= 5) return 'warning'
  return 'danger'
}

// 查看详情
const viewDetails = (type, date, count) => {
  currentDetailType.value = type
  currentDetailDate.value = date
  currentDetailCount.value = count
  detailsDialogVisible.value = true
}

// 分页处理
const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
}

const handleCurrentChange = (val) => {
  currentPage.value = val
}

// 渲染图表
const renderCharts = () => {
  console.log('🎨 开始渲染图表:', { 
    statisticsData: !!statisticsData.value, 
    summaryData: !!summaryData.value,
    pieChartRef: !!pieChart.value,
    trendChartRef: !!trendChart.value
  })
  
  if (!statisticsData.value) {
    console.warn('统计数据不存在，跳过图表渲染')
    return
  }
  
  // 销毁现有图表
  Object.values(charts).forEach(chart => {
    if (chart && chart.dispose) {
      chart.dispose()
    }
  })
  
  // 重置图表对象
  charts.trend = null
  charts.pie = null
  
  // 渲染综合趋势图
  if (trendChart.value) {
    console.log('📈 渲染趋势图')
    charts.trend = renderTrendChart(trendChart.value, statisticsData.value, filterForm.task_type)
  } else {
    console.warn('趋势图容器不存在')
  }
  
  // 渲染饼图
  if (pieChart.value && summaryData.value) {
    console.log('🥧 渲染饼图')
    charts.pie = renderPieChart(pieChart.value, summaryData.value)
  } else {
    console.warn('饼图渲染条件不满足:', { 
      pieChartRef: !!pieChart.value, 
      summaryData: !!summaryData.value 
    })
  }
  
  console.log('✅ 图表渲染完成')
}

// 渲染综合趋势图
const renderTrendChart = (container, data, taskType) => {
  if (!container || !data) return null
  
  const chart = echarts.init(container)
  
  // 获取所有日期并排序
  const allDates = new Set()
  Object.values(data).forEach(typeData => {
    typeData.forEach(item => allDates.add(item.date))
  })
  const dates = Array.from(allDates).sort()
  
  // 创建数据系列
  const series = [
    {
      name: '失败数量',
      type: 'line',
      data: dates.map(date => {
        const item = data.failed_count.find(d => d.date === date)
        return item ? Number(item.count) : 0
      }),
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: {
        width: 3,
        color: '#ff4d4f'
      },
      itemStyle: {
        color: '#ff4d4f'
      },
      areaStyle: {
        opacity: 0.1,
        color: '#ff4d4f'
      }
    },
    {
      name: '超时数量',
      type: 'line',
      data: dates.map(date => {
        const item = data.timeout_count.find(d => d.date === date)
        return item ? Number(item.count) : 0
      }),
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: {
        width: 3,
        color: '#fa8c16'
      },
      itemStyle: {
        color: '#fa8c16'
      },
      areaStyle: {
        opacity: 0.1,
        color: '#fa8c16'
      }
    },
    {
      name: '延期完成',
      type: 'line',
      data: dates.map(date => {
        const item = data.timeout_but_succeed.find(d => d.date === date)
        return item ? Number(item.count) : 0
      }),
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: {
        width: 3,
        color: '#faad14'
      },
      itemStyle: {
        color: '#faad14'
      },
      areaStyle: {
        opacity: 0.1,
        color: '#faad14'
      }
    },
    {
      name: '按时完成',
      type: 'line',
      data: dates.map(date => {
        const item = data.succeed_not_timeout.find(d => d.date === date)
        return item ? Number(item.count) : 0
      }),
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: {
        width: 3,
        color: '#52c41a'
      },
      itemStyle: {
        color: '#52c41a'
      },
      areaStyle: {
        opacity: 0.1,
        color: '#52c41a'
      }
    },
    {
      name: '超时未完成',
      type: 'line',
      data: dates.map(date => {
        const item = data.timeout_not_succeed.find(d => d.date === date)
        return item ? Number(item.count) : 0
      }),
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: {
        width: 3,
        color: '#f5222d'
      },
      itemStyle: {
        color: '#f5222d'
      },
      areaStyle: {
        opacity: 0.1,
        color: '#f5222d'
      }
    },
    {
      name: '已完成',
      type: 'line',
      data: dates.map(date => {
        const item = data.succeed_count.find(d => d.date === date)
        return item ? Number(item.count) : 0
      }),
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: {
        width: 3,
        color: '#13c2c2'
      },
      itemStyle: {
        color: '#13c2c2'
      },
      areaStyle: {
        opacity: 0.1,
        color: '#13c2c2'
      }
    },
    {
      name: '总数量',
      type: 'line',
      data: dates.map(date => {
        const item = data.total_count.find(d => d.date === date)
        return item ? Number(item.count) : 0
      }),
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: {
        width: 3,
        color: '#1890ff'
      },
      itemStyle: {
        color: '#1890ff'
      },
      areaStyle: {
        opacity: 0.1,
        color: '#1890ff'
      }
    }
  ]
  
  const option = {
    title: {
      text: `${taskType || 'AmazonListingJob'} 任务趋势分析`,
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 'bold'
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        label: {
          backgroundColor: '#6a7985'
        }
      },
      formatter: function(params) {
        let result = `<div style="font-weight: bold; margin-bottom: 5px;">${params[0].axisValue}</div>`
        params.forEach(param => {
          const color = param.color
          result += `<div style="margin: 2px 0;">
            <span style="display: inline-block; width: 10px; height: 10px; background-color: ${color}; border-radius: 50%; margin-right: 5px;"></span>
            ${param.seriesName}: <span style="font-weight: bold;">${param.value}</span>
          </div>`
        })
        return result
      }
    },
    legend: {
      top: 40,
      data: ['失败数量', '超时数量', '延期完成', '按时完成', '超时未完成', '已完成', '总数量'],
      textStyle: {
        fontSize: 12
      },
      itemGap: 15,
      orient: 'horizontal'
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '8%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: {
        rotate: 45,
        fontSize: 11
      },
      axisLine: {
        lineStyle: {
          color: '#e4e7ed'
        }
      }
    },
    yAxis: {
      type: 'value',
      name: '数量',
      nameTextStyle: {
        fontSize: 12,
        color: '#606266'
      },
      axisLabel: {
        fontSize: 11
      },
      axisLine: {
        lineStyle: {
          color: '#e4e7ed'
        }
      },
      splitLine: {
        lineStyle: {
          color: '#f5f7fa',
          type: 'dashed'
        }
      }
    },
    series: series,
    dataZoom: [
      {
        type: 'slider',
        start: 0,
        end: 100,
        height: 20,
        bottom: 10
      }
    ]
  }
  
  chart.setOption(option)
  
  // 响应式调整
  window.addEventListener('resize', () => {
    chart.resize()
  })
  
  return chart
}

// 渲染饼图
const renderPieChart = (container, data) => {
  console.log('🥧 开始渲染饼图:', { container: !!container, data })
  
  if (!container) {
    console.warn('饼图容器不存在')
    return null
  }
  
  if (!data || Object.keys(data).length === 0) {
    console.warn('饼图数据为空')
    return null
  }
  
  const chart = echarts.init(container)
  
  // 获取第一个任务类型的数据（通常是AmazonListingJob）
  const taskType = Object.keys(data)[0]
  const taskData = data[taskType]
  
  console.log('📊 饼图任务数据:', { taskType, taskData })
  
  if (!taskData) {
    console.warn('任务数据不存在')
    return null
  }
  
  // 计算各种状态的数量
  const totalCount = taskData.total_count || 0
  const succeedCount = taskData.succeed_count || 0
  const failedCount = taskData.failed_count || 0
  const timeoutButSucceed = taskData.timeout_but_succeed || 0
  const succeedNotTimeout = taskData.succeed_not_timeout || 0
  const timeoutNotSucceed = taskData.timeout_not_succeed || 0
  
  // 计算未完成数量
  const incompleteCount = totalCount - succeedCount
  
  // 计算正常进行中的数量（未完成 - 失败 - 超时未完成）
  const processingCount = Math.max(0, incompleteCount - failedCount - timeoutNotSucceed)
  
  console.log('📈 饼图计算数据:', {
    totalCount,
    succeedCount,
    incompleteCount,
    succeedNotTimeout,
    timeoutButSucceed,
    failedCount,
    timeoutNotSucceed,
    processingCount
  })
  
  const option = {
    title: {
      text: `${taskType} 状态分布`,
      left: 'center',
      top: 20,
      textStyle: {
        fontSize: 16,
        fontWeight: 'bold'
      }
    },
    tooltip: {
      trigger: 'item',
      formatter: function(params) {
        return `${params.seriesName}<br/>${params.name}: ${params.value} (${params.percent}%)`
      }
    },
    legend: {
      orient: 'vertical',
      left: 'left',
      top: 'middle',
      textStyle: {
        fontSize: 12
      }
    },
    series: [
      // 外层饼图：已完成 vs 未完成
      {
        name: '总体状态',
        type: 'pie',
        radius: ['20%', '40%'],
        center: ['60%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 8,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: true,
          position: 'inside',
          formatter: '{b}\n{d}%',
          textStyle: {
            fontSize: 11,
            fontWeight: 'bold'
          }
        },
        labelLine: {
          show: false
        },
        data: [
          { 
            value: succeedCount, 
            name: '已完成',
            itemStyle: { color: '#52c41a' }
          },
          { 
            value: incompleteCount, 
            name: '未完成',
            itemStyle: { color: '#fa8c16' }
          }
        ].filter(item => item.value > 0) // 只显示有数据的项
      },
      // 内层饼图：详细状态分布
      {
        name: '详细状态',
        type: 'pie',
        radius: ['45%', '70%'],
        center: ['60%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 6,
          borderColor: '#fff',
          borderWidth: 1
        },
        label: {
          show: true,
          position: 'outside',
          formatter: '{b}: {c}\n({d}%)',
          textStyle: {
            fontSize: 10
          }
        },
        labelLine: {
          show: true,
          length: 15,
          length2: 10
        },
        data: [
          { 
            value: succeedNotTimeout, 
            name: '按时完成',
            itemStyle: { color: '#52c41a' }
          },
          { 
            value: timeoutButSucceed, 
            name: '延期完成',
            itemStyle: { color: '#faad14' }
          },
          { 
            value: failedCount, 
            name: '失败',
            itemStyle: { color: '#ff4d4f' }
          },
          { 
            value: timeoutNotSucceed, 
            name: '超时未完成',
            itemStyle: { color: '#f5222d' }
          },
          { 
            value: processingCount, 
            name: '正常进行中',
            itemStyle: { color: '#1890ff' }
          }
        ].filter(item => item.value > 0) // 只显示有数据的项
      }
    ]
  }
  
  console.log('🎨 饼图配置:', option)
  
  chart.setOption(option)
  
  // 响应式调整
  const resizeHandler = () => {
    chart.resize()
  }
  window.addEventListener('resize', resizeHandler)
  
  // 保存清理函数
  chart._cleanup = () => {
    window.removeEventListener('resize', resizeHandler)
  }
  
  // 重写dispose方法以包含清理
  const originalDispose = chart.dispose.bind(chart)
  chart.dispose = () => {
    if (chart._cleanup) {
      chart._cleanup()
    }
    originalDispose()
  }
  
  console.log('✅ 饼图渲染完成')
  return chart
}

// 计算处理中的任务数量
const calculateProcessingCount = (data) => {
  // 正常进行中 = 总数 - 已完成 - 失败 - 超时未完成
  const totalCount = data.total_count || 0
  const succeedCount = data.succeed_count || 0
  const failedCount = data.failed_count || 0
  const timeoutNotSucceed = data.timeout_not_succeed || 0
  
  const incompleteCount = totalCount - succeedCount
  const processingCount = Math.max(0, incompleteCount - failedCount - timeoutNotSucceed)
  
  return processingCount
}

// 组件挂载
onMounted(async () => {
  initDefaultDateRange()
  await loadConfig()
  await loadStatistics()
})
</script>

<style scoped>
.statistics-container {
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0 0 10px 0;
  color: #303133;
}

.page-header p {
  margin: 0;
  color: #909399;
}

.filter-card {
  margin-bottom: 20px;
}

.summary-card {
  margin-bottom: 20px;
}

.summary-item {
  text-align: center;
  padding: 20px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background: #fafafa;
}

.summary-item h4 {
  margin: 0 0 15px 0;
  color: #303133;
  font-size: 16px;
}

.summary-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 15px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px;
  border-radius: 6px;
}

.stat-item.total {
  background: #e6f7ff;
  color: #1890ff;
}

.stat-item.success {
  background: #f6ffed;
  color: #52c41a;
}

.stat-item.failed {
  background: #fff2f0;
  color: #ff4d4f;
}

.stat-item.timeout {
  background: #fff7e6;
  color: #fa8c16;
}

.stat-item.warning {
  background: #fffbe6;
  color: #faad14;
}

.stat-item.danger {
  background: #fff1f0;
  color: #f5222d;
}

.stat-item .label {
  font-size: 12px;
  margin-bottom: 5px;
}

.stat-item .value {
  font-size: 18px;
  font-weight: bold;
}

.success-rate {
  font-size: 14px;
  color: #52c41a;
  font-weight: bold;
}

.config-loading {
  text-align: center;
  padding: 20px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background: #fafafa;
}

.empty-hint {
  font-size: 12px;
  color: #909399;
  margin-left: 10px;
}

.loading-hint {
  font-size: 12px;
  color: #909399;
  margin-left: 10px;
}

.data-status {
  margin-bottom: 20px;
}

.cache-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 15px 20px;
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 8px;
}

.cache-time {
  display: flex;
  align-items: center;
}

.cache-time .el-icon {
  margin-right: 8px;
  color: #409eff;
}

.cache-time span {
  font-size: 14px;
  color: #303133;
  font-weight: 500;
  margin-right: 10px;
}

.cache-time .el-tag {
  margin-left: 10px;
}

.debug-content {
  padding: 10px 0;
}

.debug-content h4 {
  margin: 15px 0 10px 0;
  color: #303133;
  font-size: 14px;
}

.sql-code, .params-code {
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  padding: 12px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 12px;
  line-height: 1.5;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.sql-code {
  color: #2c3e50;
}

.params-code {
  color: #7f8c8d;
}

.data-section {
  margin-bottom: 40px;
}

.data-section:last-child {
  margin-bottom: 0;
}

.section-title {
  margin: 0 0 20px 0;
  padding: 10px 0;
  color: #303133;
  font-size: 16px;
  font-weight: 600;
  border-bottom: 2px solid #e4e7ed;
}

.stat-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.percentage {
  font-size: 12px;
  color: #909399;
  min-width: 35px;
}

.pagination-container {
  margin-top: 20px;
  text-align: right;
}

.chart-container {
  padding: 20px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background: #fff;
  height: 100%;
}

.chart-title {
  margin: 0 0 20px 0;
  color: #303133;
  font-size: 16px;
  font-weight: 600;
  text-align: center;
}

.summary-cards-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: 100%;
}

.summary-card-item {
  flex: 1;
  padding: 20px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  transition: box-shadow 0.3s ease;
}

.summary-card-item:hover {
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid #f0f0f0;
}

.card-header h4 {
  margin: 0;
  color: #303133;
  font-size: 18px;
  font-weight: 600;
}

.success-rate {
  font-size: 14px;
  color: #52c41a;
  font-weight: bold;
  background: #f6ffed;
  padding: 4px 8px;
  border-radius: 4px;
  border: 1px solid #b7eb8f;
}

.summary-stats-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stat-row {
  display: flex;
  gap: 12px;
}

.stat-row.sub-stats {
  margin-left: 20px;
  opacity: 0.9;
}

.stat-row.sub-stats .stat-item {
  border-left: 3px solid #e4e7ed;
  padding-left: 12px;
}

.stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px;
  border-radius: 6px;
  transition: all 0.3s ease;
  min-height: 70px;
  justify-content: center;
}

.stat-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.stat-item.total {
  background: linear-gradient(135deg, #e6f7ff 0%, #bae7ff 100%);
  color: #1890ff;
  border: 1px solid #91d5ff;
}

.stat-item.success {
  background: linear-gradient(135deg, #f6ffed 0%, #d9f7be 100%);
  color: #52c41a;
  border: 1px solid #b7eb8f;
}

.stat-item.success-detail {
  background: linear-gradient(135deg, #f6ffed 0%, #d9f7be 100%);
  color: #389e0d;
  border: 1px solid #95de64;
}

.stat-item.failed {
  background: linear-gradient(135deg, #fff2f0 0%, #ffccc7 100%);
  color: #ff4d4f;
  border: 1px solid #ffa39e;
}

.stat-item.timeout {
  background: linear-gradient(135deg, #fff7e6 0%, #ffd591 100%);
  color: #fa8c16;
  border: 1px solid #ffb366;
}

.stat-item.warning {
  background: linear-gradient(135deg, #fffbe6 0%, #fff566 100%);
  color: #faad14;
  border: 1px solid #ffd666;
}

.stat-item.danger {
  background: linear-gradient(135deg, #fff1f0 0%, #ffa39e 100%);
  color: #f5222d;
  border: 1px solid #ff7875;
}

.stat-item.incomplete {
  background: linear-gradient(135deg, #fff7e6 0%, #ffd591 100%);
  color: #fa8c16;
  border: 1px solid #ffb366;
}

.stat-item.processing {
  background: linear-gradient(135deg, #f0f9ff 0%, #bfdbfe 100%);
  color: #1890ff;
  border: 1px solid #93c5fd;
}

.stat-item .label {
  font-size: 12px;
  margin-bottom: 6px;
  font-weight: 500;
  text-align: center;
  opacity: 0.8;
}

.stat-item .value {
  font-size: 20px;
  font-weight: bold;
  margin-bottom: 2px;
}

.stat-item .sub-label {
  font-size: 11px;
  color: #909399;
  font-weight: normal;
  opacity: 0.7;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .summary-cards-container {
    gap: 15px;
  }
  
  .summary-card-item {
    padding: 15px;
  }
  
  .stat-item {
    padding: 10px;
    min-height: 60px;
  }
  
  .stat-item .value {
    font-size: 18px;
  }
}

@media (max-width: 768px) {
  .summary-card .el-row {
    flex-direction: column;
  }
  
  .summary-card .el-col {
    width: 100% !important;
    margin-bottom: 20px;
  }
  
  .stat-row {
    flex-direction: column;
    gap: 8px;
  }
  
  .stat-row.sub-stats {
    margin-left: 10px;
  }
}
</style> 