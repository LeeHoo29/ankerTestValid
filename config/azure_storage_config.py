#!/usr/bin/env python3
"""
Azure Storage 配置文件
"""
import os
from typing import Dict, Optional
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

# Azure Storage 认证配置（从环境变量读取）
AZURE_STORAGE_CONFIG = {
    'client_id': os.getenv('AZURE_STORAGE_CLIENT_ID', os.getenv('AZURE_CLIENT_ID', 'YOUR_AZURE_CLIENT_ID')),
    'tenant_id': os.getenv('AZURE_STORAGE_TENANT_ID', os.getenv('AZURE_TENANT_ID', 'YOUR_AZURE_TENANT_ID')),
    'client_secret': os.getenv('AZURE_STORAGE_CLIENT_SECRET', os.getenv('AZURE_CLIENT_SECRET', 'YOUR_AZURE_CLIENT_SECRET')),
    'subscription_id': os.getenv('AZURE_STORAGE_SUB_ID', os.getenv('AZURE_SUBSCRIPTION_ID', 'YOUR_AZURE_SUBSCRIPTION_ID')),
    'resource_group': os.getenv('AZURE_STORAGE_RESOURCE_GROUP', 'YOUR_RESOURCE_GROUP')
}

# 存储账户配置（需要根据实际情况调整）
STORAGE_ACCOUNT_CONFIG = {
    'account_name': '',  # 需要填入实际的存储账户名
    'account_url': '',   # 格式: https://{account_name}.blob.core.windows.net
    'container_name': 'shulex-data',  # 默认容器名
}

# yiya0110 存储账户配置
YIYA0110_STORAGE_CONFIG = {
    'account_name': 'yiya0110',
    'account_url': 'https://yiya0110.blob.core.windows.net',
    'container_name': 'download',
    'blob_base_path': 'compress'  # 新路径结构的基础路径
}

# 存储账户配置：collector0109（解析数据）
COLLECTOR0109_STORAGE_CONFIG = {
    'account_name': 'collector0109',
    'account_url': 'https://collector0109.blob.core.windows.net',
    'container_name': 'parse',
    'blob_base_path': 'parse'  # 解析文件的基础路径：parse/{任务类型}/{taskID}/* (经测试验证)
}

# 环境变量设置（用于Azure SDK认证）
def set_azure_environment_variables():
    """设置Azure认证相关的环境变量"""
    os.environ['AZURE_CLIENT_ID'] = AZURE_STORAGE_CONFIG['client_id']
    os.environ['AZURE_TENANT_ID'] = AZURE_STORAGE_CONFIG['tenant_id']
    os.environ['AZURE_CLIENT_SECRET'] = AZURE_STORAGE_CONFIG['client_secret']
    os.environ['AZURE_SUBSCRIPTION_ID'] = AZURE_STORAGE_CONFIG['subscription_id']


def get_storage_account_url(account_name: str, service_type: str = 'blob') -> str:
    """
    获取指定存储账户的服务URL
    
    Args:
        account_name: 存储账户名 (如: 'yiya0110', 'collector0109')
        service_type: 服务类型 ('blob', 'queue', 'file')
        
    Returns:
        str: 完整的服务URL
    """
    if account_name == 'yiya0110':
        base_url = YIYA0110_STORAGE_CONFIG['account_url']
    elif account_name == 'collector0109':
        base_url = COLLECTOR0109_STORAGE_CONFIG['account_url']
    else:
        # 通用格式
        base_url = f"https://{account_name}.{service_type}.core.windows.net"
    
    return base_url


# 常用存储操作配置
BLOB_OPERATIONS_CONFIG = {
    'upload_chunk_size': 4 * 1024 * 1024,  # 4MB
    'max_concurrency': 4,
    'timeout': 300,  # 5分钟
    'retry_total': 3
} 