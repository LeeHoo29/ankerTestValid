# 数据库迁移说明

## 概述

本系统已完全迁移到MySQL数据库存储，`task_mapping.json` 文件将不再使用。

## 主要变更

### 🗃️ 数据存储变更
- **旧方式**: JSON文件存储 (`data/output/task_mapping.json`)
- **新方式**: MySQL数据库存储 (`local_anker_valid` 数据库)

### 📊 数据库表结构
- `task_mapping`: 主要任务映射表
- `task_file_details`: 文件详情表

### 🔧 API变更
所有API端点现在仅使用数据库：
- `/api/completed_tasks` - 获取已完成任务
- `/api/delete_task/<job_id>` - 删除任务
- `/api/task_detail/<job_id>` - 获取任务详情
- `/api/check_task_exists` - 检查任务是否存在

## 迁移步骤

### 1. 数据库初始化
```bash
python scripts/init_local_database.py
```

### 2. 从JSON文件迁移数据（可选）
如果您有现有的 `task_mapping.json` 文件，初始化脚本会自动迁移数据。

### 3. 验证迁移
访问数据库管理页面: http://localhost:3001/database

## 兼容性说明

### ✅ 继续支持
- 所有现有API接口
- 前端界面功能
- 任务执行流程

### ❌ 不再支持
- JSON文件回退机制
- 手动编辑 `task_mapping.json`
- 基于文件的数据操作

## 数据库配置

配置文件: `config/local_db_config.py`

```python
DATABASE_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '123456',
    'database': 'local_anker_valid'
}
```

## 故障排除

### 数据库连接失败
1. 确认MySQL服务已启动
2. 验证数据库配置
3. 检查用户权限

### 数据迁移问题
1. 备份原始JSON文件
2. 重新运行初始化脚本
3. 检查日志输出

## 注意事项

⚠️ **重要提醒**:
- `task_mapping.json` 文件将不再更新
- 新任务数据仅存储在数据库中
- 删除操作不可逆，请谨慎操作

## 联系支持

如遇问题，请检查日志文件或联系技术支持团队。 