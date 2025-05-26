"""
数据库连接器模块，负责管理数据库连接和执行查询
"""
import logging
import time
from typing import Dict, List, Optional, Any, Union, Tuple

import mysql.connector
from mysql.connector import Error as MySQLError

# 导入数据库配置
from config.db_config import DB_CONFIG

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseConnector:
    """数据库连接器类，管理数据库连接和查询操作"""

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化数据库连接器
        
        Args:
            config: 数据库配置信息，默认使用DB_CONFIG
        """
        self.config = config or DB_CONFIG
        self.connection = None
        self.cursor = None
        
    def connect(self) -> bool:
        """
        建立数据库连接
        
        Returns:
            bool: 连接成功返回True，否则返回False
        """
        try:
            # 准备连接参数
            connection_params = {
                'host': self.config["host"],
                'user': self.config["user"],
                'password': self.config["password"],
                'port': self.config["port"],
            }
            
            # 如果配置中指定了数据库，添加到连接参数中
            if 'database' in self.config and self.config['database']:
                connection_params['database'] = self.config['database']
                
            # 如果指定了SSL CA证书
            if self.config.get("ssl_ca"):
                connection_params['ssl_ca'] = self.config["ssl_ca"]
            
            # 建立数据库连接
            self.connection = mysql.connector.connect(**connection_params)
            
            if self.connection.is_connected():
                db_info = self.connection.get_server_info()
                current_db = self.config.get('database', 'None')
                logger.info(f"已连接到MySQL服务器，版本: {db_info}，数据库: {current_db}")
                
                # 创建游标
                self.cursor = self.connection.cursor(dictionary=True)
                return True
                
        except MySQLError as err:
            logger.error(f"数据库连接失败: {err}")
            return False
    
    def disconnect(self) -> None:
        """关闭数据库连接"""
        if self.connection and self.connection.is_connected():
            if self.cursor:
                self.cursor.close()
            self.connection.close()
            logger.info("数据库连接已关闭")
    
    def execute_query(self, query: str, params: Optional[Union[Dict, Tuple, List]] = None) -> List[Dict]:
        """
        执行查询并返回结果
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            List[Dict]: 查询结果列表
        """
        result = []
        
        if not self.connection or not self.connection.is_connected():
            if not self.connect():
                logger.error("无法执行查询，数据库未连接")
                return result
        
        try:
            # 执行查询
            start_time = time.time()
            self.cursor.execute(query, params or ())
            execution_time = time.time() - start_time
            
            # 获取结果
            result = self.cursor.fetchall()
            logger.info(f"查询执行成功，获取 {len(result)} 条记录，耗时 {execution_time:.2f} 秒")
            
            return result
            
        except MySQLError as err:
            logger.error(f"查询执行失败: {err}")
            return result
    
    def execute_many(self, query: str, params_list: List[Union[Dict, Tuple, List]]) -> bool:
        """
        执行批量操作（插入或更新）
        
        Args:
            query: SQL语句模板
            params_list: 参数列表
            
        Returns:
            bool: 操作成功返回True，否则返回False
        """
        if not self.connection or not self.connection.is_connected():
            if not self.connect():
                logger.error("无法执行批量操作，数据库未连接")
                return False
        
        try:
            # 开始事务
            self.connection.start_transaction()
            
            # 执行批量操作
            start_time = time.time()
            self.cursor.executemany(query, params_list)
            self.connection.commit()
            
            execution_time = time.time() - start_time
            affected_rows = self.cursor.rowcount
            
            logger.info(f"批量操作成功，影响 {affected_rows} 行记录，耗时 {execution_time:.2f} 秒")
            return True
            
        except MySQLError as err:
            # 回滚事务
            self.connection.rollback()
            logger.error(f"批量操作失败: {err}")
            return False
    
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