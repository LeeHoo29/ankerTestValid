<template>
  <div class="statistics-table">
    <el-table 
      :data="tableData" 
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
        prop="task_type" 
        label="任务类型" 
        width="200"
        sortable
      />
      <el-table-column 
        prop="count" 
        label="数量" 
        width="100"
        sortable
        align="right"
      >
        <template #default="{ row }">
          <el-tag 
            :type="getCountTagType(row.count)"
            size="small"
          >
            {{ row.count }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column 
        label="操作" 
        width="120"
      >
        <template #default="{ row }">
          <el-button 
            link 
            size="small"
            @click="viewDetails(row)"
          >
            查看详情
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <!-- 分页 -->
    <div class="pagination-container" v-if="tableData.length > pageSize">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="data.length"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, defineProps, defineEmits } from 'vue'
import { ElMessage } from 'element-plus'

// 定义props
const props = defineProps({
  data: {
    type: Array,
    default: () => []
  },
  title: {
    type: String,
    default: '统计数据'
  }
})

// 定义emits
const emit = defineEmits(['view-details'])

// 分页相关
const currentPage = ref(1)
const pageSize = ref(20)

// 计算表格数据
const tableData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return props.data.slice(start, end)
})

// 获取数量标签类型
const getCountTagType = (count) => {
  if (count === 0) return 'info'
  if (count <= 5) return 'success'
  if (count <= 20) return 'warning'
  return 'danger'
}

// 查看详情
const viewDetails = (row) => {
  emit('view-details', row)
  ElMessage.info(`查看 ${row.date} ${row.task_type} 的详细信息`)
}

// 分页处理
const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
}

const handleCurrentChange = (val) => {
  currentPage.value = val
}
</script>

<style scoped>
.statistics-table {
  width: 100%;
}

.pagination-container {
  margin-top: 20px;
  text-align: right;
}
</style> 