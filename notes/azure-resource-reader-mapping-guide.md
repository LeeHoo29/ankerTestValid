# Azure 资源读取器 - 任务映射功能指南

## 📋 功能概述

Azure 资源读取器的任务映射功能会自动记录每次下载操作的映射关系，帮助您快速定位已下载的文件。

## 🗂️ 映射文件结构

### 文件位置
```
data/output/task_mapping.json
```

### 文件格式
```json
{
  "输入参数": {
    "relative_path": "./任务类型/实际任务ID/",
    "task_type": "任务类型",
    "actual_task_id": "实际任务ID",
    "last_updated": "最后更新时间",
    "full_path": "完整文件路径"
  }
}
```

### 示例映射
```json
{
  "2796867471": {
    "relative_path": "./AmazonReviewStarJob/1910599147004108800/",
    "task_type": "AmazonReviewStarJob",
    "actual_task_id": "1910599147004108800",
    "last_updated": "2025-05-24T19:40:30.107820",
    "full_path": "data/output/AmazonReviewStarJob/1910599147004108800/"
  },
  "1925464883027513344": {
    "relative_path": "./AmazonListingJob/1925464883027513344/",
    "task_type": "AmazonListingJob",
    "actual_task_id": "1925464883027513344",
    "last_updated": "2025-05-24T19:41:31.758356",
    "full_path": "data/output/AmazonListingJob/1925464883027513344/"
  }
}
```

## 🚀 使用方法

### 1. 基本下载（自动生成映射）
```bash
# 下载文件并自动更新映射
python3 src/azure_resource_reader.py AmazonReviewStarJob 2796867471 html
```

### 2. 🆕 同时获取原始数据和解析数据（推荐）
```bash
# 同时下载原始文件和解析文件
python3 src/azure_resource_reader.py AmazonReviewStarJob 2796867471 html --with-parse
python3 src/azure_resource_reader.py AmazonListingJob 1925464883027513344 json --with-parse

# 指定特定原始文件的同时获取解析数据
python3 src/azure_resource_reader.py AmazonReviewStarJob 2796867471 html --with-parse --files page_1.gz

# 仅查看信息（不下载）
python3 src/azure_resource_reader.py AmazonReviewStarJob 2796867471 html --with-parse --info-only
```

### 3. 查看当前映射
```bash
# 显示所有映射关系
python3 src/azure_resource_reader.py --show-mapping
```

输出示例：
```
🔍 Azure Storage 任务映射查看器
================================================================================
📄 映射文件路径: data/output/task_mapping.json
📊 总计映射数量: 2

📋 任务映射列表:
--------------------------------------------------------------------------------

🔍 输入参数: 2796867471
  📂 任务类型: AmazonReviewStarJob
  📋 实际任务ID: 1910599147004108800
  📁 相对路径: ./AmazonReviewStarJob/1910599147004108800/
  📅 最后更新: 2025-05-24T19:40:30.107820
  📄 文件数量: 5
```

### 4. 禁用映射功能
```bash
# 下载文件但不更新映射
python3 src/azure_resource_reader.py AmazonListingJob 2796867471 html --no-mapping
```

### 5. 🆕 解析文件模式（collector0109）
解析文件模式专门用于读取Azure Storage collector0109账户中的JSON解析结果。

**⚠️ 重要更新**: 解析文件路径结构已更正为：`parse/parse/{任务类型}/{task_id}/*`

```bash
# 自动查找JSON解析文件
python3 src/azure_resource_reader.py --account collector0109 --parse-mode AmazonReviewStarJob 1910599147004108800 json

# 指定解析文件名
python3 src/azure_resource_reader.py --account collector0109 --parse-mode AmazonReviewStarJob 1910599147004108800 json --files result.json

# 查看解析文件信息
python3 src/azure_resource_reader.py --account collector0109 --parse-mode AmazonReviewStarJob 1910599147004108800 json --info-only

# 列出解析目录中的所有文件
python3 src/azure_resource_reader.py --account collector0109 --parse-mode AmazonReviewStarJob 1910599147004108800 json --list-jobs
```

**解析模式特点**:
- **路径结构**: `parse/parse/{任务类型}/{task_id}/*` （已修正）
- 自动优先查找 `.json` > `.json.gz` > 其他文件
- 支持JSON格式验证和预览
- 独立的映射记录格式

## 📁 目录结构映射

### 🆕 --with-parse模式的文件结构
当使用`--with-parse`模式时，原始文件和解析文件会保存在同一个目录下：

```
data/output/AmazonReviewStarJob/1910599147004108800/
├── page_1.html           # 原始文件（解压缩后）
├── page_2.html           # 原始文件（解压缩后）
├── parse_result.json     # 解析文件（如果存在）
└── ...
```

