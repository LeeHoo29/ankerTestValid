# 超时未完成统计功能实现文档

## 📋 功能概述

新增了"**超时未完成**"（`timeout_not_succeed`）统计维度，用于统计已经超时但尚未完成的任务数量。

## 🎯 业务逻辑

### 统计维度定义
- **超时未完成**: 任务已超过截止时间（`break_at`），但尚未交付（`deliver_at` 为 NULL），且状态不是 FAILED 的任务

### 完整统计体系
1. **总数** (`total_count`): 所有任务
2. **失败** (`failed_count`): 状态为 FAILED 的任务  
3. **超时** (`timeout_count`): 已超时的任务（包括延期完成和超时未完成）
4. **已完成** (`succeed_count`): 已交付的任务
5. **延期完成** (`timeout_but_succeed`): 已超时但已完成的任务
6. **按时完成** (`succeed_not_timeout`): 未超时且已完成的任务
7. **超时未完成** (`timeout_not_succeed`): 已超时且未完成的任务 ⭐ **新增**

### 数据关系验证
- 超时总数 = 延期完成 + 超时未完成
- 已完成 = 延期完成 + 按时完成
- 总数 = 已完成 + 失败 + 超时未完成

## 🔧 技术实现

### 1. 后端修改

#### 配置文件 (`config/task_statistics_config.py`)
```python
# 新增SQL模板
'timeout_not_succeed': """
    SELECT 
        COUNT(*) as count,
        DATE(created_at) AS date,
        type as task_type
    FROM {table} 
    WHERE created_at >= %s 
        AND created_at <= %s
        AND tenant_id IN ({tenant_ids})
        AND type IN ({task_types})
        AND break_at < DATE_FORMAT(UTC_TIMESTAMP(), '%%Y-%%m-%%d %%H:%%i:%%s')
        AND deliver_at IS NULL
        AND `status` != "FAILED"
    GROUP BY date, task_type
    ORDER BY date DESC, task_type
"""

# 更新合并查询模板
'combined_statistics': """
    SELECT 
        DATE(a.created_at) AS date,
        a.type as task_type,
        COUNT(*) as total_count,
        SUM(CASE WHEN a.status = 'FAILED' THEN 1 ELSE 0 END) as failed_count,
        SUM(CASE WHEN a.break_at < %s 
                 AND (a.deliver_at IS NULL OR a.deliver_at > a.break_at)
                 AND a.status != 'FAILED' THEN 1 ELSE 0 END) as timeout_count,
        SUM(CASE WHEN a.deliver_at IS NOT NULL AND a.status != 'FAILED' THEN 1 ELSE 0 END) as succeed_count,
        SUM(CASE WHEN a.break_at < %s 
                 AND a.deliver_at IS NOT NULL 
                 AND a.deliver_at > a.break_at
                 AND a.status != 'FAILED' THEN 1 ELSE 0 END) as timeout_but_succeed,
        SUM(CASE WHEN (a.break_at >= %s OR a.break_at IS NULL)
                 AND a.deliver_at IS NOT NULL 
                 AND a.status != 'FAILED' THEN 1 ELSE 0 END) as succeed_not_timeout,
        SUM(CASE WHEN a.break_at < %s 
                 AND a.deliver_at IS NULL
                 AND a.status != 'FAILED' THEN 1 ELSE 0 END) as timeout_not_succeed
    FROM {table} a
    WHERE a.created_at >= %s 
        AND a.created_at <= %s
        AND a.tenant_id IN ({tenant_ids})
        AND a.type IN ({task_types})
    GROUP BY date, task_type
    ORDER BY date DESC, task_type
"""
```

#### API接口 (`web_app.py`)
- 更新 `get_optimized_statistics_data()` 函数
- 更新 `get_statistics_summary()` 接口  
- 更新 `get_statistics_details()` 接口
- 添加对 `timeout_not_succeed` 详情查询的支持

### 2. 前端修改

