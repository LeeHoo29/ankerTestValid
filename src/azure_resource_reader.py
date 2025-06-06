#!/usr/bin/env python3
"""
Azure Storage 资源读取器
专门用于读取线上Azure Storage中的资源文件
"""
import os
import sys
import gzip
import logging
import json
import argparse
import re
from pathlib import Path
from typing import Dict, List, Optional, Union, BinaryIO
from datetime import datetime
import io

# Azure Storage SDK imports
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.core.exceptions import AzureError, ResourceNotFoundError

# 导入项目配置
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.azure_storage_config import (
    AZURE_STORAGE_CONFIG,
    YIYA0110_STORAGE_CONFIG,
    COLLECTOR0109_STORAGE_CONFIG,
    set_azure_environment_variables,
    get_storage_account_url
)

# 导入数据库连接器
from src.db.connector import DatabaseConnector
from config.db_config import DB_CONFIG

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """
    设置日志配置
    
    Args:
        verbose: 是否启用详细日志输出
    """
    if verbose:
        # 详细模式：显示所有日志，包括Azure SDK的HTTP请求
        logging.getLogger().setLevel(logging.INFO)
        logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.INFO)
        logging.getLogger('azure.identity').setLevel(logging.INFO)
        print("🔧 已启用详细日志模式")
    else:
        # 简化模式：隐藏Azure SDK的详细HTTP日志
        logging.getLogger().setLevel(logging.INFO)
        logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)
        logging.getLogger('azure.identity').setLevel(logging.WARNING)
        # 保持我们自己的日志
        logging.getLogger(__name__).setLevel(logging.INFO)
        logging.getLogger('src.azure_resource_reader_optimizer').setLevel(logging.INFO)
        logging.getLogger('src.db.connector').setLevel(logging.INFO)


