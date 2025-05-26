#!/usr/bin/env python3
"""
Azure Storage 客户端工具类
基于官方文档: https://learn.microsoft.com/en-us/azure/storage/common/storage-samples-python
"""
import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, BinaryIO
from datetime import datetime, timedelta
import asyncio

# Azure Storage SDK imports
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.storage.blob import BlobProperties, ContentSettings
from azure.storage.queue import QueueServiceClient, QueueClient
from azure.storage.filedatalake import DataLakeServiceClient
from azure.core.exceptions import AzureError, ResourceNotFoundError

# 导入项目配置
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.azure_storage_config import (
    AZURE_STORAGE_CONFIG, 
    STORAGE_ACCOUNT_CONFIG,
    BLOB_OPERATIONS_CONFIG,
    set_azure_environment_variables,
    get_storage_account_url
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AzureStorageClient:
    """Azure Storage 综合客户端"""
    
    def __init__(self, storage_account_name: str, use_default_credential: bool = False):
        """
        初始化Azure Storage客户端
        
        Args:
            storage_account_name: Azure存储账户名
            use_default_credential: 是否使用默认凭据，False则使用服务主体认证
        """
        self.storage_account_name = storage_account_name
        self.account_url = get_storage_account_url(storage_account_name, 'blob')
        
        # 设置环境变量
        set_azure_environment_variables()
        
        # 创建认证凭据
        if use_default_credential:
            self.credential = DefaultAzureCredential()
        else:
            self.credential = ClientSecretCredential(
                tenant_id=AZURE_STORAGE_CONFIG['tenant_id'],
                client_id=AZURE_STORAGE_CONFIG['client_id'],
                client_secret=AZURE_STORAGE_CONFIG['client_secret']
            )
        
        # 初始化各种服务客户端
        self.blob_service_client = None
        self.queue_service_client = None
        self.datalake_service_client = None
        
        self._initialize_clients()
    
    def _initialize_clients(self):
        """初始化各种Azure Storage服务客户端"""
        try:
            # Blob Storage客户端
            self.blob_service_client = BlobServiceClient(
                account_url=self.account_url,
                credential=self.credential
            )
            
            # Queue Storage客户端
            queue_url = get_storage_account_url(self.storage_account_name, 'queue')
            self.queue_service_client = QueueServiceClient(
                account_url=queue_url,
                credential=self.credential
            )
            
            # Data Lake客户端 (如果需要)
            self.datalake_service_client = DataLakeServiceClient(
                account_url=self.account_url,
                credential=self.credential
            )
            
            logger.info(f"Azure Storage客户端初始化成功: {self.storage_account_name}")
            
        except Exception as e:
            logger.error(f"初始化Azure Storage客户端失败: {str(e)}")
            raise
    
    def test_connection(self) -> bool:
        """
        测试Azure Storage连接
        
        Returns:
            bool: 连接成功返回True
        """
        try:
            # 尝试列出容器来测试连接
            containers = list(self.blob_service_client.list_containers())
            logger.info(f"✅ 连接成功! 找到 {len(containers)} 个容器")
            return True
        except Exception as e:
            logger.error(f"❌ 连接失败: {str(e)}")
            return False
    
    def list_containers(self) -> List[Dict]:
        """
        列出所有Blob容器
        
        Returns:
            List[Dict]: 容器信息列表
        """
        try:
            containers = []
            for container in self.blob_service_client.list_containers():
                containers.append({
                    'name': container.name,
                    'last_modified': container.last_modified,
                    'metadata': container.metadata or {}
                })
            logger.info(f"列出 {len(containers)} 个容器")
            return containers
        except Exception as e:
            logger.error(f"列出容器失败: {str(e)}")
            return []
    
    def create_container(self, container_name: str, metadata: Optional[Dict] = None) -> bool:
        """
        创建Blob容器
        
        Args:
            container_name: 容器名称
            metadata: 容器元数据
            
        Returns:
            bool: 创建成功返回True
        """
        try:
            container_client = self.blob_service_client.get_container_client(container_name)
            container_client.create_container(metadata=metadata)
            logger.info(f"✅ 容器创建成功: {container_name}")
            return True
        except Exception as e:
            logger.error(f"❌ 创建容器失败: {str(e)}")
            return False
    
    def upload_blob(self, container_name: str, blob_name: str, data: Union[str, bytes, BinaryIO], 
                   overwrite: bool = True, metadata: Optional[Dict] = None) -> bool:
        """
        上传Blob数据
        
        Args:
            container_name: 容器名称
            blob_name: Blob名称
            data: 要上传的数据
            overwrite: 是否覆盖已存在的Blob
            metadata: Blob元数据
            
        Returns:
            bool: 上传成功返回True
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name, 
                blob=blob_name
            )
            
            # 配置内容设置
            content_settings = None
            if blob_name.endswith('.json'):
                content_settings = ContentSettings(content_type='application/json')
            elif blob_name.endswith('.csv'):
                content_settings = ContentSettings(content_type='text/csv')
            elif blob_name.endswith('.xlsx'):
                content_settings = ContentSettings(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            
            blob_client.upload_blob(
                data=data,
                overwrite=overwrite,
                metadata=metadata,
                content_settings=content_settings,
                max_concurrency=BLOB_OPERATIONS_CONFIG['max_concurrency'],
                timeout=BLOB_OPERATIONS_CONFIG['timeout']
            )
            
            logger.info(f"✅ Blob上传成功: {container_name}/{blob_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Blob上传失败: {str(e)}")
            return False
    
    def upload_file(self, container_name: str, local_file_path: str, 
                   blob_name: Optional[str] = None, overwrite: bool = True) -> bool:
        """
        上传本地文件到Blob Storage
        
        Args:
            container_name: 容器名称
            local_file_path: 本地文件路径
            blob_name: Blob名称，如果为None则使用文件名
            overwrite: 是否覆盖已存在的Blob
            
        Returns:
            bool: 上传成功返回True
        """
        try:
            file_path = Path(local_file_path)
            if not file_path.exists():
                logger.error(f"本地文件不存在: {local_file_path}")
                return False
            
            if blob_name is None:
                blob_name = file_path.name
            
            with open(file_path, 'rb') as data:
                return self.upload_blob(
                    container_name=container_name,
                    blob_name=blob_name,
                    data=data,
                    overwrite=overwrite,
                    metadata={'original_filename': file_path.name, 'upload_time': datetime.now().isoformat()}
                )
                
        except Exception as e:
            logger.error(f"❌ 文件上传失败: {str(e)}")
            return False
    
    def download_blob(self, container_name: str, blob_name: str, local_file_path: Optional[str] = None) -> Union[bytes, bool]:
        """
        下载Blob数据
        
        Args:
            container_name: 容器名称
            blob_name: Blob名称
            local_file_path: 本地保存路径，如果为None则返回bytes数据
            
        Returns:
            Union[bytes, bool]: 如果local_file_path为None返回bytes，否则返回下载是否成功
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )
            
            blob_data = blob_client.download_blob().readall()
            
            if local_file_path:
                with open(local_file_path, 'wb') as file:
                    file.write(blob_data)
                logger.info(f"✅ Blob下载成功: {container_name}/{blob_name} -> {local_file_path}")
                return True
            else:
                logger.info(f"✅ Blob数据读取成功: {container_name}/{blob_name}")
                return blob_data
                
        except Exception as e:
            logger.error(f"❌ Blob下载失败: {str(e)}")
            return False if local_file_path else b''
    
    def list_blobs(self, container_name: str, prefix: Optional[str] = None) -> List[Dict]:
        """
        列出容器中的Blob
        
        Args:
            container_name: 容器名称
            prefix: Blob名称前缀过滤
            
        Returns:
            List[Dict]: Blob信息列表
        """
        try:
            container_client = self.blob_service_client.get_container_client(container_name)
            blobs = []
            
            for blob in container_client.list_blobs(name_starts_with=prefix):
                blobs.append({
                    'name': blob.name,
                    'size': blob.size,
                    'last_modified': blob.last_modified,
                    'content_type': blob.content_settings.content_type if blob.content_settings else None,
                    'metadata': blob.metadata or {}
                })
            
            logger.info(f"列出 {len(blobs)} 个Blob (容器: {container_name})")
            return blobs
            
        except Exception as e:
            logger.error(f"列出Blob失败: {str(e)}")
            return []
    
    def delete_blob(self, container_name: str, blob_name: str) -> bool:
        """
        删除Blob
        
        Args:
            container_name: 容器名称
            blob_name: Blob名称
            
        Returns:
            bool: 删除成功返回True
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )
            blob_client.delete_blob()
            logger.info(f"✅ Blob删除成功: {container_name}/{blob_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Blob删除失败: {str(e)}")
            return False
    
    def get_blob_properties(self, container_name: str, blob_name: str) -> Optional[Dict]:
        """
        获取Blob属性信息
        
        Args:
            container_name: 容器名称
            blob_name: Blob名称
            
        Returns:
            Optional[Dict]: Blob属性字典
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )
            properties = blob_client.get_blob_properties()
            
            return {
                'name': blob_name,
                'size': properties.size,
                'content_type': properties.content_settings.content_type,
                'last_modified': properties.last_modified,
                'etag': properties.etag,
                'metadata': properties.metadata or {},
                'creation_time': properties.creation_time,
                'blob_type': properties.blob_type
            }
            
        except Exception as e:
            logger.error(f"获取Blob属性失败: {str(e)}")
            return None
    
    def generate_sas_url(self, container_name: str, blob_name: str, 
                        expiry_hours: int = 24, permissions: str = 'r') -> Optional[str]:
        """
        生成Blob的SAS URL
        
        Args:
            container_name: 容器名称
            blob_name: Blob名称
            expiry_hours: 过期时间（小时）
            permissions: 权限 ('r'=读, 'w'=写, 'rw'=读写)
            
        Returns:
            Optional[str]: SAS URL
        """
        try:
            from azure.storage.blob import generate_blob_sas, BlobSasPermissions
            from datetime import timezone
            
            # 设置权限
            sas_permissions = BlobSasPermissions(read='r' in permissions, write='w' in permissions)
            
            # 生成SAS token
            sas_token = generate_blob_sas(
                account_name=self.storage_account_name,
                container_name=container_name,
                blob_name=blob_name,
                account_key=None,  # 使用服务主体认证时为None
                permission=sas_permissions,
                expiry=datetime.now(timezone.utc) + timedelta(hours=expiry_hours)
            )
            
            sas_url = f"{self.account_url}/{container_name}/{blob_name}?{sas_token}"
            logger.info(f"✅ SAS URL生成成功: {blob_name}")
            return sas_url
            
        except Exception as e:
            logger.error(f"❌ SAS URL生成失败: {str(e)}")
            return None