### 输入参数类型

#### 1. 完整任务ID（18-20位数字）
- **输入**: `1925464883027513344`
- **识别**: 自动识别为有效任务ID
- **映射**: `1925464883027513344` → `./AmazonListingJob/1925464883027513344/`

#### 2. 短job_id（数字）
- **输入**: `2796867471`
- **处理**: 自动添加`SL`前缀 → `SL2796867471`
- **查询**: 数据库查询转换为实际任务ID
- **映射**: `2796867471` → `./AmazonReviewStarJob/1910599147004108800/`

#### 3. 带前缀的job_id
- **输入**: `SL2796867471`
- **处理**: 直接查询数据库
- **映射**: `SL2796867471` → `./AmazonReviewStarJob/1910599147004108800/`

## 🎯 映射功能优势

### 1. 快速定位
根据输入参数快速找到对应的下载文件夹，无需记忆复杂的任务ID。

### 2. 历史记录
保留所有下载历史，支持回溯查找。

### 3. 🆕 一站式下载
使用`--with-parse`模式，一个命令即可获取原始数据和解析数据。

### 4. 文件统计
自动统计每个任务目录下的文件数量。

### 5. 灵活控制
支持禁用映射功能，满足不同使用场景。

## 🔧 高级用法

### 1. 批量查看映射
```bash
# 查看映射文件内容
cat data/output/task_mapping.json | jq '.'
```

### 2. 根据映射快速访问文件
```bash
# 根据输入参数查找对应目录
input_param="2796867471"
relative_path=$(jq -r ".[\"$input_param\"].relative_path" data/output/task_mapping.json)
echo "文件路径: $relative_path"

# 列出该目录下的所有文件
ls -la "data/output/${relative_path#./}"
```

### 3. 映射文件维护
```bash
# 备份映射文件
cp data/output/task_mapping.json data/output/task_mapping_backup.json

# 清空映射文件（重新开始记录）
echo '{}' > data/output/task_mapping.json
```

## 📊 支持的任务类型

### AmazonListingJob
- **默认文件**: `login.gz`, `normal.gz`
- **路径结构**: `./AmazonListingJob/{task_id}/`

### AmazonReviewStarJob
- **默认文件**: `page_1.gz`, `page_2.gz`, `page_3.gz`, `page_4.gz`, `page_5.gz`
- **路径结构**: `./AmazonReviewStarJob/{task_id}/`

## ⚠️ 注意事项

1. **映射文件位置**: 确保`data/output`目录存在且可写
2. **JSON格式**: 映射文件使用JSON格式，避免手动编辑破坏格式
3. **权限问题**: 确保对映射文件有读写权限
4. **备份建议**: 定期备份映射文件，避免意外丢失
5. **🆕 解析文件路径**: 解析文件路径结构为 `parse/parse/{任务类型}/{task_id}/*`

## 🐛 故障排除

### 映射文件损坏
```bash
# 检查JSON格式
cat data/output/task_mapping.json | jq '.'

# 如果格式错误，重新创建
echo '{}' > data/output/task_mapping.json
```

### 权限问题
```bash
# 检查权限
ls -la data/output/task_mapping.json

# 修复权限
chmod 644 data/output/task_mapping.json
```

### 目录不存在
```bash
# 创建必要目录
mkdir -p data/output
```

## 💡 最佳实践

1. **🆕 优先使用--with-parse**: 对于需要同时获取原始数据和解析数据的场景
2. **定期查看映射**: 使用`--show-mapping`查看当前映射状态
3. **有选择性禁用**: 对于测试操作使用`--no-mapping`
4. **备份重要映射**: 定期备份映射文件
5. **清理无效映射**: 删除对应目录不存在的映射条目

## 📊 存储账户对比

| 账户 | 用途 | 容器 | 路径结构 | 文件类型 |
|------|------|------|----------|----------|
| **yiya0110** | 原始任务数据 | download | compress/{task_type}/{task_id}/ | login.gz, normal.gz, page_*.gz |
| **collector0109** | 解析结果数据 | parse | parse/parse/{task_type}/{task_id}/ | *.json, *.json.gz |

## 🆕 功能亮点

### --with-parse 模式优势
1. **一站式下载**: 一个命令获取所有相关数据
2. **自动路径管理**: 自动处理两个存储账户的路径结构
3. **统一保存**: 原始文件和解析文件保存在同一目录
4. **智能映射**: 自动记录两种数据的映射关系
5. **错误容忍**: 即使解析文件不存在，原始文件仍可正常下载

---

> 📝 **提示**: 映射功能大大简化了文件管理流程，特别适合需要频繁访问下载文件的场景。新的`--with-parse`模式为数据获取提供了更便捷的解决方案。