class AzureResourceReader:
    """Azure Storage 资源读取器"""
    
    def __init__(self, account_name: str = 'yiya0110', use_default_credential: bool = False):
        """
        初始化Azure资源读取器
        
        Args:
            account_name: Azure存储账户名，支持 'yiya0110' (原始数据) 或 'collector0109' (解析数据)
            use_default_credential: 是否使用默认凭据，False则使用服务主体认证
        """
        self.account_name = account_name
        self.account_url = get_storage_account_url(account_name, 'blob')
        
        # 根据账户名设置存储配置
        if account_name == 'yiya0110':
            self.storage_config = YIYA0110_STORAGE_CONFIG
        elif account_name == 'collector0109':
            self.storage_config = COLLECTOR0109_STORAGE_CONFIG
        else:
            raise ValueError(f"不支持的存储账户: {account_name}。支持的账户: 'yiya0110', 'collector0109'")
        
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
        
        # 初始化Blob服务客户端
        self.blob_service_client = BlobServiceClient(
            account_url=self.account_url,
            credential=self.credential
        )
        
        logger.info(f"Azure资源读取器初始化成功: {account_name} ({self.storage_config['container_name']})")
    
    def read_amazon_listing_job_file(self, job_id: str, filename: str = 'login.gz', 
                                    decompress: bool = True) -> Union[str, bytes, None]:
        """
        读取Amazon Listing Job文件
        
        Args:
            job_id: 任务ID，如 '1925464883027513344'
            filename: 文件名，默认为 'login.gz'，也支持 'normal.gz'
            decompress: 是否自动解压缩，默认为True
            
        Returns:
            Union[str, bytes, None]: 文件内容，如果解压缩则返回str，否则返回bytes
        """
        return self.read_task_file('AmazonListingJob', job_id, filename, decompress)
    
    def read_task_file(self, task_type: str, job_id: str, filename: str, 
                      decompress: bool = True) -> Union[str, bytes, None]:
        """
        读取任务文件（通用方法）
        
        Args:
            task_type: 任务类型，如 'AmazonListingJob'
            job_id: 任务ID，如 '1925464883027513344'
            filename: 文件名，如 'login.gz' 或 'normal.gz'
            decompress: 是否自动解压缩，默认为True
            
        Returns:
            Union[str, bytes, None]: 文件内容
        """
        container_name = self.storage_config['container_name']
        blob_path = f"{self.storage_config['blob_base_path']}/{task_type}/{job_id}/{filename}"
        
        return self.read_blob_content(container_name, blob_path, decompress=decompress)
    
    def read_amazon_listing_job_both_files(self, job_id: str, 
                                         decompress: bool = True) -> Dict[str, Union[str, bytes, None]]:
        """
        读取Amazon Listing Job的两个默认文件：login.gz 和 normal.gz
        
        Args:
            job_id: 任务ID，如 '1925464883027513344'
            decompress: 是否自动解压缩，默认为True
            
        Returns:
            Dict[str, Union[str, bytes, None]]: 包含两个文件内容的字典
        """
        result = {}
        
        # 读取login.gz
        logger.info(f"正在读取 login.gz 文件...")
        result['login'] = self.read_amazon_listing_job_file(job_id, 'login.gz', decompress)
        
        # 读取normal.gz
        logger.info(f"正在读取 normal.gz 文件...")
        result['normal'] = self.read_amazon_listing_job_file(job_id, 'normal.gz', decompress)
        
        return result
    
    def read_blob_content(self, container_name: str, blob_path: str, 
                         decompress: bool = True) -> Union[str, bytes, None]:
        """
        读取Blob内容
        
        Args:
            container_name: 容器名称
            blob_path: Blob路径
            decompress: 是否自动解压缩.gz文件，默认为True
            
        Returns:
            Union[str, bytes, None]: 文件内容
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_path
            )
            
            logger.info(f"正在读取 Blob: {container_name}/{blob_path}")
            
            # 下载Blob数据
            blob_data = blob_client.download_blob().readall()
            
            # 检查是否需要解压缩
            if decompress and blob_path.endswith('.gz'):
                logger.info("检测到.gz文件，正在解压缩...")
                try:
                    # 使用gzip解压缩
                    decompressed_data = gzip.decompress(blob_data)
                    # 尝试解码为UTF-8字符串
                    try:
                        content = decompressed_data.decode('utf-8')
                        logger.info(f"✅ 成功读取并解压缩文件，内容长度: {len(content)} 字符")
                        return content
                    except UnicodeDecodeError:
                        logger.warning("无法解码为UTF-8，返回原始字节数据")
                        logger.info(f"✅ 成功读取并解压缩文件，数据长度: {len(decompressed_data)} 字节")
                        return decompressed_data
                        
                except gzip.BadGzipFile:
                    logger.warning("文件不是有效的gzip格式，返回原始数据")
                    logger.info(f"✅ 成功读取文件，数据长度: {len(blob_data)} 字节")
                    return blob_data
            else:
                logger.info(f"✅ 成功读取文件，数据长度: {len(blob_data)} 字节")
                return blob_data
                
        except ResourceNotFoundError:
            logger.error(f"❌ 文件不存在: {container_name}/{blob_path}")
            return None
        except Exception as e:
            logger.error(f"❌ 读取文件失败: {str(e)}")
            return None
    
    def save_blob_to_file(self, container_name: str, blob_path: str, 
                         local_file_path: str, decompress: bool = True) -> bool:
        """
        下载Blob并保存到本地文件
        
        Args:
            container_name: 容器名称
            blob_path: Blob路径
            local_file_path: 本地文件保存路径
            decompress: 是否自动解压缩.gz文件，默认为True
            
        Returns:
            bool: 下载成功返回True
        """
        content = self.read_blob_content(container_name, blob_path, decompress=decompress)
        
        if content is None:
            return False
        
        try:
            # 确保目录存在
            local_path = Path(local_file_path)
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入文件
            if isinstance(content, str):
                with open(local_file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            else:
                with open(local_file_path, 'wb') as f:
                    f.write(content)
            
            logger.info(f"✅ 文件保存成功: {local_file_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 保存文件失败: {str(e)}")
            return False
    
    def list_amazon_listing_jobs(self, limit: int = 100) -> List[Dict]:
        """
        列出Amazon Listing Job目录
        
        Args:
            limit: 限制返回的数量，默认100
            
        Returns:
            List[Dict]: 任务信息列表
        """
        container_name = self.storage_config['container_name']
        prefix = f"{self.storage_config['blob_base_path']}/AmazonListingJob/"
        
        return self.list_blobs_with_prefix(container_name, prefix, limit)
    
    def list_task_jobs(self, task_type: str, limit: int = 100) -> List[Dict]:
        """
        列出指定任务类型的所有任务
        
        Args:
            task_type: 任务类型，如 'AmazonListingJob'
            limit: 限制返回的数量，默认100
            
        Returns:
            List[Dict]: 任务信息列表
        """
        container_name = self.storage_config['container_name']
        prefix = f"{self.storage_config['blob_base_path']}/{task_type}/"
        
        return self.list_blobs_with_prefix(container_name, prefix, limit)
    
    def list_blobs_with_prefix(self, container_name: str, prefix: str, 
                              limit: int = 100) -> List[Dict]:
        """
        列出指定前缀的Blob
        
        Args:
            container_name: 容器名称
            prefix: Blob路径前缀
            limit: 限制返回的数量
            
        Returns:
            List[Dict]: Blob信息列表
        """
        try:
            container_client = self.blob_service_client.get_container_client(container_name)
            blobs = []
            
            count = 0
            for blob in container_client.list_blobs(name_starts_with=prefix):
                if count >= limit:
                    break
                    
                blobs.append({
                    'name': blob.name,
                    'size': blob.size,
                    'last_modified': blob.last_modified,
                    'content_type': blob.content_settings.content_type if blob.content_settings else None,
                    'path_parts': blob.name.split('/'),
                    'job_id': self._extract_job_id_from_path(blob.name)
                })
                count += 1
            
            logger.info(f"列出 {len(blobs)} 个Blob (前缀: {prefix})")
            return blobs
            
        except Exception as e:
            logger.error(f"列出Blob失败: {str(e)}")
            return []
    
    def _extract_job_id_from_path(self, blob_path: str) -> Optional[str]:
        """
        从Blob路径中提取Job ID
        
        Args:
            blob_path: Blob路径，如 "compress/AmazonListingJob/1925464883027513344/login.gz"
            
        Returns:
            Optional[str]: Job ID
        """
        try:
            parts = blob_path.split('/')
            # 新路径结构: compress/TaskType/JobID/filename
            if len(parts) >= 4 and parts[0] == 'compress':
                return parts[2]  # JobID在第3个位置（索引2）
        except:
            pass
        return None
    
    def get_blob_info(self, container_name: str, blob_path: str) -> Optional[Dict]:
        """
        获取Blob详细信息
        
        Args:
            container_name: 容器名称
            blob_path: Blob路径
            
        Returns:
            Optional[Dict]: Blob信息字典
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_path
            )
            
            properties = blob_client.get_blob_properties()
            
            return {
                'name': blob_path,
                'size': properties.size,
                'size_mb': round(properties.size / (1024 * 1024), 2),
                'content_type': properties.content_settings.content_type,
                'last_modified': properties.last_modified,
                'etag': properties.etag,
                'metadata': properties.metadata or {},
                'creation_time': properties.creation_time,
                'blob_type': properties.blob_type,
                'url': f"{self.account_url}/{container_name}/{blob_path}"
            }
            
        except Exception as e:
            logger.error(f"获取Blob信息失败: {str(e)}")
            return None
    
    def read_parse_file(self, task_type: str, task_id: str, filename: str = None, 
                       decompress: bool = True) -> Union[str, bytes, None]:
        """
        读取解析文件（collector0109账户）
        
        Args:
            task_type: 任务类型（如: AmazonListingJob）
            task_id: 任务ID（如: 1910599147004108800）
            filename: 文件名，如果不指定则尝试查找JSON文件
            decompress: 是否自动解压缩，默认为True
            
        Returns:
            Union[str, bytes, None]: 文件内容
        """
        if self.account_name != 'collector0109':
            logger.error("读取解析文件需要使用collector0109存储账户")
            return None
        
        container_name = self.storage_config['container_name']
        
        # 路径结构：parse/{task_type}/{task_id}/*
        blob_prefix = f"{self.storage_config['blob_base_path']}/{task_type}/{task_id}/"
        
        if filename:
            # 指定文件名
            blob_path = f"{blob_prefix}{filename}"
            return self.read_blob_content(container_name, blob_path, decompress=decompress)
        else:
            # 自动查找JSON文件
            return self._auto_find_parse_file(container_name, blob_prefix, decompress)
    
    def _auto_find_parse_file(self, container_name: str, blob_prefix: str, 
                             decompress: bool = True) -> Union[str, bytes, None]:
        """
        自动查找解析文件（优先JSON文件）
        
        Args:
            container_name: 容器名
            blob_prefix: Blob路径前缀
            decompress: 是否解压缩
            
        Returns:
            Union[str, bytes, None]: 文件内容
        """
        try:
            container_client = self.blob_service_client.get_container_client(container_name)
            
            # 查找所有文件
            blobs = list(container_client.list_blobs(name_starts_with=blob_prefix))
            
            if not blobs:
                logger.warning(f"未找到任何文件，路径前缀: {blob_prefix}")
                return None
            
            # 优先级：.json > .json.gz > 其他
            json_files = [b for b in blobs if b.name.endswith('.json')]
            json_gz_files = [b for b in blobs if b.name.endswith('.json.gz')]
            other_files = [b for b in blobs if not (b.name.endswith('.json') or b.name.endswith('.json.gz'))]
            
            target_blob = None
            if json_files:
                target_blob = json_files[0]
                logger.info(f"找到JSON文件: {target_blob.name}")
            elif json_gz_files:
                target_blob = json_gz_files[0]
                logger.info(f"找到压缩JSON文件: {target_blob.name}")
            elif other_files:
                target_blob = other_files[0]
                logger.info(f"找到其他文件: {target_blob.name}")
            
            if target_blob:
                return self.read_blob_content(container_name, target_blob.name, decompress=decompress)
            else:
                logger.warning("未找到合适的解析文件")
                return None
                
        except Exception as e:
            logger.error(f"自动查找解析文件失败: {str(e)}")
            return None
    
    def list_parse_files(self, task_type: str, task_id: str) -> List[Dict]:
        """
        列出解析文件目录中的所有文件
        
        Args:
            task_type: 任务类型（如: AmazonListingJob）
            task_id: 任务ID
            
        Returns:
            List[Dict]: 文件信息列表
        """
        if self.account_name != 'collector0109':
            logger.error("列出解析文件需要使用collector0109存储账户")
            return []
        
        container_name = self.storage_config['container_name']
        prefix = f"{self.storage_config['blob_base_path']}/{task_type}/{task_id}/"
        
        return self.list_blobs_with_prefix(container_name, prefix, limit=100)

    def read_task_file_with_parse(self, task_type: str, task_id: str, filename: str, 
                                 decompress: bool = True) -> Dict[str, Union[str, bytes, None]]:
        """
        同时读取原始任务文件和解析文件
        
        Args:
            task_type: 任务类型，如 'AmazonListingJob'
            task_id: 任务ID，如 '1925464883027513344'
            filename: 原始文件名，如 'login.gz' 或 'normal.gz'
            decompress: 是否自动解压缩，默认为True
            
        Returns:
            Dict[str, Union[str, bytes, None]]: 包含原始文件和解析文件内容的字典
        """
        result = {}
        
        # 读取原始文件（yiya0110）
        if self.account_name == 'yiya0110':
            logger.info(f"正在读取原始文件: {filename}")
            result['original'] = self.read_task_file(task_type, task_id, filename, decompress)
            
            # 创建collector0109读取器来读取解析文件
            parse_reader = AzureResourceReader('collector0109')
            logger.info(f"正在读取解析文件...")
            result['parse'] = parse_reader.read_parse_file(task_type, task_id, None, decompress)
            
        else:
            logger.warning("此方法需要使用yiya0110账户作为主读取器")
            result['original'] = None
            result['parse'] = None
            
        return result

    def fetch_and_save_parse_files(self, task_type: str, task_id: str, 
                                  save_dir: str = 'data/output', 
                                  decompress: bool = True) -> Dict[str, any]:
        """
        从collector0109获取解析文件并保存到指定文件夹
        根据测试结果优化，仅使用正确的路径：parse/{task_type}/{task_id}/
        
        Args:
            task_type: 任务类型（如: AmazonReviewStarJob）
            task_id: 任务ID（如: 1887037115222994944）
            save_dir: 保存目录，默认: data/output
            decompress: 是否自动解压缩，默认为True
            
        Returns:
            Dict: 包含操作结果的字典
        """
        if self.account_name != 'collector0109':
            logger.error("获取解析文件需要使用collector0109存储账户")
            return {
                'success': False,
                'error': '需要使用collector0109存储账户',
                'files_downloaded': [],
                'save_path': None
            }
        
        logger.info(f"🔍 正在从collector0109获取解析文件")
        logger.info(f"📋 任务类型: {task_type}")
        logger.info(f"📋 任务ID: {task_id}")
        
        container_name = self.storage_config['container_name']
        # 根据测试结果，使用正确的路径结构：parse/{task_type}/{task_id}/
        blob_prefix = f"{self.storage_config['blob_base_path']}/{task_type}/{task_id}/"
        
        logger.info(f"📁 搜索路径: {blob_prefix}")
        
        try:
            container_client = self.blob_service_client.get_container_client(container_name)
            
            # 查找所有文件
            blobs = list(container_client.list_blobs(name_starts_with=blob_prefix))
            
            if not blobs:
                logger.warning(f"❌ 未找到任何解析文件，路径: {blob_prefix}")
                return {
                    'success': False,
                    'error': f'未找到解析文件，路径: {blob_prefix}',
                    'files_downloaded': [],
                    'save_path': None
                }
            
            logger.info(f"✅ 找到 {len(blobs)} 个解析文件")
            
            # 创建保存目录
            save_path = Path(save_dir) / 'parse' / task_type / task_id
            save_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"📂 保存目录: {save_path}")
            
            downloaded_files = []
            
            # 优先级处理：JSON > JSON.GZ > 其他
            json_files = [b for b in blobs if b.name.endswith('.json')]
            json_gz_files = [b for b in blobs if b.name.endswith('.json.gz')]
            other_files = [b for b in blobs if not (b.name.endswith('.json') or b.name.endswith('.json.gz'))]
            
            # 按优先级处理文件
            files_to_process = []
            if json_files:
                files_to_process.extend(json_files)
                logger.info(f"📄 找到 {len(json_files)} 个JSON文件")
            if json_gz_files:
                files_to_process.extend(json_gz_files)
                logger.info(f"📄 找到 {len(json_gz_files)} 个压缩JSON文件")
            if other_files:
                files_to_process.extend(other_files)
                logger.info(f"📄 找到 {len(other_files)} 个其他文件")
            
            # 下载所有文件
            for blob in files_to_process:
                try:
                    logger.info(f"📥 正在下载: {blob.name}")
                    
                    # 读取文件内容
                    content = self.read_blob_content(container_name, blob.name, decompress=decompress)
                    
                    if content is not None:
                        # 生成保存文件名，确保JSON文件保持.json扩展名
                        file_name = Path(blob.name).name
                        if decompress and blob.name.endswith('.gz'):
                            # 如果解压缩了，移除.gz扩展名
                            file_name = file_name.replace('.gz', '')
                        
                        # 确保JSON文件始终保持.json扩展名
                        if file_name.endswith('.json') or blob.name.endswith('.json') or blob.name.endswith('.json.gz'):
                            if not file_name.endswith('.json'):
                                file_name = file_name.rsplit('.', 1)[0] + '.json'
                        
                        local_file_path = save_path / file_name
                        
                        # 保存文件
                        success = self._save_content_to_file(content, str(local_file_path))
                        
                        if success:
                            downloaded_files.append({
                                'original_name': blob.name,
                                'saved_name': file_name,
                                'local_path': str(local_file_path),
                                'size': blob.size,
                                'content_length': len(content) if isinstance(content, str) else len(content)
                            })
                            logger.info(f"✅ 已保存: {local_file_path}")
                            
                            # 如果是JSON文件，显示预览
                            if file_name.endswith('.json') and isinstance(content, str):
                                try:
                                    import json as json_module
                                    parsed_data = json_module.loads(content)
                                    logger.info(f"📋 JSON解析成功，类型: {type(parsed_data)}")
                                    if isinstance(parsed_data, dict):
                                        logger.info(f"🔑 JSON键: {list(parsed_data.keys())[:5]}...")
                                    elif isinstance(parsed_data, list):
                                        logger.info(f"📊 JSON数组长度: {len(parsed_data)}")
                                except:
                                    logger.info(f"📄 JSON文件已保存，但无法解析内容")
                        else:
                            logger.error(f"❌ 保存失败: {blob.name}")
                    else:
                        logger.error(f"❌ 读取失败: {blob.name}")
                        
                except Exception as e:
                    logger.error(f"❌ 处理文件失败 {blob.name}: {str(e)}")
            
            # 返回结果
            result = {
                'success': len(downloaded_files) > 0,
                'files_downloaded': downloaded_files,
                'save_path': str(save_path),
                'total_files_found': len(blobs),
                'total_files_downloaded': len(downloaded_files)
            }
            
            if downloaded_files:
                logger.info(f"✅ 成功下载 {len(downloaded_files)} 个解析文件到: {save_path}")
            else:
                logger.warning(f"⚠️  未能下载任何文件")
                result['error'] = '未能下载任何文件'
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 获取解析文件失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'files_downloaded': [],
                'save_path': None
            }
    
    def _save_content_to_file(self, content: Union[str, bytes], file_path: str) -> bool:
        """
        保存内容到文件（内部方法）
        
        Args:
            content: 文件内容
            file_path: 文件路径
            
        Returns:
            bool: 保存成功返回True
        """
        try:
            # 确保目录存在
            local_path = Path(file_path)
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入文件
            if isinstance(content, str):
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            else:
                with open(file_path, 'wb') as f:
                    f.write(content)
            
            return True
            
        except Exception as e:
            logger.error(f"保存文件失败: {str(e)}")
            return False


