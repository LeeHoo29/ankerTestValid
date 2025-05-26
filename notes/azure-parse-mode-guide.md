# Azure 解析文件读取器指南

## 🎯 功能概述

Azure 解析文件读取器是Azure资源读取器的解析模式扩展，专门用于从 collector0109 存储账户读取JSON解析结果文件。

## 🏗️ 架构设计

### 存储架构
- **存储账户**: collector0109
- **容器**: parse  
- **路径结构**: `parse/parse/{任务类型}/{task_id}/*`（已修正）
- **文件类型**: JSON解析结果文件（.json, .json.gz等）

### 配置信息
```python
COLLECTOR0109_STORAGE_CONFIG = {
    'account_name': 'collector0109',
    'account_url': 'https://collector0109.blob.core.windows.net',
    'container_name': 'parse',
    'blob_base_path': 'parse'  # 解析文件的基础路径：parse/parse/{任务类型}/{task_id}/*
}
```

## 🚀 使用方法

### 🆕 推荐方式：--with-parse模式
对于大多数场景，推荐使用`--with-parse`模式，它可以同时获取原始数据和解析数据：

```bash
# 同时获取原始数据和解析数据（推荐）
python3 src/azure_resource_reader.py AmazonReviewStarJob 1910599147004108800 html --with-parse
python3 src/azure_resource_reader.py AmazonListingJob 1925464883027513344 json --with-parse

# 指定特定原始文件同时获取解析数据
python3 src/azure_resource_reader.py AmazonReviewStarJob 1910599147004108800 html --with-parse --files page_1.gz

# 仅查看信息（不下载）
python3 src/azure_resource_reader.py AmazonReviewStarJob 1910599147004108800 html --with-parse --info-only
```

### 基本语法（纯解析模式）
```bash
python3 src/azure_resource_reader.py --account collector0109 --parse-mode <任务类型> <task_id> <output_type> [选项]
```

### 参数说明
- `--account collector0109`: 指定使用collector0109存储账户
- `--parse-mode`: 启用解析模式
- `<任务类型>`: 任务类型（如: AmazonReviewStarJob, AmazonListingJob）
- `<task_id>`: 任务ID（如: 1910599147004108800）
- `<output_type>`: 输出文件类型（html, txt, json, raw）

### 使用示例

#### 1. 自动查找JSON文件
```bash
python3 src/azure_resource_reader.py --account collector0109 --parse-mode AmazonReviewStarJob 1910599147004108800 json
```

#### 2. 指定具体文件名
```bash
python3 src/azure_resource_reader.py --account collector0109 --parse-mode AmazonReviewStarJob 1910599147004108800 json --files result.json
```

#### 3. 批量下载多个文件
```bash
python3 src/azure_resource_reader.py --account collector0109 --parse-mode AmazonReviewStarJob 1910599147004108800 json --files file1.json file2.json.gz
```

#### 4. 仅查看文件信息
```bash
python3 src/azure_resource_reader.py --account collector0109 --parse-mode AmazonReviewStarJob 1910599147004108800 json --info-only
```

#### 5. 列出目录中的所有文件
```bash
python3 src/azure_resource_reader.py --account collector0109 --parse-mode AmazonReviewStarJob 1910599147004108800 json --list-jobs
```

#### 6. 禁用映射文件生成
```bash
python3 src/azure_resource_reader.py --account collector0109 --parse-mode AmazonReviewStarJob 1910599147004108800 json --no-mapping
```

## 🔍 智能文件发现

解析模式具有智能文件发现功能，当不指定具体文件名时：

### 文件优先级
1. **`.json`** 文件（最高优先级）
2. **`.json.gz`** 文件（中等优先级）  
3. **其他文件** 文件（最低优先级）

### 发现过程
```
1. 扫描指定路径: parse/parse/{任务类型}/{task_id}/
2. 按优先级筛选文件类型
3. 选择第一个匹配的文件
4. 自动解压缩（如果需要）
5. 验证JSON格式（如果是JSON文件）
```

## 📁 文件存储结构

### --with-parse模式的存储结构（推荐）
```
data/output/AmazonReviewStarJob/1910599147004108800/
├── page_1.html           # 原始文件（yiya0110）
├── page_2.html           # 原始文件（yiya0110）
├── parse_result.json     # 解析文件（collector0109）
└── ...
```

### 纯解析模式的存储结构
```
data/output/parse/AmazonReviewStarJob/1910599147004108800/
├── auto_found.json       # 自动发现的文件
├── result.json           # 指定下载的文件
└── ...
```

### 映射文件记录

#### --with-parse模式的映射
```json
{
  "1910599147004108800": {
    "relative_path": "./AmazonReviewStarJob/1910599147004108800/",
    "task_type": "AmazonReviewStarJob",
    "actual_task_id": "1910599147004108800",
    "last_updated": "2025-05-24T20:00:00.000000",
    "full_path": "data/output/AmazonReviewStarJob/1910599147004108800/"
  },
  "1910599147004108800_parse": {
    "relative_path": "./parse/AmazonReviewStarJob/1910599147004108800/",
    "task_type": "parse",
    "job_id": "AmazonReviewStarJob",
    "task_id": "1910599147004108800",
    "last_updated": "2025-05-24T20:00:00.000000",
    "full_path": "data/output/parse/AmazonReviewStarJob/1910599147004108800/"
  }
}
```

