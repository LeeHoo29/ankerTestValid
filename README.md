# 任务检查工具看板

## 项目概述

这是一个统一的任务管理和监控平台，提供Web界面来管理和监控各种工具模块的执行。目前支持Azure Resource Reader模块，未来可以扩展支持更多工具。

## 功能特性

### 🎯 核心功能
- **统一看板**: 集中管理多种工具模块
- **任务监控**: 实时监控任务执行状态
- **历史记录**: 完整的任务执行历史
- **文件管理**: 查看和下载任务输出文件
- **对比查看**: 并排对比HTML和JSON数据

### 🔧 当前支持的工具模块

#### Azure Resource Reader
- 支持AmazonReviewStarJob和AmazonListingJob任务类型
- 多种输出格式：HTML、TXT、JSON、RAW
- 解析模式支持（--with-parse）
- 自动任务ID转换
- 文件自动解压和组织

### 🚀 未来扩展计划
- 数据库检查工具
- API监控模块
- 日志分析工具
- 系统设置管理
- 更多工具模块...

## 快速开始

### 环境要求
- Python 3.9+
- Flask
- 其他依赖见 `requirements.txt`

### 安装依赖
```bash
pip install -r requirements.txt
```

### 环境变量配置
复制环境变量模板：
```bash
cp .env.example .env
```

编辑 `.env` 文件，填入真实的Azure认证信息：
```bash
# Azure Storage 认证信息
AZURE_STORAGE_CLIENT_ID=your_client_id
AZURE_STORAGE_TENANT_ID=your_tenant_id
AZURE_STORAGE_CLIENT_SECRET=your_client_secret
AZURE_STORAGE_SUB_ID=your_subscription_id
AZURE_STORAGE_RESOURCE_GROUP=your_resource_group

# 兼容性变量名（可选）
AZURE_CLIENT_ID=your_client_id
AZURE_TENANT_ID=your_tenant_id
AZURE_CLIENT_SECRET=your_client_secret
AZURE_SUBSCRIPTION_ID=your_subscription_id
AZURE_RESOURCE_GROUP=your_resource_group
```

### 启动应用
```bash
python3 web_app.py
```

访问地址：http://localhost:5001

## 使用指南

### Azure Resource Reader 模块

1. **选择任务类型**：
   - AmazonReviewStarJob：Amazon评论星级任务
   - AmazonListingJob：Amazon商品列表任务

2. **输入任务ID**：
   - 支持长任务ID或Job ID
   - 系统会自动进行转换

3. **选择输出类型**：
   - HTML：网页格式（推荐）
   - TXT：纯文本格式
   - JSON：结构化数据
   - RAW：原始压缩文件

4. **启用解析模式**：
   - 勾选后会同时获取原始数据和解析数据
   - 使用优化算法提高处理效率

### 任务管理

- **实时监控**：在主页面查看任务执行状态
- **历史记录**：在任务历史页面查看所有执行记录
- **文件查看**：点击已完成任务查看输出文件
- **对比功能**：并排查看HTML快照和JSON解析结果

## 项目结构

```
ankerTestValid/
├── web_app.py              # 主应用文件
├── templates/              # HTML模板
│   ├── index.html         # 主页面
│   ├── tasks.html         # 任务历史页面
│   └── compare.html       # 对比查看页面
├── static/                # 静态资源
│   ├── style.css          # 样式文件
│   └── js/                # JavaScript文件
├── src/                   # 工具模块源码
│   └── azure_resource_reader.py
├── config/                # 配置文件
│   └── azure_storage_config.py
├── data/                  # 数据目录
│   └── output/            # 任务输出文件
├── docs/                  # 文档
├── .env                   # 环境变量（需要创建）
├── .env.example           # 环境变量模板
├── requirements.txt       # Python依赖
└── README.md             # 项目说明
```

## 技术架构

### 后端技术
- **Flask**: Web框架
- **Python**: 主要编程语言
- **多线程**: 后台任务执行
- **JSON**: 数据存储和交换

### 前端技术
- **HTML5**: 页面结构
- **CSS3**: 样式设计
- **JavaScript**: 交互逻辑
- **Font Awesome**: 图标库

### 特色功能
- **响应式设计**: 支持桌面和移动设备
- **实时更新**: 任务状态实时刷新
- **文件缓存**: 优化文件加载性能
- **错误处理**: 完善的错误提示机制

## 开发指南

### 添加新工具模块

1. **创建工具脚本**：在 `src/` 目录下创建新的工具脚本
2. **更新路由**：在 `web_app.py` 中添加新的路由处理
3. **添加菜单项**：在 `templates/index.html` 中添加左侧菜单项
4. **创建模板**：为新工具创建专门的HTML模板

### 环境变量管理

项目支持两套环境变量命名：
- `AZURE_STORAGE_*`：主要变量名
- `AZURE_*`：兼容性变量名

配置文件会自动选择可用的变量名。

## 安全说明

- ⚠️ **重要**：`.env` 文件包含敏感信息，已添加到 `.gitignore`
- 🔒 所有Azure认证信息都通过环境变量管理
- 📁 输出文件仅限于 `data/output` 目录访问
- 🛡️ 文件路径安全检查防止目录遍历攻击

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证。

## 联系方式

如有问题或建议，请通过以下方式联系：
- 创建 Issue
- 提交 Pull Request
- 发送邮件

---

**注意**：这是一个内部工具，请确保在安全的环境中使用，并妥善保管Azure认证信息。