def main():
    """主函数：处理命令行参数并执行相应操作"""
    parser = argparse.ArgumentParser(
        description='Azure Storage 资源读取器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 读取原始数据文件（yiya0110账户）
  python3 src/azure_resource_reader.py AmazonListingJob 1925464883027513344 html
  python3 src/azure_resource_reader.py AmazonReviewStarJob 2796867471 html
  
  # 🆕 直接获取解析文件（优化版本，推荐）
  python3 src/azure_resource_reader.py AmazonReviewStarJob 1887037115222994944 --fetch-parse
  python3 src/azure_resource_reader.py AmazonListingJob 1925464883027513344 --fetch-parse
  
  # 🆕 同时读取原始数据和解析数据
  python3 src/azure_resource_reader.py AmazonReviewStarJob 2796867471 html --with-parse
  python3 src/azure_resource_reader.py AmazonListingJob 1925464883027513344 json --with-parse
  
  # 读取解析文件（传统方式）
  python3 src/azure_resource_reader.py --account collector0109 --parse-mode SL2796867471 1910599147004108800 json
  python3 src/azure_resource_reader.py --account collector0109 --parse-mode SL2796867471 1910599147004108800 json --files result.json
  
  # 查看当前的任务映射
  python3 src/azure_resource_reader.py --show-mapping
  
  # 禁用映射文件生成
  python3 src/azure_resource_reader.py AmazonListingJob 2796867471 html --no-mapping
  
  # 启用详细日志输出（包括HTTP请求详情）
  python3 src/azure_resource_reader.py AmazonListingJob 2834468425 html --with-parse --verbose
  
映射功能说明:
  - 每次成功下载文件后，会在 data/output/task_mapping.json 中记录映射关系
  - 映射格式: 输入参数 -> 实际下载路径
  - 例如: 2796867471 -> ./AmazonReviewStarJob/1910599147004108800/*
  - 🆕 --with-parse模式: 原始文件和解析文件保存在同一目录，使用统一映射
  - 🆕 --fetch-parse模式: 仅解析文件，单独映射到 ./parse/{任务类型}/{任务ID}/
  - 解析模式: SL2796867471 -> ./parse/SL2796867471/1910599147004108800/*
        """
    )
    
    parser.add_argument('task_type_or_job_id', 
                       nargs='?',
                       help='任务类型（如: AmazonListingJob）或解析模式下的job_id（如: SL2796867471）')
    parser.add_argument('task_id_or_task_id', 
                       nargs='?',
                       help='任务ID（长数字串）或解析模式下的task_id')
    parser.add_argument('output_type', 
                       nargs='?',
                       choices=['html', 'txt', 'json', 'raw'],
                       help='输出文件类型: html(自动解压), txt(自动解压), json(自动解压), raw(不解压)')
    
    parser.add_argument('--account', '-a',
                       choices=['yiya0110', 'collector0109'],
                       default='yiya0110',
                       help='Azure存储账户: yiya0110(原始数据), collector0109(解析数据)')
    parser.add_argument('--parse-mode', '-p',
                       action='store_true',
                       help='解析文件模式（需要配合--account collector0109使用）')
    parser.add_argument('--with-parse', 
                       action='store_true',
                       help='同时获取原始数据和解析数据（自动使用yiya0110读取原始数据，collector0109读取解析数据）')
    parser.add_argument('--fetch-parse', 
                       action='store_true',
                       help='🆕 直接从collector0109获取解析文件（优化路径，基于测试结果）')
    parser.add_argument('--files', '-f',
                       nargs='+',
                       default=None,
                       help='要读取的文件列表，解析模式下默认自动查找JSON文件')
    parser.add_argument('--save-dir', '-s',
                       default='data/output',
                       help='保存目录，默认: data/output')
    parser.add_argument('--info-only', '-i',
                       action='store_true',
                       help='仅显示文件信息，不下载内容')
    parser.add_argument('--list-jobs', '-l',
                       action='store_true',
                       help='列出指定任务类型的所有任务')
    parser.add_argument('--no-mapping', 
                       action='store_true',
                       help='不生成任务映射文件')
    parser.add_argument('--show-mapping', 
                       action='store_true',
                       help='显示当前的任务映射文件内容')
    parser.add_argument('--verbose', '-v',
                       action='store_true',
                       help='启用详细日志输出（包括HTTP请求详情）')
    
    args = parser.parse_args()
    
    # 根据verbose参数设置日志级别
    setup_logging(verbose=args.verbose)
    
    # 如果只是显示映射文件内容
    if args.show_mapping:
        show_task_mapping(args.save_dir)
        return
    
    # 🆕 处理 --fetch-parse 模式
    if args.fetch_parse:
        if not args.task_type_or_job_id or not args.task_id_or_task_id:
            parser.error("--fetch-parse 模式需要提供 task_type 和 task_id 参数")
        
        task_type = args.task_type_or_job_id
        task_id = args.task_id_or_task_id
        
        print(f"🔍 Azure Storage 解析文件获取器 (优化版本)")
        print(f"📋 任务类型: {task_type}")
        print(f"📋 任务ID: {task_id}")
        print(f"📁 搜索路径: collector0109/parse/{task_type}/{task_id}/")
        print("=" * 80)
        
        # 创建collector0109读取器
        reader = AzureResourceReader('collector0109')
        
        # 使用优化的方法获取解析文件
        result = reader.fetch_and_save_parse_files(
            task_type=task_type,
            task_id=task_id,
            save_dir=args.save_dir,
            decompress=True
        )
        
        # 显示结果
        if result['success']:
            print(f"\n✅ 解析文件获取成功!")
            print(f"📂 保存路径: {result['save_path']}")
            print(f"📊 找到文件数: {result['total_files_found']}")
            print(f"📥 下载文件数: {result['total_files_downloaded']}")
            
            if result['files_downloaded']:
                print(f"\n📄 已下载的文件:")
                for file_info in result['files_downloaded']:
                    print(f"  ✅ {file_info['saved_name']}")
                    print(f"     📊 大小: {file_info['size']} 字节")
                    print(f"     📁 路径: {file_info['local_path']}")
                    print()
        else:
            print(f"\n❌ 解析文件获取失败!")
            print(f"🔍 错误信息: {result.get('error', '未知错误')}")
        
        return
    
    # 检查必需参数
    if not args.task_type_or_job_id or not args.task_id_or_task_id or not args.output_type:
        parser.error("当不使用 --show-mapping 时，需要提供 task_type_or_job_id, task_id_or_task_id 和 output_type 参数")
    
    # 保存原始输入参数用于映射
    original_input = args.task_id_or_task_id
    
    # 检查解析模式的参数一致性
    if args.parse_mode and args.account != 'collector0109':
        parser.error("解析模式必须使用 --account collector0109")
    
    if args.account == 'collector0109' and not args.parse_mode:
        print("⚠️  使用collector0109账户但未启用解析模式，将自动启用解析模式")
        args.parse_mode = True
    
    # 检查--with-parse参数
    if args.with_parse:
        if args.account != 'yiya0110':
            print("⚠️  --with-parse 模式将自动使用yiya0110作为主账户")
            args.account = 'yiya0110'
        
        # 处理同时获取原始数据和解析数据的模式
        handle_with_parse_mode(args)
        return
    
    # 解析模式特殊处理
    if args.parse_mode:
        print(f"🔍 Azure Storage 资源读取器 (解析模式)")
        print(f"📋 Job ID: {args.task_type_or_job_id}")
        print(f"📋 Task ID: {args.task_id_or_task_id}")
        
        job_id = args.task_type_or_job_id
        task_id = args.task_id_or_task_id
        original_input = f"{job_id}:{task_id}"
        
        print(f"📁 解析数据路径: collector0109/parse/{job_id}/{task_id}/")
        print("=" * 80)
        
        # 创建资源读取器
        reader = AzureResourceReader(args.account)
        
        # 处理解析文件
        handle_parse_mode(reader, job_id, task_id, args, original_input)
        return
    
    # 原始模式处理
    # 第一步：验证和转换任务ID
    print(f"🔍 Azure Storage 资源读取器")
    print(f"📋 任务类型: {args.task_type_or_job_id}")
    print(f"📋 输入参数: {args.task_id_or_task_id}")
    
    # 检查输入是否为有效的任务ID
    if is_valid_task_id(args.task_id_or_task_id):
        # 直接使用作为任务ID
        task_id = args.task_id_or_task_id
        print(f"✅ 检测到有效的任务ID: {task_id}")
    else:
        # 需要转换为任务ID
        job_id = args.task_id_or_task_id
        
        # 如果是纯数字，添加SL前缀
        if job_id.isdigit():
            job_id = f"SL{job_id}"
            print(f"🔄 添加SL前缀: {job_id}")
        
        print(f"🔍 通过数据库查询转换 job_id: {job_id}")
        task_id = convert_job_id_to_task_id(job_id)
        
        if task_id is None:
            print(f"❌ 无法找到对应的任务ID，请检查 job_id: {job_id}")
            return
        
        print(f"✅ 查询成功，获得任务ID: {task_id}")
    
    print(f"📁 路径结构: {args.account if hasattr(args, 'account') else 'yiya0110'}/{args.task_type_or_job_id}/{task_id}/")
    print("=" * 80)
    
    # 第二步：确定要处理的文件列表
    if args.files is None:
        # 根据任务类型自动选择默认文件
        files_to_process = get_default_files_for_task_type(args.task_type_or_job_id)
        print(f"📄 根据任务类型自动选择文件: {', '.join(files_to_process)}")
    else:
        files_to_process = args.files
        print(f"📄 用户指定文件: {', '.join(files_to_process)}")
    
    # 创建资源读取器
    reader = AzureResourceReader(args.account)
    
    # 如果只是列出任务
    if args.list_jobs:
        print(f"📋 列出 {args.task_type_or_job_id} 任务 (前10个):")
        jobs = reader.list_task_jobs(args.task_type_or_job_id, limit=10)
        
        if jobs:
            print(f"✅ 找到 {len(jobs)} 个任务:")
            for job in jobs:
                job_id_extracted = job.get('job_id', 'Unknown')
                print(f"  📋 任务ID: {job_id_extracted}")
                print(f"     📄 文件: {job['name']}")
                print(f"     📊 大小: {job['size']} 字节")
                print(f"     📅 修改: {job['last_modified']}")
                print()
        else:
            print("❌ 未找到任务")
        return
    
    # 确定是否需要解压缩
    decompress = args.output_type in ['html', 'txt', 'json']
    
    # 用于记录是否有文件成功下载
    successfully_downloaded_files = []
    
    # 处理每个文件
    for filename in files_to_process:
        print(f"\n📄 处理文件: {filename}")
        print("-" * 60)
        
        # 仅显示信息
        if args.info_only:
            blob_path = f"compress/{args.task_type_or_job_id}/{task_id}/{filename}"
            blob_info = reader.get_blob_info('download', blob_path)
            
            if blob_info:
                print(f"✅ 文件信息:")
                print(f"  📊 大小: {blob_info['size_mb']} MB")
                print(f"  📅 修改时间: {blob_info['last_modified']}")
                print(f"  🔗 URL: {blob_info['url']}")
            else:
                print("❌ 文件不存在或获取信息失败")
            continue
        
        # 读取文件内容
        content = reader.read_task_file(args.task_type_or_job_id, task_id, filename, decompress)
        
        if content is None:
            print("❌ 读取失败或文件不存在")
            continue
        
        print("✅ 读取成功!")
        
        # 显示内容信息
        if isinstance(content, str):
            print(f"📝 内容长度: {len(content)} 字符")
            
            # 如果是JSON类型，尝试解析
            if args.output_type == 'json':
                try:
                    if content.strip().startswith('{') or content.strip().startswith('['):
                        parsed_data = json.loads(content)
                        print(f"📋 JSON解析成功，类型: {type(parsed_data)}")
                        if isinstance(parsed_data, dict):
                            print(f"🔑 JSON键: {list(parsed_data.keys())}")
                        elif isinstance(parsed_data, list):
                            print(f"📊 JSON数组长度: {len(parsed_data)}")
                except json.JSONDecodeError:
                    print("⚠️  内容不是有效的JSON格式")
            
            # 显示预览
            print(f"🔍 内容预览 (前200字符):")
            print(content[:200] + "..." if len(content) > 200 else content)
            
        else:
            print(f"📊 数据长度: {len(content)} 字节")
        
        # 保存到本地文件
        actual_filename = filename if filename else "auto_found"
        
        # 检测内容是否为JSON格式，如果是则强制使用json扩展名
        output_type_to_use = args.output_type
        if isinstance(content, str) and (content.strip().startswith('{') or content.strip().startswith('[')):
            try:
                json.loads(content)  # 验证是否为有效JSON
                output_type_to_use = "json"  # 强制使用json格式
                print("🔍 检测到JSON内容，将保存为.json文件")
            except json.JSONDecodeError:
                pass  # 不是有效JSON，保持原输出类型
        
        save_filename = _generate_save_filename(actual_filename, task_id, output_type_to_use)
        local_path = f"{args.save_dir}/parse/{job_id}/{task_id}/{save_filename}"
        
        success = _save_content_to_file(content, local_path)
        if success:
            print(f"💾 文件已保存到: {local_path}")
            successfully_downloaded_files.append(filename)
        else:
            print("❌ 保存失败")
    
    # 第三步：更新任务映射文件（如果有文件成功下载且未禁用映射）
    if successfully_downloaded_files and not args.info_only and not args.no_mapping:
        print("\n" + "=" * 80)
        print("第三步：更新任务映射文件")
        print("=" * 80)
        
        # 显示映射信息
        print_task_mapping_info(original_input, args.task_type_or_job_id, task_id, args.save_dir)
        
        # 更新映射
        mapping_success = update_task_mapping(original_input, args.task_type_or_job_id, task_id, args.save_dir)
        
        if mapping_success:
            print(f"✅ 成功下载 {len(successfully_downloaded_files)} 个文件并更新映射")
            print(f"📄 已下载文件: {', '.join(successfully_downloaded_files)}")
        else:
            print("⚠️  文件下载成功但映射更新失败")
    
    elif args.info_only:
        print(f"\n📋 信息查看模式，未下载文件")
    elif args.no_mapping:
        print(f"\n📋 已禁用映射文件生成")
    elif not successfully_downloaded_files:
        print(f"\n⚠️  没有文件成功下载，未更新映射")


def _generate_save_filename(original_filename: str, task_id: str, output_type: str) -> str:
    """
    生成保存文件名（不包含路径，只是文件名）
    
    Args:
        original_filename: 原始文件名，如 'login.gz'
        task_id: 任务ID
        output_type: 输出类型
        
    Returns:
        str: 生成的文件名
    """
    base_name = original_filename.replace('.gz', '').replace('.', '_')
    
    if output_type == 'raw':
        return original_filename
    else:
        extension = output_type if output_type in ['html', 'txt', 'json'] else 'txt'
        return f"{base_name}.{extension}"


def _save_content_to_file(content: Union[str, bytes], file_path: str) -> bool:
    """
    保存内容到文件
    
    Args:
        content: 文件内容
        file_path: 文件路径
        
    Returns:
        bool: 保存成功返回True
    """
    try:
        # 确保目录存在
        local_path = Path(file_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入文件
        if isinstance(content, str):
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        else:
            with open(file_path, 'wb') as f:
                f.write(content)
        
        return True
        
    except Exception as e:
        logger.error(f"保存文件失败: {str(e)}")
        return False


def demo_read_amazon_listing_job():
    """演示读取Amazon Listing Job文件（保留用于测试）"""
    # 创建资源读取器
    reader = AzureResourceReader('yiya0110')
    
    # 指定要读取的任务ID
    job_id = '1925464883027513344'
    
    print(f"🔍 正在读取Amazon Listing Job文件...")
    print(f"📋 任务类型: AmazonListingJob")
    print(f"📋 任务ID: {job_id}")
    print(f"📁 路径结构: yiya0110/download/compress/AmazonListingJob/{job_id}/")
    print("=" * 80)
    
    # 方法1：读取默认的两个文件
    print("方法1：读取两个默认文件 (login.gz + normal.gz)")
    both_files = reader.read_amazon_listing_job_both_files(job_id)
    
    for file_type, content in both_files.items():
        print(f"\n📄 {file_type}.gz 文件:")
        if content:
            print(f"✅ 读取成功!")
            if isinstance(content, str):
                print(f"📝 内容长度: {len(content)} 字符")
                print(f"🔍 内容预览 (前200字符):")
                print(content[:200] + "..." if len(content) > 200 else content)
            else:
                print(f"📊 数据长度: {len(content)} 字节")
        else:
            print("❌ 读取失败或文件不存在")
    
    print("\n" + "=" * 80)
    
    # 方法2：使用通用方法读取指定文件
    print("方法2：使用通用方法读取login.gz")
    login_content = reader.read_task_file('AmazonListingJob', job_id, 'login.gz')
    
    if login_content:
        print("✅ 通用方法读取成功!")
        if isinstance(login_content, str):
            print(f"📝 内容长度: {len(login_content)} 字符")
        else:
            print(f"📊 数据长度: {len(login_content)} 字节")
    else:
        print("❌ 通用方法读取失败")
    
    print("\n" + "=" * 80)
    
    # 方法3：获取文件信息
    print("方法3：获取文件详细信息")
    for filename in ['login.gz', 'normal.gz']:
        blob_path = f"compress/AmazonListingJob/{job_id}/{filename}"
        blob_info = reader.get_blob_info('download', blob_path)
        
        print(f"\n📄 {filename}:")
        if blob_info:
            print(f"  📊 大小: {blob_info['size_mb']} MB")
            print(f"  📅 修改时间: {blob_info['last_modified']}")
            print(f"  🔗 URL: {blob_info['url']}")
        else:
            print("  ❌ 文件不存在或获取信息失败")
    
    print("\n" + "=" * 80)
    
    # 方法4：保存文件到本地
    print("方法4：下载并保存到本地")
    for filename in ['login.gz', 'normal.gz']:
        blob_path = f"compress/AmazonListingJob/{job_id}/{filename}"
        local_filename = filename.replace('.gz', '.txt')
        local_path = f"data/output/amazon_listing_{job_id}_{local_filename}"
        
        success = reader.save_blob_to_file('download', blob_path, local_path)
        if success:
            print(f"✅ {filename} 已保存到: {local_path}")
        else:
            print(f"❌ {filename} 保存失败")
    
    print("\n" + "=" * 80)
    
    # 方法5：列出Amazon Listing Jobs
    print("方法5：列出最近的Amazon Listing Jobs (前5个)")
    jobs = reader.list_amazon_listing_jobs(limit=5)
    
    if jobs:
        print(f"✅ 找到 {len(jobs)} 个任务:")
        for job in jobs:
            job_id_extracted = job.get('job_id', 'Unknown')
            print(f"  📋 任务ID: {job_id_extracted}")
            print(f"     📄 文件: {job['name']}")
            print(f"     📊 大小: {job['size']} 字节")
            print(f"     📅 修改: {job['last_modified']}")
            print()
    else:
        print("❌ 未找到任务或列取失败")


def is_valid_task_id(task_id: str) -> bool:
    """
    检查是否为有效的任务ID格式（长数字串）
    
    Args:
        task_id: 要检查的任务ID
        
    Returns:
        bool: 如果是有效的任务ID返回True
    """
    # 检查是否为18-20位的纯数字
    return re.match(r'^\d{18,20}$', task_id) is not None


def convert_job_id_to_task_id(job_id: str) -> Optional[str]:
    """
    通过数据库查询将 job_id 转换为 task_id
    
    Args:
        job_id: 请求序列号，如 'SL2796867471'
        
    Returns:
        Optional[str]: 找到的 task_id (ext_ssn)，未找到返回None
    """
    # 创建数据库连接
    db_config = DB_CONFIG.copy()
    db_config['database'] = 'shulex_collector_prod'
    
    db = DatabaseConnector(db_config)
    if not db.connect():
        logger.error("无法连接到数据库 shulex_collector_prod")
        return None
    
    try:
        # 定义要查询的表
        tables_to_check = ['log_a', 'log_b', 'log_c', 'log_d']
        
        logger.info(f"正在查询 job_id: {job_id}")
        
        all_results = []
        
        # 查询各个表
        for table_name in tables_to_check:
            query = f"SELECT * FROM {table_name} WHERE req_ssn = %s"
            try:
                records = db.execute_query(query, (job_id,))
                if records:
                    all_results.extend(records)
                    logger.info(f"在表 {table_name} 中找到 {len(records)} 条记录")
                    
            except Exception as e:
                logger.error(f"查询表 {table_name} 失败: {str(e)}")
        
        # 分析查询结果
        if len(all_results) == 0:
            logger.warning(f"在所有表中都没有找到 job_id: {job_id}")
            return None
            
        elif len(all_results) == 1:
            # 找到唯一记录
            record = all_results[0]
            ext_ssn = record.get('ext_ssn', '')
            if ext_ssn:
                logger.info(f"找到唯一记录，task_id (ext_ssn): {ext_ssn}")
                return ext_ssn
            else:
                logger.warning(f"找到记录但 ext_ssn 为空")
                return None
                
        else:
            # 找到多条记录，需要去重
            unique_ext_ssns = set()
            for record in all_results:
                ext_ssn = record.get('ext_ssn', '')
                if ext_ssn:
                    unique_ext_ssns.add(ext_ssn)
            
            if len(unique_ext_ssns) == 1:
                task_id = list(unique_ext_ssns)[0]
                logger.info(f"找到 {len(all_results)} 条记录，去重后得到唯一 task_id: {task_id}")
                return task_id
            else:
                logger.warning(f"找到 {len(all_results)} 条记录，但包含 {len(unique_ext_ssns)} 个不同的 ext_ssn")
                return None
    
    finally:
        db.disconnect()


def get_default_files_for_task_type(task_type: str) -> List[str]:
    """
    根据任务类型获取默认的文件列表
    
    Args:
        task_type: 任务类型，如 'AmazonListingJob' 或 'AmazonReviewStarJob'
        
    Returns:
        List[str]: 默认文件列表
    """
    if task_type == 'AmazonListingJob':
        return ['login.gz', 'normal.gz']
    elif task_type == 'AmazonReviewStarJob':
        return ['page_1.gz', 'page_2.gz', 'page_3.gz', 'page_4.gz', 'page_5.gz']
    else:
        # 对于未知任务类型，尝试默认文件
        return ['login.gz', 'normal.gz']


def update_task_mapping(input_param: str, task_type: str, actual_task_id: str, 
                       save_dir: str = 'data/output') -> bool:
    """
    更新任务映射文件，记录输入参数到实际下载路径的映射
    
    Args:
        input_param: 用户输入的参数（task_id或job_id）
        task_type: 任务类型
        actual_task_id: 实际的任务ID
        save_dir: 保存目录
        
    Returns:
        bool: 更新成功返回True
    """
    try:
        # 映射文件路径
        map_file_path = f"{save_dir}/task_mapping.json"
        
        # 读取现有映射
        mapping = {}
        if os.path.exists(map_file_path):
            try:
                with open(map_file_path, 'r', encoding='utf-8') as f:
                    mapping = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                logger.warning(f"映射文件格式错误或不存在，将创建新的映射文件")
                mapping = {}
        
        # 生成相对路径
        relative_path = f"./{task_type}/{actual_task_id}/"
        
        # 更新映射
        mapping[input_param] = {
            'relative_path': relative_path,
            'task_type': task_type,
            'actual_task_id': actual_task_id,
            'last_updated': datetime.now().isoformat()
        }
        
        # 确保目录存在
        os.makedirs(save_dir, exist_ok=True)
        
        # 保存更新后的映射
        with open(map_file_path, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ 任务映射已更新: {input_param} -> {relative_path}")
        return True
        
    except Exception as e:
        logger.error(f"❌ 更新任务映射失败: {str(e)}")
        return False


def print_task_mapping_info(input_param: str, task_type: str, actual_task_id: str, 
                           save_dir: str = 'data/output') -> None:
    """
    打印任务映射信息
    
    Args:
        input_param: 用户输入的参数
        task_type: 任务类型
        actual_task_id: 实际的任务ID
        save_dir: 保存目录
    """
    relative_path = f"./{task_type}/{actual_task_id}/"
    full_path = f"{save_dir}/{task_type}/{actual_task_id}/"
    
    print(f"\n📋 任务映射信息:")
    print(f"  🔍 输入参数: {input_param}")
    print(f"  📁 相对路径: {relative_path}")
    print(f"  📄 映射文件: {save_dir}/task_mapping.json")


def show_task_mapping(save_dir: str = 'data/output') -> None:
    """
    显示当前的任务映射文件内容
    
    Args:
        save_dir: 保存目录
    """
    map_file_path = f"{save_dir}/task_mapping.json"
    
    print("🔍 Azure Storage 任务映射查看器")
    print("=" * 80)
    
    if not os.path.exists(map_file_path):
        print(f"❌ 映射文件不存在: {map_file_path}")
        return
    
    try:
        with open(map_file_path, 'r', encoding='utf-8') as f:
            mapping = json.load(f)
        
        if not mapping:
            print("📋 映射文件为空")
            return
        
        print(f"📄 映射文件路径: {map_file_path}")
        print(f"📊 总计映射数量: {len(mapping)}")
        print("\n📋 任务映射列表:")
        print("-" * 80)
        
        # 按最后更新时间排序
        sorted_mappings = sorted(
            mapping.items(),
            key=lambda x: x[1].get('last_updated', ''),
            reverse=True
        )
        
        for input_param, info in sorted_mappings:
            print(f"\n🔍 输入参数: {input_param}")
            task_type = info.get('task_type', 'Unknown')
            
            if task_type == 'parse':
                # 解析文件映射显示
                print(f"  📂 类型: 解析文件")
                print(f"  📋 Job ID: {info.get('job_id', 'Unknown')}")
                print(f"  📋 Task ID: {info.get('task_id', 'Unknown')}")
            else:
                # 原始文件映射显示
                print(f"  📂 任务类型: {task_type}")
                print(f"  📋 实际任务ID: {info.get('actual_task_id', 'Unknown')}")
            
            print(f"  📁 相对路径: {info.get('relative_path', 'Unknown')}")
            print(f"  📅 最后更新: {info.get('last_updated', 'Unknown')}")
            
            # 检查目录是否存在，通过relative_path构建完整路径
            relative_path = info.get('relative_path', '')
            if relative_path:
                # 移除相对路径前缀 './' 并构建完整路径
                clean_path = relative_path.lstrip('./')
                full_path = os.path.join(save_dir, clean_path)
                
                if os.path.exists(full_path):
                    file_count = len([f for f in os.listdir(full_path) if os.path.isfile(os.path.join(full_path, f))])
                    print(f"  📄 文件数量: {file_count}")
                else:
                    print(f"  ⚠️  目录不存在")
            else:
                print(f"  ⚠️  相对路径信息缺失")
        
        print("\n" + "=" * 80)
        print("💡 使用方式:")
        print(f"   根据映射，输入参数可以直接定位到对应的下载文件夹")
        print(f"   例如：输入 '{list(mapping.keys())[0]}' 对应文件夹 '{list(mapping.values())[0].get('relative_path', '')}*'")
        
    except json.JSONDecodeError:
        print(f"❌ 映射文件格式错误: {map_file_path}")
    except Exception as e:
        print(f"❌ 读取映射文件失败: {str(e)}")


def handle_with_parse_mode(args) -> None:
    """
    处理同时获取原始数据和解析数据的模式（集成优化版本）
    
    Args:
        args: 命令行参数
    """
    print(f"🔍 Azure Storage 资源读取器 (原始数据 + 解析数据 - 优化版本)")
    print(f"📋 任务类型: {args.task_type_or_job_id}")
    print(f"📋 输入参数: {args.task_id_or_task_id}")
    
    # 保存原始输入参数用于映射
    original_input = args.task_id_or_task_id
    
    # 第一步：验证和转换任务ID，同时获取analysis_response
    task_id = None
    analysis_response = None
    job_id = None
    
    if is_valid_task_id(args.task_id_or_task_id):
        # 直接使用作为任务ID
        task_id = args.task_id_or_task_id
        print(f"✅ 检测到有效的任务ID: {task_id}")
    else:
        # 需要转换为任务ID并获取analysis_response
        job_id = args.task_id_or_task_id
        
        # 如果是纯数字，添加SL前缀
        if job_id.isdigit():
            job_id = f"SL{job_id}"
            print(f"🔄 添加SL前缀: {job_id}")
        
        print(f"🔍 通过数据库查询转换 job_id: {job_id}")
        
        # 🆕 尝试使用优化器获取task_id和analysis_response
        try:
            # 导入优化器模块
            from src.azure_resource_reader_optimizer import convert_job_id_to_task_info
            task_info = convert_job_id_to_task_info(job_id)
            
            if task_info is None:
                print(f"❌ 无法找到对应的任务ID，请检查 job_id: {job_id}")
                return
            
            task_id, analysis_response = task_info
            print(f"✅ 查询成功，获得任务ID: {task_id}")
            
            if analysis_response:
                print(f"✅ 获得 analysis_response 数据，长度: {len(str(analysis_response))} 字符")
                
                # 检查是否启用了analysis_response解析
                try:
                    from config.analysis_response_config import is_analysis_response_enabled
                    
                    if is_analysis_response_enabled(args.task_type_or_job_id):
                        print(f"✅ 任务类型 {args.task_type_or_job_id} 已启用 analysis_response 解析")
                    else:
                        print(f"⚠️  任务类型 {args.task_type_or_job_id} 未启用 analysis_response 解析，将使用传统方法")
                        analysis_response = None
                except ImportError:
                    print(f"⚠️  无法导入 analysis_response 配置，将使用传统方法")
                    analysis_response = None
            else:
                print(f"ℹ️  未找到 analysis_response 数据")
                
        except ImportError:
            # 回退到原始方法
            print(f"⚠️  优化器模块不可用，使用传统方法")
            task_id = convert_job_id_to_task_id(job_id)
            
            if task_id is None:
                print(f"❌ 无法找到对应的任务ID，请检查 job_id: {job_id}")
                return
            
            print(f"✅ 查询成功，获得任务ID: {task_id}")
    
    task_type = args.task_type_or_job_id
    print(f"📁 原始数据路径: yiya0110/download/compress/{task_type}/{task_id}/")
    print(f"📁 解析数据路径: collector0109/parse/{task_type}/{task_id}/")
    print("=" * 80)
    
    # 第二步：确定要处理的文件列表
    if args.files is None:
        # 根据任务类型自动选择默认文件
        files_to_process = get_default_files_for_task_type(task_type)
        print(f"📄 根据任务类型自动选择原始文件: {', '.join(files_to_process)}")
    else:
        files_to_process = args.files
        print(f"📄 用户指定原始文件: {', '.join(files_to_process)}")
    
    # 创建主读取器（yiya0110）
    reader = AzureResourceReader('yiya0110')
    
    # 确定是否需要解压缩
    decompress = args.output_type in ['html', 'txt', 'json']
    
    # 用于记录是否有文件成功下载
    successfully_downloaded_files = []
    parse_file_downloaded = False
    parse_result = None
    
    # 🆕 首先尝试使用优化方法获取解析文件
    if not args.info_only:
        print(f"\n🚀 步骤1: 使用优化方法获取解析文件")
        print("-" * 60)
        
        try:
            from src.azure_resource_reader_optimizer import fetch_and_save_parse_files_optimized
            
            # 创建collector0109读取器用于解析文件
            parse_reader = AzureResourceReader('collector0109')
            
            # 使用优化方法获取解析文件
            parse_result = fetch_and_save_parse_files_optimized(
                reader=parse_reader,
                task_type=task_type,
                task_id=task_id,
                save_dir=args.save_dir,
                decompress=decompress,
                job_id=job_id,
                analysis_response=analysis_response
            )
            
            if parse_result['success']:
                print(f"✅ 解析文件获取成功!")
                if 'method_used' in parse_result:
                    method_name = "analysis_response链接" if parse_result['method_used'] == 'analysis_response' else "Azure存储"
                    print(f"📡 获取方式: {method_name}")
                print(f"📥 下载文件数: {parse_result['total_files_downloaded']}")
                
                # 显示文件详情
                if parse_result['files_downloaded']:
                    for file_info in parse_result['files_downloaded']:
                        print(f"  ✅ {file_info['saved_name']}")
                        if 'size' in file_info:
                            print(f"     📊 大小: {file_info['size']} 字节")
                        print(f"     📁 路径: {file_info['local_path']}")
                
                parse_file_downloaded = True
            else:
                print(f"❌ 解析文件获取失败: {parse_result.get('error', '未知错误')}")
                
        except ImportError:
            print(f"⚠️  优化器模块不可用，将在处理原始文件时使用传统方法")
    
    # 处理每个原始文件
    print(f"\n📄 步骤2: 获取原始文件")
    print("-" * 60)
    
    for filename in files_to_process:
        print(f"\n📄 处理原始文件: {filename}")
        print("-" * 40)
        
        if args.info_only:
            # 显示原始文件信息
            blob_path = f"compress/{task_type}/{task_id}/{filename}"
            blob_info = reader.get_blob_info('download', blob_path)
            
            if blob_info:
                print(f"✅ 原始文件信息:")
                print(f"  📊 大小: {blob_info['size_mb']} MB")
                print(f"  📅 修改时间: {blob_info['last_modified']}")
                print(f"  🔗 URL: {blob_info['url']}")
            else:
                print("❌ 原始文件不存在或获取信息失败")
            continue
        
        # 读取原始文件
        content = reader.read_task_file(task_type, task_id, filename, decompress)
        
        if content is not None:
            print("✅ 原始文件读取成功!")
            if isinstance(content, str):
                print(f"📝 原始文件长度: {len(content)} 字符")
            else:
                print(f"📊 原始文件大小: {len(content)} 字节")
            
            # 保存原始文件
            save_filename = _generate_save_filename(filename, task_id, args.output_type)
            local_path = f"{args.save_dir}/{task_type}/{task_id}/{save_filename}"
            
            success = _save_content_to_file(content, local_path)
            if success:
                print(f"💾 原始文件已保存到: {local_path}")
                successfully_downloaded_files.append(filename)
        else:
            print("❌ 原始文件读取失败或文件不存在")
    
    # 如果优化方法没有成功获取解析文件，使用传统方法
    if not parse_file_downloaded and not args.info_only:
        print(f"\n🔄 步骤3: 使用传统方法获取解析文件")
        print("-" * 60)
        
        # 使用传统方法获取解析文件（仅第一个文件时执行）
        if files_to_process:
            filename = files_to_process[0]  # 解析文件与具体原始文件无关
            
            # 使用新方法同时读取原始文件和解析文件中的解析部分
            combined_content = reader.read_task_file_with_parse(task_type, task_id, filename, decompress)
            parse_content = combined_content.get('parse')
            
            if parse_content is not None:
                print("✅ 解析文件读取成功!")
                if isinstance(parse_content, str):
                    print(f"📝 解析文件长度: {len(parse_content)} 字符")
                    
                    # JSON格式验证和检测
                    if parse_content.strip().startswith('{') or parse_content.strip().startswith('['):
                        try:
                            parsed_data = json.loads(parse_content)
                            print(f"📋 JSON解析成功，类型: {type(parsed_data)}")
                        except json.JSONDecodeError:
                            print("⚠️  解析文件不是有效的JSON格式")
                    
                    # 显示预览
                    print(f"🔍 解析文件预览 (前200字符):")
                    print(parse_content[:200] + "..." if len(parse_content) > 200 else parse_content)
                else:
                    print(f"📊 解析文件大小: {len(parse_content)} 字节")
                
                # 保存解析文件
                parse_filename = _generate_save_filename("parse_result", task_id, "json")
                parse_local_path = f"{args.save_dir}/{task_type}/{task_id}/{parse_filename}"
                
                parse_success = _save_content_to_file(parse_content, parse_local_path)
                if parse_success:
                    print(f"💾 解析文件已保存到: {parse_local_path}")
                    parse_file_downloaded = True
            else:
                print("❌ 解析文件读取失败或文件不存在")
    
    # 第三步：更新任务映射文件
    if (successfully_downloaded_files or parse_file_downloaded) and not args.info_only and not args.no_mapping:
        print("\n" + "=" * 80)
        print("步骤4：更新任务映射文件")
        print("=" * 80)
        
        # 显示映射信息
        print_task_mapping_info(original_input, task_type, task_id, args.save_dir)
        
        # 更新原始文件映射
        mapping_success = update_task_mapping(original_input, task_type, task_id, args.save_dir)
        
        # 在 --with-parse 模式下，解析文件和原始文件在同一目录，不需要单独的映射
        if mapping_success:
            if parse_file_downloaded:
                print(f"✅ 成功下载原始文件和解析文件并更新映射")
                print(f"📄 原始文件数量: {len(successfully_downloaded_files)}")
                print(f"📄 解析文件: 1个 (保存在同一目录)")
                
                # 显示使用的方法
                if parse_result and 'method_used' in parse_result:
                    method_name = "analysis_response优化链接" if parse_result['method_used'] == 'analysis_response' else "Azure存储"
                    print(f"🚀 解析文件获取方式: {method_name}")
            else:
                print(f"✅ 成功下载原始文件并更新映射")
                print(f"📄 已下载文件: {', '.join(successfully_downloaded_files)}")
                if not parse_file_downloaded:
                    print("⚠️  解析文件下载失败")
    
    elif args.info_only:
        print(f"\n📋 信息查看模式，未下载文件")
        # 显示解析文件信息（如果未在优化步骤中获取）
        if not parse_file_downloaded:
            parse_reader = AzureResourceReader('collector0109')
            parse_files = parse_reader.list_parse_files(task_type, task_id)
            if parse_files:
                print(f"\n✅ 解析文件信息 (共{len(parse_files)}个):")
                for parse_file in parse_files:
                    print(f"  📄 {parse_file['name']}")
                    print(f"     📊 大小: {parse_file['size']} 字节")
            else:
                print("\n❌ 未找到解析文件")
                
    elif args.no_mapping:
        print(f"\n📋 已禁用映射文件生成")
    elif not successfully_downloaded_files and not parse_file_downloaded:
        print(f"\n⚠️  没有文件成功下载，未更新映射")


def handle_parse_mode(reader: AzureResourceReader, job_id: str, task_id: str, 
                     args, original_input: str) -> None:
    """
    处理解析模式的文件读取
    
    Args:
        reader: Azure资源读取器实例
        job_id: 请求序列号
        task_id: 任务ID
        args: 命令行参数
        original_input: 原始输入参数
    """
    
    # 如果只是列出文件
    if args.list_jobs:
        print(f"📋 列出解析文件:")
        files = reader.list_parse_files(job_id, task_id)
        
        if files:
            print(f"✅ 找到 {len(files)} 个文件:")
            for file_info in files:
                print(f"  📄 文件: {file_info['name']}")
                print(f"     📊 大小: {file_info['size']} 字节")
                print(f"     📅 修改: {file_info['last_modified']}")
                print()
        else:
            print("❌ 未找到文件")
        return
    
    # 确定是否需要解压缩
    decompress = args.output_type in ['html', 'txt', 'json']
    
    # 用于记录是否有文件成功下载
    successfully_downloaded_files = []
    
    # 确定要处理的文件列表
    if args.files is None:
        # 解析模式默认自动查找JSON文件
        files_to_process = [None]  # None表示自动查找
        print(f"📄 解析模式：自动查找JSON文件")
    else:
        files_to_process = args.files
        print(f"📄 用户指定文件: {', '.join(files_to_process)}")
    
    # 处理每个文件
    for filename in files_to_process:
        if filename is None:
            print(f"\n📄 自动查找解析文件:")
        else:
            print(f"\n📄 处理文件: {filename}")
        print("-" * 60)
        
        # 仅显示信息
        if args.info_only:
            if filename is None:
                files = reader.list_parse_files(job_id, task_id)
                if files:
                    print(f"✅ 找到 {len(files)} 个文件:")
                    for file_info in files:
                        print(f"  📄 {file_info['name']}")
                        print(f"     📊 大小: {file_info['size']} 字节")
                else:
                    print("❌ 未找到文件")
            else:
                # 构造完整路径用于获取信息
                blob_path = f"parse/{job_id}/{task_id}/{filename}"
                blob_info = reader.get_blob_info('parse', blob_path)
                
                if blob_info:
                    print(f"✅ 文件信息:")
                    print(f"  📊 大小: {blob_info['size_mb']} MB")
                    print(f"  📅 修改时间: {blob_info['last_modified']}")
                    print(f"  🔗 URL: {blob_info['url']}")
                else:
                    print("❌ 文件不存在或获取信息失败")
            continue
        
        # 读取文件内容
        content = reader.read_parse_file(job_id, task_id, filename, decompress)
        
        if content is None:
            print("❌ 读取失败或文件不存在")
            continue
        
        print("✅ 读取成功!")
        
        # 显示内容信息
        if isinstance(content, str):
            print(f"📝 内容长度: {len(content)} 字符")
            
            # 如果是JSON类型，尝试解析和格式化
            if args.output_type == 'json':
                try:
                    if content.strip().startswith('{') or content.strip().startswith('['):
                        parsed_data = json.loads(content)
                        print(f"📋 JSON解析成功，类型: {type(parsed_data)}")
                        if isinstance(parsed_data, dict):
                            print(f"🔑 JSON键: {list(parsed_data.keys())}")
                        elif isinstance(parsed_data, list):
                            print(f"📊 JSON数组长度: {len(parsed_data)}")
                except json.JSONDecodeError:
                    print("⚠️  内容不是有效的JSON格式")
            
            # 显示预览
            print(f"🔍 内容预览 (前200字符):")
            print(content[:200] + "..." if len(content) > 200 else content)
            
        else:
            print(f"📊 数据长度: {len(content)} 字节")
        
        # 保存到本地文件
        actual_filename = filename if filename else "auto_found"
        
        # 检测内容是否为JSON格式，如果是则强制使用json扩展名
        output_type_to_use = args.output_type
        if isinstance(content, str) and (content.strip().startswith('{') or content.strip().startswith('[')):
            try:
                json.loads(content)  # 验证是否为有效JSON
                output_type_to_use = "json"  # 强制使用json格式
                print("🔍 检测到JSON内容，将保存为.json文件")
            except json.JSONDecodeError:
                pass  # 不是有效JSON，保持原输出类型
        
        save_filename = _generate_save_filename(actual_filename, task_id, output_type_to_use)
        local_path = f"{args.save_dir}/parse/{job_id}/{task_id}/{save_filename}"
        
        success = _save_content_to_file(content, local_path)
        if success:
            print(f"💾 文件已保存到: {local_path}")
            successfully_downloaded_files.append(actual_filename)
        else:
            print("❌ 保存失败")
    
    # 更新任务映射文件（如果有文件成功下载且未禁用映射）
    if successfully_downloaded_files and not args.info_only and not args.no_mapping:
        print("\n" + "=" * 80)
        print("第三步：更新任务映射文件")
        print("=" * 80)
        
        # 显示映射信息
        print_parse_mapping_info(original_input, job_id, task_id, args.save_dir)
        
        # 更新映射
        mapping_success = update_parse_mapping(original_input, job_id, task_id, args.save_dir)
        
        if mapping_success:
            print(f"✅ 成功下载 {len(successfully_downloaded_files)} 个文件并更新映射")
            print(f"📄 已下载文件: {', '.join(successfully_downloaded_files)}")
        else:
            print("⚠️  文件下载成功但映射更新失败")
    
    elif args.info_only:
        print(f"\n📋 信息查看模式，未下载文件")
    elif args.no_mapping:
        print(f"\n📋 已禁用映射文件生成")
    elif not successfully_downloaded_files:
        print(f"\n⚠️  没有文件成功下载，未更新映射")


def print_parse_mapping_info(original_input: str, job_id: str, task_id: str, 
                            save_dir: str = 'data/output') -> None:
    """
    打印解析文件映射信息
    
    Args:
        original_input: 原始输入参数
        job_id: 请求序列号（实际是任务类型）
        task_id: 任务ID
        save_dir: 保存目录
    """
    relative_path = f"./parse/{job_id}/{task_id}/"
    full_path = f"{save_dir}/parse/{job_id}/{task_id}/"
    
    print(f"\n📋 解析文件映射信息:")
    print(f"  🔍 输入参数: {original_input}")
    print(f"  📁 相对路径: {relative_path}")
    print(f"  📄 映射文件: {save_dir}/task_mapping.json")


def update_parse_mapping(original_input: str, job_id: str, task_id: str, 
                        save_dir: str = 'data/output') -> bool:
    """
    更新解析文件映射
    
    Args:
        original_input: 原始输入参数
        job_id: 请求序列号（实际是任务类型）  
        task_id: 任务ID
        save_dir: 保存目录
        
    Returns:
        bool: 更新成功返回True
    """
    try:
        # 映射文件路径
        map_file_path = f"{save_dir}/task_mapping.json"
        
        # 读取现有映射
        mapping = {}
        if os.path.exists(map_file_path):
            try:
                with open(map_file_path, 'r', encoding='utf-8') as f:
                    mapping = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                logger.warning(f"映射文件格式错误或不存在，将创建新的映射文件")
                mapping = {}
        
        # 生成相对路径
        relative_path = f"./parse/{job_id}/{task_id}/"
        
        # 更新映射
        mapping[original_input] = {
            'relative_path': relative_path,
            'task_type': 'parse',
            'job_id': job_id,
            'task_id': task_id,
            'last_updated': datetime.now().isoformat()
        }
        
        # 确保目录存在
        os.makedirs(save_dir, exist_ok=True)
        
        # 保存更新后的映射
        with open(map_file_path, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ 解析文件映射已更新: {original_input} -> {relative_path}")
        return True
        
    except Exception as e:
        logger.error(f"❌ 更新解析文件映射失败: {str(e)}")
        return False


if __name__ == '__main__':
    main() 