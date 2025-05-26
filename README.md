# Shulex-Anker 数据验证工具

这个工具用于验证和处理Shulex-Anker的数据问题。主要功能包括连接数据库查询数据、处理业务部门提供的CSV/Excel文件，以及进行数据校验和分析。

## 功能特点

- 连接Azure MySQL数据库进行数据查询
- 读取并处理CSV/Excel格式的问题反馈文件
- 进行数据验证和分析
- 生成数据分析报告
- 重新提交解析任务（支持批量和逐个提交）
- 数据库问题诊断和错误分析
- **🆕 Azure Storage集成** - 支持Blob Storage、Queue Storage、File Storage操作

## 安装步骤

1. 确保已安装Python 3.x
2. 克隆本仓库到本地
3. 安装依赖包：

```bash
pip install -r requirements.txt
```

4. 配置数据库连接：
   - 编辑config目录下的.env文件填入数据库凭据，或直接使用默认配置

## 使用方法

### 验证数据库连接

```bash
python3 src/main.py test_connection
```

### 处理CSV/Excel文件

```bash
python3 src/main.py process_file --file [文件路径] --type [csv|excel]
```

### Azure Storage操作

```bash
# 测试Azure Storage连接
python3 src/azure_storage_client.py

# 在代码中使用Azure Storage
from src.azure_storage_client import AzureStorageClient
client = AzureStorageClient("your_storage_account_name")
```

### 🆕 Azure资源读取器（支持任务映射）

Azure资源读取器专门用于从Azure Storage中读取线上任务数据，支持自动的参数转换和文件映射管理。

```bash
# 🆕 推荐：同时获取原始数据和解析数据
python3 src/azure_resource_reader.py AmazonReviewStarJob 2796867471 html --with-parse
python3 src/azure_resource_reader.py AmazonListingJob 1925464883027513344 json --with-parse

# 指定特定文件的同时获取解析数据
python3 src/azure_resource_reader.py AmazonReviewStarJob 2796867471 html --with-parse --files page_1.gz

# 读取原始数据文件（yiya0110账户）
python3 src/azure_resource_reader.py AmazonListingJob 1925464883027513344 html
python3 src/azure_resource_reader.py AmazonReviewStarJob 2796867471 html

# 🆕 读取解析文件（collector0109账户）- 路径已修正
# 路径结构: parse/parse/{任务类型}/{task_id}/*
python3 src/azure_resource_reader.py --account collector0109 --parse-mode AmazonReviewStarJob 1910599147004108800 json

# 指定解析文件名
python3 src/azure_resource_reader.py --account collector0109 --parse-mode AmazonReviewStarJob 1910599147004108800 json --files result.json

# 通用功能
# 查看当前任务映射
python3 src/azure_resource_reader.py --show-mapping

# 禁用映射文件生成
python3 src/azure_resource_reader.py AmazonListingJob 2796867471 html --no-mapping

# 获取文件信息而不下载
python3 src/azure_resource_reader.py AmazonListingJob 2796867471 html --info-only

# 列出指定任务类型的任务
python3 src/azure_resource_reader.py AmazonListingJob 2796867471 html --list-jobs
```

**任务映射功能**:
- 自动记录输入参数到下载路径的映射关系
- 支持完整任务ID和job_id两种输入方式
- 映射文件位置: `data/output/task_mapping.json`
- 支持查看历史映射和文件统计

**🆕 --with-parse模式特点**:
- **一站式下载**: 一个命令同时获取原始数据和解析数据
- **统一保存**: 所有文件保存在同一目录下
- **智能映射**: 自动记录两种数据的映射关系
- **错误容忍**: 即使解析文件不存在，原始文件仍可正常下载

**支持的存储账户**:
- `yiya0110`: 原始任务数据（AmazonListingJob, AmazonReviewStarJob）
- `collector0109`: JSON解析结果数据（解析模式）

**支持的任务类型**:
- `AmazonListingJob`: login.gz, normal.gz
- `AmazonReviewStarJob`: page_1.gz ~ page_5.gz
- `解析模式`: 自动查找JSON文件

详细文档: [Azure资源读取器映射指南](./notes/azure-resource-reader-mapping-guide.md) 📋

### 分析任务数据库问题

```bash
python3 src/main.py analyze_tasks_with_db --file [Excel文件路径] --column "解决进度" --nrows 10
```

### 重新提交解析任务

```bash
# 直接指定任务ID
python3 src/main.py resubmit_parse_jobs --job-ids SL2813610252 SL2789485480

# 从txt文件批量提交
python3 src/main.py resubmit_from_txt_file --file "data/input/job_ids.txt" --nrows 5

# 逐个提交（推荐用于大量任务）
python3 src/main.py resubmit_from_txt_file_one_by_one --file "data/input/job_ids.txt" --nrows 445 --delay-seconds 1.0
```

### 运行完整验证流程

```bash
python3 src/main.py validate --file [文件路径] --output [输出路径]
```

## 项目结构

