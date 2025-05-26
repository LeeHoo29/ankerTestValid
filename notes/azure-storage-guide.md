# 🗄️ Azure Storage Python 开发指南

基于官方文档: [Azure Storage samples using Python client libraries](https://learn.microsoft.com/en-us/azure/storage/common/storage-samples-python)

## 📋 概述

Azure Storage提供了多种数据存储服务，通过Python SDK可以轻松集成到应用程序中。本指南涵盖Blob Storage、Queue Storage和File Storage的主要操作。

### 🎯 支持的存储服务

- **Blob Storage** 💾 - 对象存储，适用于文档、图片、视频等非结构化数据
- **Queue Storage** 📬 - 消息队列服务，用于应用程序之间的异步通信  
- **File Storage** 📁 - 文件共享服务，提供SMB协议访问
- **Table Storage** 📊 - NoSQL键值存储（已被Cosmos DB取代）

## 🔧 环境设置

### 1. 安装必要的Python包

```bash
pip install azure-storage-blob>=12.8.1
pip install azure-storage-queue>=12.1.6
pip install azure-storage-file-share>=12.4.2
pip install azure-identity>=1.8.0
pip install azure-mgmt-storage>=19.0.0
```

### 2. 认证配置

我们使用Azure服务主体进行认证：

```python
# 认证信息（已配置）
AZURE_STORAGE_CONFIG = {
    'client_id': 'YOUR_AZURE_CLIENT_ID',
    'tenant_id': 'YOUR_AZURE_TENANT_ID', 
    'client_secret': 'YOUR_AZURE_CLIENT_SECRET',
    'subscription_id': 'YOUR_AZURE_SUBSCRIPTION_ID',
    'resource_group': 'shulex-prod-usw3-rg-1219'
}
```

## 🗂️ Blob Storage 操作

### 基础连接和认证

```python
from azure.identity import ClientSecretCredential
from azure.storage.blob import BlobServiceClient

# 创建认证凭据
credential = ClientSecretCredential(
    tenant_id="YOUR_AZURE_TENANT_ID",
    client_id="YOUR_AZURE_CLIENT_ID", 
    client_secret="YOUR_AZURE_CLIENT_SECRET"
)

# 创建Blob服务客户端
storage_account_name = "your_storage_account"  # 替换为实际账户名
account_url = f"https://{storage_account_name}.blob.core.windows.net"
blob_service_client = BlobServiceClient(account_url=account_url, credential=credential)
```

### 容器操作

```python
# 列出所有容器
def list_containers():
    containers = blob_service_client.list_containers()
    for container in containers:
        print(f"容器: {container.name}")

# 创建容器
def create_container(container_name):
    container_client = blob_service_client.get_container_client(container_name)
    container_client.create_container()
    print(f"容器 {container_name} 创建成功")

# 删除容器
def delete_container(container_name):
    container_client = blob_service_client.get_container_client(container_name)
    container_client.delete_container()
    print(f"容器 {container_name} 删除成功")
```

### Blob操作

#### 上传Blob

```python
# 上传文本数据
def upload_text_blob(container_name, blob_name, text_data):
    blob_client = blob_service_client.get_blob_client(
        container=container_name, 
        blob=blob_name
    )
    blob_client.upload_blob(text_data, overwrite=True)
    print(f"文本上传成功: {blob_name}")

# 上传文件
def upload_file_blob(container_name, local_file_path, blob_name=None):
    if blob_name is None:
        blob_name = os.path.basename(local_file_path)
    
    blob_client = blob_service_client.get_blob_client(
        container=container_name,
        blob=blob_name
    )
    
    with open(local_file_path, 'rb') as data:
        blob_client.upload_blob(data, overwrite=True)
    print(f"文件上传成功: {local_file_path} -> {blob_name}")

# 批量上传（适用于大文件）
def upload_large_file(container_name, local_file_path, blob_name):
    blob_client = blob_service_client.get_blob_client(
        container=container_name,
        blob=blob_name  
    )
    
    with open(local_file_path, 'rb') as data:
        blob_client.upload_blob(
            data,
            overwrite=True,
            max_concurrency=4,  # 并发上传
            blob_type="BlockBlob"
        )
```

#### 下载Blob

```python
# 下载为文本
def download_text_blob(container_name, blob_name):
    blob_client = blob_service_client.get_blob_client(
        container=container_name,
        blob=blob_name
    )
    blob_data = blob_client.download_blob()
    return blob_data.content_as_text()

# 下载到文件
def download_file_blob(container_name, blob_name, local_file_path):
    blob_client = blob_service_client.get_blob_client(
        container=container_name,
        blob=blob_name
    )
    
    with open(local_file_path, 'wb') as file:
        blob_data = blob_client.download_blob()
        file.write(blob_data.readall())
    print(f"文件下载成功: {blob_name} -> {local_file_path}")
```

#### 列出和管理Blob

```python
# 列出容器中的所有Blob
def list_blobs(container_name, prefix=None):
    container_client = blob_service_client.get_container_client(container_name)
    blobs = container_client.list_blobs(name_starts_with=prefix)
    
    for blob in blobs:
        print(f"Blob: {blob.name}, 大小: {blob.size} bytes, 修改时间: {blob.last_modified}")

# 获取Blob属性
def get_blob_properties(container_name, blob_name):
    blob_client = blob_service_client.get_blob_client(
        container=container_name,
        blob=blob_name
    )
    properties = blob_client.get_blob_properties()
    
    return {
        'size': properties.size,
        'content_type': properties.content_settings.content_type,
        'last_modified': properties.last_modified,
        'etag': properties.etag
    }

# 删除Blob
def delete_blob(container_name, blob_name):
    blob_client = blob_service_client.get_blob_client(
        container=container_name,
        blob=blob_name
    )
    blob_client.delete_blob()
    print(f"Blob删除成功: {blob_name}")
```

### 高级功能

#### 生成SAS URL（共享访问签名）

```python
from azure.storage.blob import generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta

def generate_blob_sas_url(container_name, blob_name, expiry_hours=24):
    # 设置权限
    permissions = BlobSasPermissions(read=True, write=False)
    
    # 生成SAS token（注意：使用服务主体时需要不同的方法）
    sas_token = generate_blob_sas(
        account_name=storage_account_name,
        container_name=container_name,
        blob_name=blob_name,
        account_key=None,  # 使用服务主体时为None
        permission=permissions,
        expiry=datetime.utcnow() + timedelta(hours=expiry_hours)
    )
    
    return f"{account_url}/{container_name}/{blob_name}?{sas_token}"
```

#### Blob元数据操作

```python
# 设置Blob元数据
def set_blob_metadata(container_name, blob_name, metadata):
    blob_client = blob_service_client.get_blob_client(
        container=container_name,
        blob=blob_name
    )
    blob_client.set_blob_metadata(metadata)
    print(f"元数据设置成功: {blob_name}")

# 获取Blob元数据
def get_blob_metadata(container_name, blob_name):
    blob_client = blob_service_client.get_blob_client(
        container=container_name,
        blob=blob_name
    )
    properties = blob_client.get_blob_properties()
    return properties.metadata
```

## 📬 Queue Storage 操作

```python
from azure.storage.queue import QueueServiceClient

# 创建Queue服务客户端
queue_url = f"https://{storage_account_name}.queue.core.windows.net"
queue_service_client = QueueServiceClient(account_url=queue_url, credential=credential)

# 创建队列
def create_queue(queue_name):
    queue_client = queue_service_client.get_queue_client(queue_name)
    queue_client.create_queue()
    print(f"队列创建成功: {queue_name}")

# 发送消息
def send_message(queue_name, message):
    queue_client = queue_service_client.get_queue_client(queue_name)
    queue_client.send_message(message)
    print(f"消息发送成功: {message}")

# 接收消息
def receive_messages(queue_name, max_messages=10):
    queue_client = queue_service_client.get_queue_client(queue_name)
    messages = queue_client.receive_messages(max_messages=max_messages)
    
    for message in messages:
        print(f"收到消息: {message.content}")
        # 处理完消息后删除
        queue_client.delete_message(message.id, message.pop_receipt)
```

## 📁 File Storage 操作

```python
from azure.storage.fileshare import ShareServiceClient

# 创建File服务客户端
file_url = f"https://{storage_account_name}.file.core.windows.net"
file_service_client = ShareServiceClient(account_url=file_url, credential=credential)

# 创建文件共享
def create_file_share(share_name):
    share_client = file_service_client.get_share_client(share_name)
    share_client.create_share()
    print(f"文件共享创建成功: {share_name}")

# 上传文件
def upload_file_to_share(share_name, file_name, local_file_path):
    file_client = file_service_client.get_file_client(
        share=share_name,
        file_path=file_name
    )
    
    with open(local_file_path, 'rb') as data:
        file_client.upload_file(data)
    print(f"文件上传成功: {file_name}")

# 下载文件
def download_file_from_share(share_name, file_name, local_file_path):
    file_client = file_service_client.get_file_client(
        share=share_name,
        file_path=file_name
    )
    
    with open(local_file_path, 'wb') as file:
        data = file_client.download_file()
        file.write(data.readall())
    print(f"文件下载成功: {file_name}")
```

## 🚀 实际应用场景

### 1. 数据备份和归档

```python
def backup_local_folder_to_blob(local_folder, container_name, prefix="backup/"):
    """将本地文件夹备份到Blob Storage"""
    for root, dirs, files in os.walk(local_folder):
        for file in files:
            local_path = os.path.join(root, file)
            relative_path = os.path.relpath(local_path, local_folder)
            blob_name = prefix + relative_path.replace("\\", "/")
            
            upload_file_blob(container_name, local_path, blob_name)
            print(f"备份完成: {relative_path}")
```

### 2. 日志文件处理

```python
def process_log_files(container_name, log_prefix="logs/"):
    """处理存储在Blob中的日志文件"""
    container_client = blob_service_client.get_container_client(container_name)
    blobs = container_client.list_blobs(name_starts_with=log_prefix)
    
    for blob in blobs:
        if blob.name.endswith('.log'):
            # 下载并处理日志
            log_content = download_text_blob(container_name, blob.name)
            # 在这里添加日志处理逻辑
            print(f"处理日志文件: {blob.name}")
```

### 3. 数据管道集成

```python
def data_pipeline_example():
    """数据处理管道示例"""
    # 1. 从队列接收处理任务
    task_message = receive_messages("data-processing-queue", 1)
    
    # 2. 从Blob下载数据文件
    data_content = download_text_blob("raw-data", "input.csv")
    
    # 3. 处理数据（这里是示例）
    processed_data = data_content.upper()  # 简单的处理示例
    
    # 4. 上传处理结果
    upload_text_blob("processed-data", "output.csv", processed_data)
    
    # 5. 发送完成通知
    send_message("notification-queue", "数据处理完成")
```

## 🔧 最佳实践

### 1. 错误处理和重试

```python
from azure.core.exceptions import AzureError
import time

def robust_upload(container_name, blob_name, data, max_retries=3):
    """带重试机制的上传"""
    for attempt in range(max_retries):
        try:
            blob_client = blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )
            blob_client.upload_blob(data, overwrite=True)
            print(f"上传成功: {blob_name}")
            return True
        except AzureError as e:
            print(f"上传失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 指数退避
    return False
```

### 2. 性能优化

```python
# 并发上传多个文件
import concurrent.futures

def upload_files_concurrently(container_name, file_list, max_workers=4):
    """并发上传多个文件"""
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for local_path in file_list:
            blob_name = os.path.basename(local_path)
            future = executor.submit(upload_file_blob, container_name, local_path, blob_name)
            futures.append(future)
        
        # 等待所有上传完成
        concurrent.futures.wait(futures)
        print(f"批量上传完成: {len(file_list)} 个文件")
```

### 3. 成本优化

```python
# 设置Blob访问层级（冷热数据分层）
def set_blob_access_tier(container_name, blob_name, access_tier="Cool"):
    """设置Blob访问层级来优化成本"""
    blob_client = blob_service_client.get_blob_client(
        container=container_name,
        blob=blob_name
    )
    blob_client.set_standard_blob_tier(access_tier)
    print(f"访问层级设置为: {access_tier}")
```

## 🔗 相关资源

- [Azure Storage Python SDK文档](https://learn.microsoft.com/en-us/azure/storage/common/storage-samples-python)
- [Azure Blob Storage Python快速入门](https://learn.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-python)
- [Azure Storage最佳实践](https://learn.microsoft.com/en-us/azure/storage/common/storage-performance-checklist)

## 📝 下一步

1. **获取存储账户名**: 联系Azure管理员获取实际的存储账户名称
2. **测试连接**: 使用提供的认证信息测试连接
3. **实践操作**: 尝试上传、下载、列出文件等基本操作
4. **集成到项目**: 将Azure Storage集成到现有的数据处理流程中

---

*基于Azure官方文档整理，最后更新: 2025年5月23日* 