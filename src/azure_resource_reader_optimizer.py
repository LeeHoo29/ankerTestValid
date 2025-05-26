#!/usr/bin/env python3
"""
Azure Resource Reader 优化器模块
提供优化的解析文件获取方法，优先使用analysis_response链接下载
"""

import os
import sys
import json
import logging
import requests
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple, Any
from datetime import datetime
import gzip

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 导入数据库连接器
from src.db.connector import DatabaseConnector
from config.db_config import DB_CONFIG

# 配置日志
logger = logging.getLogger(__name__)


def convert_job_id_to_task_info(job_id: str) -> Optional[Tuple[str, str]]:
    """
    通过数据库查询将 job_id 转换为 task_id 和 analysis_response
    
    Args:
        job_id: 请求序列号，如 'SL2796867471'
        
    Returns:
        Optional[Tuple[str, str]]: 找到的 (task_id, analysis_response)，未找到返回None
        - task_id: ext_ssn字段的值
        - analysis_response: analysis_response字段的值（可能为None）
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
        
        # 查询各个表，增加analysis_response字段
        for table_name in tables_to_check:
            query = f"SELECT ext_ssn, analysis_response FROM {table_name} WHERE req_ssn = %s"
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
            analysis_response = record.get('analysis_response', None)
            
            if ext_ssn:
                logger.info(f"找到唯一记录，task_id (ext_ssn): {ext_ssn}")
                if analysis_response:
                    logger.info(f"找到 analysis_response 字段，长度: {len(str(analysis_response))} 字符")
                else:
                    logger.info("analysis_response 字段为空")
                return (ext_ssn, analysis_response)
            else:
                logger.warning(f"找到记录但 ext_ssn 为空")
                return None
                
        else:
            # 找到多条记录，需要去重
            unique_records = {}
            for record in all_results:
                ext_ssn = record.get('ext_ssn', '')
                analysis_response = record.get('analysis_response', None)
                if ext_ssn:
                    if ext_ssn not in unique_records:
                        unique_records[ext_ssn] = analysis_response
                    # 如果存在多个相同ext_ssn但不同analysis_response，优先选择非空的
                    elif analysis_response and not unique_records[ext_ssn]:
                        unique_records[ext_ssn] = analysis_response
            
            if len(unique_records) == 1:
                task_id = list(unique_records.keys())[0]
                analysis_response = unique_records[task_id]
                logger.info(f"找到 {len(all_results)} 条记录，去重后得到唯一 task_id: {task_id}")
                if analysis_response:
                    logger.info(f"找到 analysis_response 字段，长度: {len(str(analysis_response))} 字符")
                return (task_id, analysis_response)
            else:
                logger.warning(f"找到 {len(all_results)} 条记录，但包含 {len(unique_records)} 个不同的 ext_ssn")
                return None
    
    finally:
        db.disconnect()


def try_download_from_analysis_response(task_type: str, task_id: str, 
                                       analysis_response: str, save_dir: str, 
                                       decompress: bool = True) -> Dict[str, any]:
    """
    尝试从analysis_response中的链接下载文件
    
    Args:
        task_type: 任务类型
        task_id: 任务ID
        analysis_response: analysis_response JSON字符串
        save_dir: 保存目录
        decompress: 是否解压缩
        
    Returns:
        Dict: 下载结果，包含提取的文件路径信息
    """
    # 导入配置解析函数
    try:
        from config.analysis_response_config import parse_analysis_response
    except ImportError as e:
        return {
            'success': False,
            'error': f'导入配置失败: {str(e)}',
            'files_downloaded': [],
            'extracted_blob_path': None
        }
    
    try:
        # 解析analysis_response
        download_links = parse_analysis_response(analysis_response)
        
        if not download_links:
            return {
                'success': False,
                'error': 'analysis_response中没有找到下载链接',
                'files_downloaded': [],
                'extracted_blob_path': None
            }
        
        logger.info(f"📡 从analysis_response解析到 {len(download_links)} 个下载链接")
        
        # 🆕 创建统一目录结构: data/output/{task_type}/{task_id}/
        save_path = Path(save_dir) / task_type / task_id
        save_path.mkdir(parents=True, exist_ok=True)
        
        downloaded_files = []
        extracted_blob_path = None
        
        for i, url in enumerate(download_links):
            try:
                logger.info(f"📥 正在下载第 {i+1} 个文件: {url}")
                
                # 🆕 提取Blob路径（用于后续回退）
                if extracted_blob_path is None:
                    extracted_blob_path = extract_blob_path_from_url(url)
                
                # 使用requests下载
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                
                content = response.content
                
                # 如果需要解压缩且是gzip内容
                if decompress and (url.endswith('.gz') or 'gzip' in response.headers.get('content-encoding', '')):
                    try:
                        content = gzip.decompress(content)
                        logger.info("✅ 文件已解压缩")
                    except gzip.BadGzipFile:
                        logger.warning("文件不是有效的gzip格式，保持原内容")
                
                # 🆕 统一使用 parse_result.json 作为文件名
                saved_filename = 'parse_result.json'
                file_path = save_path / saved_filename
                
                # 保存文件 
                if isinstance(content, str):
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                else:
                    # 尝试解码为UTF-8（JSON文件通常是文本）
                    try:
                        content_str = content.decode('utf-8')
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content_str)
                    except UnicodeDecodeError:
                        # 如果无法解码，保存为二进制
                        with open(file_path, 'wb') as f:
                            f.write(content)
                
                logger.info(f"✅ 文件已保存: {file_path}")
                
                downloaded_files.append({
                    'original_name': extract_filename_from_url(url),
                    'saved_name': saved_filename,  # 🆕 统一的文件名
                    'local_path': str(file_path),
                    'size': len(content),
                    'url': url
                })
                
            except Exception as e:
                logger.error(f"❌ 下载文件失败 ({url}): {str(e)}")
                continue
        
        if downloaded_files:
            logger.info(f"✅ 从analysis_response链接下载成功，共 {len(downloaded_files)} 个文件")
            return {
                'success': True,
                'files_downloaded': downloaded_files,
                'save_path': str(save_path),
                'extracted_blob_path': extracted_blob_path
            }
        else:
            logger.warning("⚠️  所有下载链接都失败了")
            return {
                'success': False,
                'error': '所有下载链接都失败了',
                'files_downloaded': [],
                'extracted_blob_path': extracted_blob_path
            }
            
    except Exception as e:
        logger.error(f"❌ 处理analysis_response失败: {str(e)}")
        return {
            'success': False,
            'error': f'处理analysis_response失败: {str(e)}',
            'files_downloaded': [],
            'extracted_blob_path': None
        }


def extract_filename_from_url(url: str) -> str:
    """
    从URL中提取文件名
    
    Args:
        url: 下载URL
        
    Returns:
        str: 文件名
    """
    try:
        from urllib.parse import urlparse, unquote
        parsed_url = urlparse(url)
        path = unquote(parsed_url.path)
        filename = path.split('/')[-1]
        
        # 如果提取到有效文件名则返回，否则使用默认名称
        if filename and '.' in filename:
            return filename
        else:
            return "parse_result.json"
            
    except Exception:
        return "parse_result.json"


def extract_blob_path_from_url(url: str) -> Optional[str]:
    """
    🆕 从URL中提取Azure Blob路径
    例如: https://collector0109.blob.core.windows.net/parse/parse/AmazonReviewStarJob/1910599147004108800/7c5f4199-0512-48e6-993e-7301ccd4d356.json
    提取: parse/AmazonReviewStarJob/1910599147004108800/7c5f4199-0512-48e6-993e-7301ccd4d356.json
    
    Args:
        url: 完整的下载URL
        
    Returns:
        Optional[str]: 提取的Blob路径，如果失败返回None
    """
    try:
        from urllib.parse import urlparse, unquote
        parsed_url = urlparse(url)
        
        # 检查是否是collector0109.blob.core.windows.net域名
        if 'collector0109.blob.core.windows.net' not in parsed_url.netloc:
            return None
            
        # 获取路径部分，去掉前导的/
        path = unquote(parsed_url.path)
        if path.startswith('/'):
            path = path[1:]
        
        # 检查路径是否以.json结尾 (确保是JSON文件)
        if not path.endswith('.json'):
            return None
            
        # 移除容器名 (parse/) 保留实际的Blob路径
        path_parts = path.split('/', 1)
        if len(path_parts) >= 2 and path_parts[0] == 'parse':
            blob_path = path_parts[1]  # 去掉容器名，保留实际路径
            logger.info(f"🔍 成功提取Blob路径: {blob_path}")
            return blob_path
        else:
            logger.warning(f"⚠️  无法从路径中提取有效的Blob路径: {path}")
            return None
            
    except Exception as e:
        logger.error(f"❌ 提取Blob路径失败: {str(e)}")
        return None


def try_azure_storage_with_specific_path(reader, blob_path: str, task_type: str, task_id: str, 
                                        save_dir: str, decompress: bool = True) -> Dict[str, any]:
    """
    🆕 使用指定的Blob路径从Azure存储下载文件
    
    Args:
        reader: Azure读取器实例 
        blob_path: 具体的Blob路径 (如: parse/AmazonReviewStarJob/1910599147004108800/xxx.json)
        task_type: 任务类型
        task_id: 任务ID
        save_dir: 保存目录
        decompress: 是否解压缩
        
    Returns:
        Dict: 下载结果
    """
    logger.info(f"🎯 尝试使用具体路径从Azure存储下载: {blob_path}")
    
    try:
        # 直接读取指定路径的文件
        container_name = reader.storage_config['container_name']  # 应该是 'parse'
        
        # 读取文件内容
        content = reader.read_blob_content(container_name, blob_path, decompress=decompress)
        
        if content is None:
            logger.warning(f"⚠️  指定路径文件不存在或读取失败: {blob_path}")
            return {
                'success': False,
                'error': f'指定路径文件不存在: {blob_path}',
                'files_downloaded': []
            }
        
        # 🆕 保存到统一目录结构: data/output/{task_type}/{task_id}/
        save_path = Path(save_dir) / task_type / task_id
        save_path.mkdir(parents=True, exist_ok=True)
        
        # 🆕 统一使用 parse_result.json 作为文件名（而不是原始的长文件名）
        saved_filename = 'parse_result.json'
        file_path = save_path / saved_filename
        
        if isinstance(content, str):
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        else:
            with open(file_path, 'wb') as f:
                f.write(content)
        
        logger.info(f"✅ 从Azure存储精确下载成功: {file_path}")
        
        # 提取原始文件名用于记录
        original_filename = blob_path.split('/')[-1]
        
        return {
            'success': True,
            'files_downloaded': [{
                'original_name': original_filename,
                'saved_name': saved_filename,  # 🆕 统一的文件名
                'local_path': str(file_path),
                'size': len(content),
                'content_length': len(content),
                'blob_path': blob_path
            }],
            'save_path': str(save_path),
            'method_used': 'azure_storage_specific_path'
        }
        
    except Exception as e:
        logger.error(f"❌ Azure存储精确下载失败: {str(e)}")
        return {
            'success': False,
            'error': f'Azure存储精确下载失败: {str(e)}',
            'files_downloaded': []
        }


def fetch_and_save_parse_files_optimized(reader, task_type: str, task_id: str, 
                                         save_dir: str = 'data/output', 
                                         decompress: bool = True,
                                         job_id: str = None,
                                         analysis_response: str = None) -> Dict[str, any]:
    """
    🆕 优化版解析文件获取方法
    优先尝试从analysis_response中的链接下载，失败时智能回退到Azure存储
    
    Args:
        reader: AzureResourceReader实例
        task_type: 任务类型（如: AmazonReviewStarJob）
        task_id: 任务ID（如: 1887037115222994944）
        save_dir: 保存目录，默认: data/output
        decompress: 是否自动解压缩，默认为True
        job_id: 请求序列号（用于数据库查询）
        analysis_response: analysis_response JSON字符串
        
    Returns:
        Dict: 包含操作结果的字典
    """
    logger.info(f"🔍 开始优化版解析文件获取流程")
    logger.info(f"📋 任务类型: {task_type}")
    logger.info(f"📋 任务ID: {task_id}")
    
    # 第一步：尝试从analysis_response获取下载链接
    download_success = False
    downloaded_files = []
    extracted_blob_path = None
    method_used = None
    
    if analysis_response:
        logger.info(f"🔗 尝试从 analysis_response 获取下载链接")
        download_result = try_download_from_analysis_response(
            task_type, task_id, analysis_response, save_dir, decompress
        )
        
        # 保存提取的路径信息，无论是否下载成功
        extracted_blob_path = download_result.get('extracted_blob_path')
        
        if download_result['success']:
            logger.info(f"✅ 从 analysis_response 链接下载成功")
            download_success = True
            downloaded_files = download_result['files_downloaded']
            method_used = 'analysis_response'
        else:
            logger.warning(f"⚠️  从 analysis_response 链接下载失败: {download_result.get('error')}")
    else:
        logger.info(f"📝 未提供 analysis_response 或任务类型未启用")
    
    # 第二步：如果第一步失败，尝试智能回退
    if not download_success:
        logger.info(f"🔄 回退到 Azure 存储获取方法")
        
        # 🆕 如果有提取的Blob路径，优先使用精确路径下载
        if extracted_blob_path:
            logger.info(f"🎯 使用从链接中提取的精确路径进行下载")
            
            # 确保使用collector0109读取器
            if reader.account_name != 'collector0109':
                from src.azure_resource_reader import AzureResourceReader
                azure_reader = AzureResourceReader('collector0109')
            else:
                azure_reader = reader
            
            # 尝试精确路径下载
            precise_result = try_azure_storage_with_specific_path(
                azure_reader, extracted_blob_path, task_type, task_id, save_dir, decompress
            )
            
            if precise_result['success']:
                logger.info(f"✅ 使用精确路径从Azure存储下载成功")
                download_success = True
                downloaded_files = precise_result['files_downloaded']
                method_used = 'azure_storage_specific_path'
            else:
                logger.warning(f"⚠️  精确路径下载也失败: {precise_result.get('error')}")
        
        # 如果精确路径下载失败或没有提取到路径，使用传统方法
        if not download_success:
            logger.info(f"🔄 使用传统Azure存储搜索方法")
            
            # 确保使用collector0109读取器
            if reader.account_name != 'collector0109':
                from src.azure_resource_reader import AzureResourceReader
                azure_reader = AzureResourceReader('collector0109')
            else:
                azure_reader = reader
            
            # 🆕 使用修改后的方法，确保保存到正确目录
            azure_result = fetch_parse_files_to_unified_directory(
                azure_reader, task_type, task_id, save_dir, decompress
            )
            
            if azure_result['success']:
                logger.info(f"✅ 传统Azure存储方法下载成功")
                download_success = True
                downloaded_files = azure_result['files_downloaded']
                method_used = 'azure_storage_search'
            else:
                logger.error(f"❌ 传统Azure存储方法也失败: {azure_result.get('error')}")
    
    # 返回结果
    if download_success:
        save_path = f"{save_dir}/{task_type}/{task_id}" if downloaded_files else None
        return {
            'success': True,
            'files_downloaded': downloaded_files,
            'save_path': save_path,
            'total_files_downloaded': len(downloaded_files),
            'method_used': method_used
        }
    else:
        return {
            'success': False,
            'error': '所有获取方法都失败',
            'files_downloaded': [],
            'save_path': None
        }


def fetch_parse_files_to_unified_directory(reader, task_type: str, task_id: str, 
                                          save_dir: str = 'data/output', 
                                          decompress: bool = True) -> Dict[str, any]:
    """
    🆕 从Azure存储获取解析文件并保存到统一目录结构
    这是对原始 fetch_and_save_parse_files 的包装，确保保存到正确位置
    
    Args:
        reader: AzureResourceReader实例 (collector0109)
        task_type: 任务类型
        task_id: 任务ID
        save_dir: 保存目录
        decompress: 是否解压缩
        
    Returns:
        Dict: 操作结果
    """
    logger.info(f"📁 使用传统方法搜索解析文件")
    
    try:
        # 使用原始方法获取文件（但会保存到parse子目录）
        original_result = reader.fetch_and_save_parse_files(
            task_type, task_id, save_dir, decompress
        )
        
        if not original_result['success']:
            return original_result
        
        # 🆕 将文件从parse子目录移动到统一目录，并统一命名为parse_result.json
        source_dir = Path(save_dir) / 'parse' / task_type / task_id
        target_dir = Path(save_dir) / task_type / task_id
        
        if source_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)
            
            moved_files = []
            for i, file_info in enumerate(original_result['files_downloaded']):
                source_file = Path(file_info['local_path'])
                
                # 🆕 统一使用 parse_result.json 作为文件名
                saved_filename = 'parse_result.json'
                target_file = target_dir / saved_filename
                
                # 移动并重命名文件
                import shutil
                shutil.move(str(source_file), str(target_file))
                
                # 更新文件信息
                updated_file_info = file_info.copy()
                updated_file_info['saved_name'] = saved_filename  # 🆕 统一的文件名
                updated_file_info['local_path'] = str(target_file)
                moved_files.append(updated_file_info)
                
                logger.info(f"📦 文件已移动到统一目录并重命名: {target_file}")
            
            # 清理空的parse目录
            try:
                source_dir.rmdir()
                source_dir.parent.rmdir()  # task_type目录
                (source_dir.parent.parent).rmdir()  # parse目录
            except OSError:
                pass  # 目录不为空，忽略
            
            return {
                'success': True,
                'files_downloaded': moved_files,
                'save_path': str(target_dir),
                'total_files_found': original_result.get('total_files_found', 0),
                'total_files_downloaded': len(moved_files)
            }
        else:
            logger.warning(f"⚠️  原始方法未创建预期的目录结构")
            return original_result
        
    except Exception as e:
        logger.error(f"❌ 统一目录处理失败: {str(e)}")
        return {
            'success': False,
            'error': f'统一目录处理失败: {str(e)}',
            'files_downloaded': []
        } 