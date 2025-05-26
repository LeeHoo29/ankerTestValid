"""
CSV文件处理模块
"""
import os
import logging
from typing import Dict, List, Optional, Any, Union

import pandas as pd

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CSVProcessor:
    """CSV文件处理类"""
    
    def __init__(self, file_path: str):
        """
        初始化CSV处理器
        
        Args:
            file_path: CSV文件路径
        """
        self.file_path = file_path
        self.data = None
        
    def read_file(self, **kwargs) -> bool:
        """
        读取CSV文件到DataFrame
        
        Args:
            **kwargs: 传递给pd.read_csv的参数
            
        Returns:
            bool: 读取成功返回True，否则返回False
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(self.file_path):
                logger.error(f"文件不存在: {self.file_path}")
                return False
                
            # 读取CSV文件
            default_params = {
                'encoding': 'utf-8',
                'na_values': ['', 'NA', 'N/A', '#N/A'],
                'low_memory': False
            }
            # 合并默认参数和用户提供的参数
            params = {**default_params, **kwargs}
            
            self.data = pd.read_csv(self.file_path, **params)
            logger.info(f"成功读取CSV文件: {self.file_path}, 包含 {len(self.data)} 行数据")
            return True
            
        except Exception as e:
            logger.error(f"读取CSV文件失败: {str(e)}")
            return False
    
    def get_data(self) -> Optional[pd.DataFrame]:
        """
        获取读取的数据
        
        Returns:
            pd.DataFrame: 数据帧对象，如果未读取文件则返回None
        """
        return self.data
    
    def filter_data(self, conditions: Dict) -> pd.DataFrame:
        """
        根据条件筛选数据
        
        Args:
            conditions: 筛选条件，格式为 {'列名': 值} 或 {'列名': [值1, 值2, ...]}
            
        Returns:
            pd.DataFrame: 筛选后的数据
        """
        if self.data is None:
            logger.warning("请先读取文件")
            return pd.DataFrame()
            
        filtered_data = self.data.copy()
        
        try:
            for column, value in conditions.items():
                if column not in filtered_data.columns:
                    logger.warning(f"列 {column} 不存在于数据中")
                    continue
                    
                if isinstance(value, list):
                    filtered_data = filtered_data[filtered_data[column].isin(value)]
                else:
                    filtered_data = filtered_data[filtered_data[column] == value]
                    
            logger.info(f"筛选后得到 {len(filtered_data)} 行数据")
            return filtered_data
            
        except Exception as e:
            logger.error(f"筛选数据时出错: {str(e)}")
            return pd.DataFrame()
    
    def save_to_csv(self, output_path: str, data: Optional[pd.DataFrame] = None, **kwargs) -> bool:
        """
        保存数据到CSV文件
        
        Args:
            output_path: 输出文件路径
            data: 要保存的数据，默认为当前数据
            **kwargs: 传递给to_csv的参数
            
        Returns:
            bool: 保存成功返回True，否则返回False
        """
        try:
            save_data = data if data is not None else self.data
            
            if save_data is None or len(save_data) == 0:
                logger.warning("没有数据可保存")
                return False
                
            # 确保输出目录存在
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            
            # 设置默认参数
            default_params = {
                'index': False,
                'encoding': 'utf-8'
            }
            # 合并默认参数和用户提供的参数
            params = {**default_params, **kwargs}
            
            save_data.to_csv(output_path, **params)
            logger.info(f"数据已保存至: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存数据失败: {str(e)}")
            return False 