#### 纯解析模式的映射
```json
{
  "AmazonReviewStarJob:1910599147004108800": {
    "relative_path": "./parse/AmazonReviewStarJob/1910599147004108800/",
    "task_type": "parse",
    "job_id": "AmazonReviewStarJob",
    "task_id": "1910599147004108800",
    "last_updated": "2025-05-24T20:00:00.000000",
    "full_path": "data/output/parse/AmazonReviewStarJob/1910599147004108800/"
  }
}
```

## 🎨 特色功能

### 1. JSON格式验证
- 自动检测JSON格式
- 显示JSON键或数组长度
- 提供格式验证报告

### 2. 内容预览
- 智能显示前200字符
- JSON结构分析
- 文件大小统计

### 3. 映射管理
- 专用的解析文件映射格式
- 与原始数据映射区分显示
- 支持混合映射查看

### 4. 错误处理
- 网络连接重试
- 文件不存在处理
- 格式验证错误处理

## 📊 --with-parse vs 纯解析模式对比

| 特性 | --with-parse模式 | 纯解析模式 |
|------|------------------|-----------|
| **推荐场景** | 需要原始数据+解析数据 | 仅需解析数据 |
| **命令复杂度** | 简单，一条命令 | 简单，但需分别下载 |
| **文件组织** | 统一目录 | 分离目录 |
| **映射记录** | 双重映射 | 单一映射 |
| **参数格式** | 任务类型 + task_id | 任务类型 + task_id |
| **路径结构** | `{task_type}/{task_id}/` | `parse/{task_type}/{task_id}/` |

## 📊 输出示例

### --with-parse模式示例
```
🔍 Azure Storage 资源读取器 (原始数据 + 解析数据)
📋 任务类型: AmazonReviewStarJob
📋 输入参数: 1910599147004108800
📁 原始数据路径: yiya0110/download/compress/AmazonReviewStarJob/1910599147004108800/
📁 解析数据路径: collector0109/parse/parse/AmazonReviewStarJob/1910599147004108800/
================================================================================

📄 处理原始文件: page_1.gz
------------------------------------------------------------
✅ 原始文件读取成功!
📝 原始文件长度: 466348 字符
💾 原始文件已保存到: data/output/AmazonReviewStarJob/1910599147004108800/page_1.html

✅ 解析文件读取成功!
📝 解析文件长度: 15420 字符
📋 JSON解析成功，类型: <class 'dict'>
🔑 JSON键: ['status', 'data', 'timestamp', 'meta']
💾 解析文件已保存到: data/output/AmazonReviewStarJob/1910599147004108800/parse_result.json
```

### 纯解析模式示例
```
🔍 Azure Storage 资源读取器 (解析模式)
📋 任务类型: AmazonReviewStarJob
📋 Task ID: 1910599147004108800
📁 路径结构: collector0109/parse/parse/AmazonReviewStarJob/1910599147004108800/
================================================================================

📄 自动查找解析文件:
------------------------------------------------------------
找到JSON文件: parse/parse/AmazonReviewStarJob/1910599147004108800/result.json
✅ 读取成功!
💾 文件已保存到: data/output/parse/AmazonReviewStarJob/1910599147004108800/auto_found.json
```

## ⚡ 性能优化

### 1. 连接复用
- 单次认证，多次使用
- 连接池管理
- 自动重试机制

### 2. 智能缓存
- 文件列表缓存
- 避免重复扫描
- 增量更新机制

### 3. 并发控制
- 合理的请求频率
- 错误重试策略
- 超时处理机制

## 🔧 故障排除

### 常见问题

#### 1. 连接失败
```bash
# 检查网络连接
curl -I https://collector0109.blob.core.windows.net

# 验证认证信息
az login --service-principal
```

#### 2. 文件不存在
```bash
# 列出可用文件
python3 src/azure_resource_reader.py --account collector0109 --parse-mode AmazonReviewStarJob 1910599147004108800 json --list-jobs
```

#### 3. JSON解析错误
- 检查文件是否为有效JSON格式
- 确认文件编码为UTF-8
- 验证文件是否完整下载

### 日志分析
```bash
# 启用详细日志
export AZURE_LOG_LEVEL=DEBUG
python3 src/azure_resource_reader.py --account collector0109 --parse-mode AmazonReviewStarJob 1910599147004108800 json
```

## 🎯 最佳实践

### 1. 选择合适的模式
- **--with-parse模式**: 大多数场景的首选，特别是需要对照原始数据和解析结果
- **纯解析模式**: 仅需解析数据或需要批量处理解析文件

### 2. 参数管理
- 使用有意义的任务类型和task_id组合
- 遵循标准的命名约定
- 记录重要的参数映射关系

### 3. 文件组织
- 优先使用`--with-parse`模式保持文件统一性
- 定期清理本地下载文件
- 备份重要的解析结果

### 4. 性能优化
- 批量下载时设置合理间隔
- 使用`--info-only`预览大文件
- 适当使用`--no-mapping`减少开销

### 5. 安全考虑
- 妥善保管认证凭据
- 定期轮换访问密钥
- 限制网络访问范围

---

## 📚 相关文档

- [Azure资源读取器映射指南](./azure-resource-reader-mapping-guide.md)
- [Azure Storage指南](./azure-storage-guide.md)
- [主项目README](../README.md)

---

> 💡 **提示**: 
> - **路径结构已修正**: 现在使用 `parse/parse/{任务类型}/{task_id}/*`
> - **推荐使用--with-parse模式**: 大多数场景下更便捷高效
> - 解析模式专为JSON数据处理优化，提供了智能文件发现、格式验证和结构分析等特色功能