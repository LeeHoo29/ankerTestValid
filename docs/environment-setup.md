# 环境变量配置指南

## 概述

本项目使用环境变量来管理Azure认证信息，确保敏感信息不会被提交到版本控制系统中。

## 配置步骤

### 1. 复制环境变量模板

```bash
cp .env.example .env
```

### 2. 编辑 `.env` 文件

使用文本编辑器打开 `.env` 文件，填入你的Azure认证信息：

```bash
# Azure Storage 认证配置
AZURE_STORAGE_CLIENT_ID=你的Azure客户端ID
AZURE_STORAGE_TENANT_ID=你的Azure租户ID
AZURE_STORAGE_CLIENT_SECRET=你的Azure客户端密钥
AZURE_STORAGE_SUB_ID=你的Azure订阅ID
AZURE_STORAGE_RESOURCE_GROUP=你的资源组名称

# Azure SDK 标准环境变量名称
AZURE_CLIENT_ID=你的Azure客户端ID
AZURE_TENANT_ID=你的Azure租户ID
AZURE_CLIENT_SECRET=你的Azure客户端密钥
AZURE_SUBSCRIPTION_ID=你的Azure订阅ID
```

### 3. 安装依赖

确保安装了 `python-dotenv` 库：

```bash
pip install python-dotenv
```

或者使用项目的requirements.txt：

```bash
pip install -r requirements.txt
```

## 安全注意事项

- ✅ `.env` 文件已被添加到 `.gitignore` 中，不会被提交到Git仓库
- ✅ 使用 `.env.example` 作为模板文件，可以安全地提交到Git
- ⚠️ 永远不要将真实的认证信息提交到版本控制系统
- ⚠️ 在生产环境中，建议使用更安全的密钥管理服务

## 验证配置

运行以下命令验证配置是否正确：

```bash
python3 -c "from config.azure_storage_config import AZURE_STORAGE_CONFIG; print('配置加载成功:', AZURE_STORAGE_CONFIG['client_id'][:8] + '...')"
```

## 环境变量说明

| 变量名 | 说明 | 示例格式 |
|--------|------|----------|
| `AZURE_STORAGE_CLIENT_ID` | Azure应用程序客户端ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `AZURE_STORAGE_TENANT_ID` | Azure租户ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `AZURE_STORAGE_CLIENT_SECRET` | Azure应用程序客户端密钥 | `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `AZURE_STORAGE_SUB_ID` | Azure订阅ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `AZURE_STORAGE_RESOURCE_GROUP` | Azure资源组名称 | `your-resource-group-name` |

## 故障排除

### 问题：配置文件找不到环境变量

**解决方案：**
1. 确认 `.env` 文件存在于项目根目录
2. 检查 `.env` 文件中的变量名是否正确
3. 确认没有多余的空格或特殊字符

### 问题：Azure认证失败

**解决方案：**
1. 验证Azure认证信息是否正确
2. 确认Azure应用程序权限配置
3. 检查网络连接和防火墙设置 