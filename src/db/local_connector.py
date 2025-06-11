"""
本地数据库连接器模块，负责管理本地MySQL连接和任务映射数据操作
"""
import logging
import time
import json
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime

import mysql.connector
from mysql.connector import Error as MySQLError

# 导入本地数据库配置
from config.local_db_config import LOCAL_DB_CONFIG, TABLE_CONFIG

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LocalDatabaseConnector:
    """本地数据库连接器类，专门用于任务映射数据的本地存储"""

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化本地数据库连接器
        
        Args:
            config: 数据库配置信息，默认使用LOCAL_DB_CONFIG
        """
        self.config = config or LOCAL_DB_CONFIG
        self.table_config = TABLE_CONFIG
        self.connection = None
        self.cursor = None
        
    def connect(self) -> bool:
        """
        建立数据库连接
        
        Returns:
            bool: 连接成功返回True，否则返回False
        """
        try:
            # 建立数据库连接
            self.connection = mysql.connector.connect(**self.config)
            
            if self.connection.is_connected():
                db_info = self.connection.get_server_info()
                current_db = self.config.get('database', 'None')
                logger.info(f"已连接到本地MySQL服务器，版本: {db_info}，数据库: {current_db}")
                
                # 创建游标
                self.cursor = self.connection.cursor(dictionary=True)
                return True
                
        except MySQLError as err:
            logger.error(f"本地数据库连接失败: {err}")
            return False
    
    def disconnect(self) -> None:
        """关闭数据库连接"""
        if self.connection and self.connection.is_connected():
            if self.cursor:
                self.cursor.close()
            self.connection.close()
            logger.info("本地数据库连接已关闭")
    
    def create_tables(self) -> bool:
        """
        创建任务映射相关的数据表
        
        Returns:
            bool: 创建成功返回True，否则返回False
        """
        if not self.connection or not self.connection.is_connected():
            if not self.connect():
                logger.error("无法创建表，数据库未连接")
                return False
        
        try:
            # 创建任务映射主表
            create_task_mapping_table = f"""
            CREATE TABLE IF NOT EXISTS {self.table_config['task_mapping']} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                job_id VARCHAR(50) NOT NULL UNIQUE COMMENT '任务Job ID（索引键）',
                task_type VARCHAR(100) NOT NULL COMMENT '任务类型',
                actual_task_id VARCHAR(100) NOT NULL COMMENT '实际任务ID',
                relative_path VARCHAR(500) NOT NULL COMMENT '相对路径',
                full_path VARCHAR(1000) DEFAULT NULL COMMENT '完整路径',
                file_count INT DEFAULT 0 COMMENT '文件数量',
                has_parse_file BOOLEAN DEFAULT FALSE COMMENT '是否有解析文件',
                download_method VARCHAR(50) DEFAULT 'azure_storage' COMMENT '下载方式',
                status VARCHAR(20) DEFAULT 'success' COMMENT '状态：success, failed, processing',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                INDEX idx_job_id (job_id),
                INDEX idx_task_type (task_type),
                INDEX idx_status (status),
                INDEX idx_created_at (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务映射表'
            """
            
            # 创建文件详情表
            create_file_details_table = f"""
            CREATE TABLE IF NOT EXISTS {self.table_config['file_details']} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                mapping_id INT NOT NULL COMMENT '关联的任务映射ID',
                file_name VARCHAR(255) NOT NULL COMMENT '文件名',
                file_type VARCHAR(50) NOT NULL COMMENT '文件类型：original, parse',
                file_size BIGINT DEFAULT 0 COMMENT '文件大小（字节）',
                file_path VARCHAR(1000) NOT NULL COMMENT '文件完整路径',
                download_success BOOLEAN DEFAULT TRUE COMMENT '下载是否成功',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                FOREIGN KEY (mapping_id) REFERENCES {self.table_config['task_mapping']}(id) ON DELETE CASCADE,
                INDEX idx_mapping_id (mapping_id),
                INDEX idx_file_type (file_type)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务文件详情表'
            """
            
            # 执行建表语句
            self.cursor.execute(create_task_mapping_table)
            self.cursor.execute(create_file_details_table)
            
            logger.info("数据表创建成功")
            return True
            
        except MySQLError as err:
            logger.error(f"创建数据表失败: {err}")
            return False
    
    def insert_task_mapping(self, job_id: str, task_type: str, actual_task_id: str, 
                          relative_path: str, **kwargs) -> Optional[int]:
        """
        插入或更新任务映射记录
        
        Args:
            job_id: 任务Job ID
            task_type: 任务类型
            actual_task_id: 实际任务ID
            relative_path: 相对路径
            **kwargs: 其他可选参数
            
        Returns:
            Optional[int]: 成功返回记录ID，失败返回None
        """
        if not self.connection or not self.connection.is_connected():
            if not self.connect():
                logger.error("无法插入记录，数据库未连接")
                return None
        
        try:
            # 准备插入数据
            full_path = kwargs.get('full_path', '')
            file_count = kwargs.get('file_count', 0)
            has_parse_file = kwargs.get('has_parse_file', False)
            download_method = kwargs.get('download_method', 'azure_storage')
            status = kwargs.get('status', 'success')
            
            # 使用 ON DUPLICATE KEY UPDATE 实现插入或更新
            insert_query = f"""
            INSERT INTO {self.table_config['task_mapping']} 
            (job_id, task_type, actual_task_id, relative_path, full_path, 
             file_count, has_parse_file, download_method, status) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                task_type = VALUES(task_type),
                actual_task_id = VALUES(actual_task_id),
                relative_path = VALUES(relative_path),
                full_path = VALUES(full_path),
                file_count = VALUES(file_count),
                has_parse_file = VALUES(has_parse_file),
                download_method = VALUES(download_method),
                status = VALUES(status),
                updated_at = CURRENT_TIMESTAMP
            """
            
            params = (job_id, task_type, actual_task_id, relative_path, full_path,
                     file_count, has_parse_file, download_method, status)
            
            self.cursor.execute(insert_query, params)
            self.connection.commit()
            
            # 获取插入或更新的记录ID
            mapping_id = self.cursor.lastrowid
            if mapping_id == 0:  # 更新情况下，获取现有记录ID
                select_query = f"SELECT id FROM {self.table_config['task_mapping']} WHERE job_id = %s"
                self.cursor.execute(select_query, (job_id,))
                result = self.cursor.fetchone()
                mapping_id = result['id'] if result else None
            
            logger.info(f"任务映射记录插入/更新成功: job_id={job_id}, mapping_id={mapping_id}")
            return mapping_id
            
        except MySQLError as err:
            logger.error(f"插入任务映射记录失败: {err}")
            self.connection.rollback()
            return None
    
    def insert_file_details(self, mapping_id: int, files_info: List[Dict]) -> bool:
        """
        插入文件详情记录
        
        Args:
            mapping_id: 任务映射ID
            files_info: 文件信息列表
            
        Returns:
            bool: 成功返回True，失败返回False
        """
        if not self.connection or not self.connection.is_connected():
            if not self.connect():
                logger.error("无法插入文件详情，数据库未连接")
                return False
        
        if not files_info:
            return True
        
        try:
            # 先删除旧的文件详情记录
            delete_query = f"DELETE FROM {self.table_config['file_details']} WHERE mapping_id = %s"
            self.cursor.execute(delete_query, (mapping_id,))
            
            # 批量插入新的文件详情
            insert_query = f"""
            INSERT INTO {self.table_config['file_details']} 
            (mapping_id, file_name, file_type, file_size, file_path, download_success)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            params_list = []
            for file_info in files_info:
                params = (
                    mapping_id,
                    file_info.get('file_name', ''),
                    file_info.get('file_type', 'original'),
                    file_info.get('file_size', 0),
                    file_info.get('file_path', ''),
                    file_info.get('download_success', True)
                )
                params_list.append(params)
            
            self.cursor.executemany(insert_query, params_list)
            self.connection.commit()
            
            logger.info(f"文件详情记录插入成功: mapping_id={mapping_id}, 文件数量={len(files_info)}")
            return True
            
        except MySQLError as err:
            logger.error(f"插入文件详情记录失败: {err}")
            self.connection.rollback()
            return False
    
    def get_task_mapping_by_job_id(self, job_id: str) -> Optional[Dict]:
        """
        根据job_id获取任务映射记录
        
        Args:
            job_id: 任务Job ID
            
        Returns:
            Optional[Dict]: 任务映射记录，未找到返回None
        """
        if not self.connection or not self.connection.is_connected():
            if not self.connect():
                logger.error("无法查询记录，数据库未连接")
                return None
        
        try:
            query = f"""
            SELECT * FROM {self.table_config['task_mapping']} 
            WHERE job_id = %s
            """
            
            self.cursor.execute(query, (job_id,))
            result = self.cursor.fetchone()
            
            if result:
                # 转换时间格式
                if result.get('created_at'):
                    result['created_at'] = result['created_at'].isoformat()
                if result.get('updated_at'):
                    result['updated_at'] = result['updated_at'].isoformat()
            
            return result
            
        except MySQLError as err:
            logger.error(f"查询任务映射记录失败: {err}")
            return None
    
    def get_all_task_mappings(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        获取所有任务映射记录
        
        Args:
            limit: 限制数量
            offset: 偏移量
            
        Returns:
            List[Dict]: 任务映射记录列表
        """
        if not self.connection or not self.connection.is_connected():
            if not self.connect():
                logger.error("无法查询记录，数据库未连接")
                return []
        
        try:
            query = f"""
            SELECT tm.*, 
                   COUNT(fd.id) as file_details_count
            FROM {self.table_config['task_mapping']} tm
            LEFT JOIN {self.table_config['file_details']} fd ON tm.id = fd.mapping_id
            GROUP BY tm.id
            ORDER BY tm.updated_at DESC
            LIMIT %s OFFSET %s
            """
            
            self.cursor.execute(query, (limit, offset))
            results = self.cursor.fetchall()
            
            # 转换时间格式
            for result in results:
                if result.get('created_at'):
                    result['created_at'] = result['created_at'].isoformat()
                if result.get('updated_at'):
                    result['updated_at'] = result['updated_at'].isoformat()
            
            return results
            
        except MySQLError as err:
            logger.error(f"查询所有任务映射记录失败: {err}")
            return []
    
    def get_file_details_by_mapping_id(self, mapping_id: int) -> List[Dict]:
        """
        根据映射ID获取文件详情
        
        Args:
            mapping_id: 任务映射ID
            
        Returns:
            List[Dict]: 文件详情列表
        """
        if not self.connection or not self.connection.is_connected():
            if not self.connect():
                logger.error("无法查询文件详情，数据库未连接")
                return []
        
        try:
            query = f"""
            SELECT * FROM {self.table_config['file_details']} 
            WHERE mapping_id = %s
            ORDER BY file_type, file_name
            """
            
            self.cursor.execute(query, (mapping_id,))
            results = self.cursor.fetchall()
            
            # 转换时间格式
            for result in results:
                if result.get('created_at'):
                    result['created_at'] = result['created_at'].isoformat()
            
            return results
            
        except MySQLError as err:
            logger.error(f"查询文件详情失败: {err}")
            return []
    
    def test_connection(self) -> bool:
        """
        测试数据库连接
        
        Returns:
            bool: 连接成功返回True，否则返回False
        """
        success = self.connect()
        if success:
            self.disconnect()
        return success 