```
ankerTestValid/
├── config/         # 配置文件
│   ├── azure_storage_config.py # Azure Storage配置
│   └── db_config.py            # 数据库配置
├── data/           # 数据文件目录
│   ├── input/      # 输入文件
│   └── output/     # 输出文件
│       ├── AmazonListingJob/    # 原始任务数据
│       ├── AmazonReviewStarJob/ # 原始任务数据  
│       ├── parse/               # 🆕 解析结果数据
│       └── task_mapping.json   # 🆕 任务映射文件
├── docs/           # 文档资料
├── notes/          # 知识笔记
│   ├── azure-resource-reader-mapping-guide.md # 映射功能指南
│   ├── azure-parse-mode-guide.md              # 🆕 解析模式指南
│   └── azure-storage-guide.md                 # Storage操作指南
├── src/            # 源代码
│   ├── db/         # 数据库相关模块
│   ├── file_processors/ # 文件处理模块
│   ├── azure_storage_client.py   # Azure Storage客户端
│   ├── azure_resource_reader.py  # 🆕 Azure资源读取器（支持解析模式）
│   ├── pdf_processor.py # PDF处理工具
│   └── main.py     # 主程序入口
└── tests/          # 测试代码
```

## 📚 知识导航

### Azure开发者Python指南

本项目包含Azure开发者Python相关的知识文档，提取自官方文档，包含553页的详细内容。

#### 📋 文档概览
- **总页数**: 553页
- **内容量**: 434,782字符，59,634词
- **代码示例**: 937个相关代码行
- **涵盖概念**: 13个核心Azure服务和概念

#### 🗂️ 知识分类

##### 📖 核心文档
- [📄 Azure开发者Python完整摘要](./notes/azure-developer-python-summary.md) - 文档总览和统计信息

##### 🔧 技术主题
- [🚀 介绍与概述](./notes/azure-introduction.md) - Azure Python开发介绍
- [⚙️ 环境搭建](./notes/azure-setup.md) - 开发环境配置和安装
- [🔐 身份验证](./notes/azure-authentication.md) - Azure认证和授权
- [🚢 部署指南](./notes/azure-deployment.md) - 应用部署策略
- [💡 示例代码](./notes/azure-examples.md) - 实际代码示例
- [🔧 故障排除](./notes/azure-troubleshooting.md) - 常见问题解决
- [🗄️ **Azure Storage指南**](./notes/azure-storage-guide.md) - **Storage服务完整操作指南** ⭐

##### 🎯 涉及的Azure服务
- **Azure Functions** - 无服务器计算
- **Azure App Service** - Web应用托管
- **Azure Storage** - 云存储服务 ⭐
  - **Blob Storage** 💾 - 对象存储（文档、图片、视频）
  - **Queue Storage** 📬 - 消息队列服务
  - **File Storage** 📁 - 文件共享服务
- **Azure SQL** - 关系数据库
- **Azure Cosmos DB** - NoSQL数据库
- **Azure Service Bus** - 消息队列
- **Azure Event Hub** - 事件流处理
- **Azure Key Vault** - 密钥管理
- **Azure Active Directory** - 身份管理
- **Azure DevOps** - 开发运维
- **Azure CLI** - 命令行工具

#### 🔍 快速查找

**按场景查找:**
- 🔄 **数据处理**: Azure Storage, Azure SQL, Azure Cosmos DB
- 🌐 **Web开发**: Azure App Service, Azure Functions
- 🔐 **安全认证**: Azure Active Directory, Azure Key Vault
- 📊 **监控部署**: Azure DevOps, Azure CLI
- 📨 **消息队列**: Azure Service Bus, Azure Event Hub
- **💾 文件存储和管理**: Azure Storage (Blob/File/Queue) ⭐

**按开发阶段查找:**
1. **起步阶段**: [环境搭建](./notes/azure-setup.md) → [介绍概览](./notes/azure-introduction.md)
2. **开发阶段**: [示例代码](./notes/azure-examples.md) → [身份验证](./notes/azure-authentication.md) → [**Storage操作**](./notes/azure-storage-guide.md) ⭐
3. **部署阶段**: [部署指南](./notes/azure-deployment.md)
4. **维护阶段**: [故障排除](./notes/azure-troubleshooting.md)

#### 📚 完整文档
如需查看完整的原始文档内容，请参考: [Azure开发者Python完整文本](./notes/azure-developer-python-full-text.txt)

### 🗄️ Azure Storage 快速入门

#### 🔧 已配置认证信息
```python
# 服务主体认证（已配置）
AZURE_STORAGE_CONFIG = {
    'client_id': 'YOUR_AZURE_CLIENT_ID',
    'tenant_id': 'YOUR_AZURE_TENANT_ID',
    'client_secret': 'YOUR_AZURE_CLIENT_SECRET',
    'subscription_id': 'YOUR_AZURE_SUBSCRIPTION_ID',
    'resource_group': 'shulex-prod-usw3-rg-1219'
}
```

#### 📖 学习资源
- [🗄️ Azure Storage完整指南](./notes/azure-storage-guide.md) - 基于官方文档的详细操作指南
- [Official Azure Storage Samples](https://learn.microsoft.com/en-us/azure/storage/common/storage-samples-python) - 微软官方示例

#### 🚀 快速开始
1. **安装依赖**: `pip install azure-storage-blob azure-identity`
2. **创建客户端**: 使用 `AzureStorageClient` 类
3. **基本操作**: 上传、下载、列出、删除文件
4. **高级功能**: SAS URL生成、元数据管理、并发操作

---

## 注意事项

- 请勿将数据库凭据直接硬编码到代码中
- 处理大文件时注意内存使用
- 逐个提交大量任务时建议设置适当的延迟时间
- 定期备份重要的分析结果文件
- **Azure Storage认证信息已预配置，需要存储账户名才能连接** ⚠️ 
- **🆕 解析文件路径结构**: `parse/parse/{任务类型}/{task_id}/*` （已修正）