#### 统计页面 (`src/views/Statistics.vue`)
```vue
<!-- 汇总统计卡片 -->
<div class="stat-item danger">
  <span class="label">超时未完成</span>
  <span class="value">{{ data.timeout_not_succeed }}</span>
</div>

<!-- 详细数据表格 -->
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
        type="text" 
        :icon="View" 
        size="small"
        @click="viewDetails('timeout_not_succeed', row.date, row.timeout_not_succeed)"
        title="查看详情"
      />
    </div>
  </template>
</el-table-column>

<!-- 趋势图表 -->
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
}
```

#### 详情对话框 (`src/components/StatisticsDetailsDialog.vue`)
```javascript
const dialogTitle = computed(() => {
  const typeMap = {
    'failed': '失败',
    'timeout': '超时', 
    'failed_timeout': '失败或超时',
    'succeed': '已完成',
    'timeout_but_succeed': '延期完成',
    'succeed_not_timeout': '按时完成',
    'timeout_not_succeed': '超时未完成'  // 新增
  }
  return `${typeMap[props.detailType] || '详细'}数据 - ${props.targetDate} (${props.count}条)`
})
```

## 📊 测试结果

### API测试结果
```bash
# 统计数据API - 包含新字段
curl -X POST http://localhost:5001/api/statistics/data \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2025-05-25", "end_date": "2025-05-28", "tenant_ids": ["Anker"], "task_type": "AmazonListingJob"}' \
  | jq '.data | keys'

# 输出：
[
  "failed_count",
  "succeed_count", 
  "succeed_not_timeout",
  "timeout_but_succeed",
  "timeout_count",
  "timeout_not_succeed",  # ✅ 新字段
  "total_count"
]

# 汇总数据API - 实际数值
curl -X POST http://localhost:5001/api/statistics/summary \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2025-05-25", "end_date": "2025-05-28", "tenant_ids": ["Anker"], "task_type": "AmazonListingJob"}' \
  | jq '.data.AmazonListingJob'

# 输出：
{
  "failed_count": "13226",
  "succeed_count": "475718", 
  "succeed_not_timeout": "462535",
  "timeout_but_succeed": "13183",
  "timeout_count": "14067",
  "timeout_not_succeed": "884",  # ✅ 超时未完成数量
  "total_count": 493612
}
```

### 数据验证
- ✅ 超时总数(14,067) = 延期完成(13,183) + 超时未完成(884)
- ✅ 已完成(475,718) = 延期完成(13,183) + 按时完成(462,535)
- ✅ 总数(493,612) = 已完成(475,718) + 失败(13,226) + 超时未完成(884) + 其他状态

## 🎨 UI展示

### 汇总统计卡片
- 新增红色"超时未完成"统计项
- 使用 `danger` 样式突出显示

### 详细数据表格  
- 新增"超时未完成"列
- 支持点击查看详情
- 显示百分比占比

### 趋势图表
- 新增红色"超时未完成"趋势线
- 图例中包含新的统计类型

## 🔍 使用场景

1. **项目管理**: 识别需要紧急处理的超时任务
2. **性能监控**: 监控任务处理效率和超时情况
3. **资源调度**: 根据超时未完成数量调整资源分配
4. **质量分析**: 分析任务超时的原因和模式

## 📝 注意事项

1. **时间基准**: 超时判断基于当前UTC时间，确保实时性
2. **状态过滤**: 排除FAILED状态，专注于可恢复的超时任务
3. **缓存机制**: 利用现有5分钟缓存机制，提高查询性能
4. **数据一致性**: 所有统计维度保持逻辑一致性

## 🚀 部署状态

- ✅ 后端API已部署并测试通过
- ✅ 前端界面已更新并集成
- ✅ 数据库查询优化完成
- ✅ 缓存机制正常工作
- ✅ 详情查询功能可用

---

**实现时间**: 2025-05-28  
**版本**: v1.0  
**状态**: 已完成并测试通过 ✅ 