def demo_azure_storage_operations():
    """Azure Storage操作演示"""
    # 注意: 需要提供实际的存储账户名
    storage_account_name = "your_storage_account_name"  # 替换为实际的存储账户名
    
    try:
        # 创建客户端
        client = AzureStorageClient(storage_account_name)
        
        # 测试连接
        print("=== 测试Azure Storage连接 ===")
        if not client.test_connection():
            print("连接失败，请检查配置")
            return
        
        # 列出容器
        print("\n=== 列出所有容器 ===")
        containers = client.list_containers()
        for container in containers:
            print(f"容器: {container['name']}, 修改时间: {container['last_modified']}")
        
        # 创建测试容器
        test_container = "test-container"
        print(f"\n=== 创建测试容器: {test_container} ===")
        client.create_container(test_container, metadata={'purpose': 'testing'})
        
        # 上传测试数据
        print(f"\n=== 上传测试数据 ===")
        test_data = "这是一个Azure Storage测试文件\n测试时间: " + datetime.now().isoformat()
        client.upload_blob(test_container, "test.txt", test_data.encode('utf-8'))
        
        # 列出Blob
        print(f"\n=== 列出容器中的Blob ===")
        blobs = client.list_blobs(test_container)
        for blob in blobs:
            print(f"Blob: {blob['name']}, 大小: {blob['size']} bytes")
        
        # 下载数据
        print(f"\n=== 下载Blob数据 ===")
        downloaded_data = client.download_blob(test_container, "test.txt")
        if downloaded_data:
            print(f"下载内容: {downloaded_data.decode('utf-8')}")
        
        print("\n✅ Azure Storage操作演示完成!")
        
    except Exception as e:
        print(f"❌ 演示过程中出错: {str(e)}")


if __name__ == '__main__':
    demo_azure_storage_operations() 