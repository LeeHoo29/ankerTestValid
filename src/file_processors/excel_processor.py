"""
Excel文件处理模块
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


class ExcelProcessor:
    """Excel文件处理类"""
    
    def __init__(self, file_path: str):
        """
        初始化Excel处理器
        
        Args:
            file_path: Excel文件路径
        """
        self.file_path = file_path
        self.data = {}  # 用字典存储多个工作表数据
        self.current_sheet = None  # 当前活动工作表
        
    def read_file_chunked(self, sheet_name: Optional[Union[str, int]] = 0, nrows: Optional[int] = None, skiprows: Optional[int] = None, **kwargs) -> bool:
        """
        优化读取Excel文件，支持大文件处理
        
        Args:
            sheet_name: 要读取的工作表名称或索引，默认为第一个工作表
            nrows: 限制读取的行数
            skiprows: 跳过的行数（从文件开头算起）
            **kwargs: 传递给pd.read_excel的其他参数
            
        Returns:
            bool: 读取成功返回True，否则返回False
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(self.file_path):
                logger.error(f"文件不存在: {self.file_path}")
                return False
                
            # 设置优化参数
            default_params = {
                'na_values': ['', 'NA', 'N/A', '#N/A'],
                'engine': 'openpyxl',  # 明确指定引擎
            }
            
            # 如果指定了行数限制，添加nrows参数
            if nrows is not None:
                default_params['nrows'] = nrows
                
            # 如果指定了跳过行数，添加skiprows参数  
            if skiprows is not None:
                default_params['skiprows'] = skiprows
                
            # 合并默认参数和用户提供的参数
            params = {**default_params, **kwargs}
            
            logger.info(f"开始读取Excel文件: {self.file_path}")
            if nrows:
                logger.info(f"限制读取行数: {nrows}")
            if skiprows:
                logger.info(f"跳过行数: {skiprows}")
                
            # 读取指定工作表
            result = pd.read_excel(self.file_path, sheet_name=sheet_name, **params)
            
            # 如果是单个工作表
            if isinstance(result, pd.DataFrame):
                sheet_key = sheet_name if sheet_name is not None else 0
                self.data = {sheet_key: result}
                self.current_sheet = sheet_key
                logger.info(f"成功读取工作表: {sheet_key}, 包含 {len(result)} 行数据, {len(result.columns)} 列")
            else:
                # 如果是多个工作表（字典）
                self.data = result
                sheet_count = len(result)
                total_rows = sum(len(df) for df in result.values())
                logger.info(f"成功读取Excel文件，包含 {sheet_count} 个工作表, 共 {total_rows} 行数据")
                
                # 设置第一个工作表为当前工作表
                if sheet_count > 0:
                    self.current_sheet = list(result.keys())[0]
            
            return True
            
        except Exception as e:
            logger.error(f"读取Excel文件失败: {str(e)}")
            return False
    
    def preview_file_info(self, sheet_name: Optional[Union[str, int]] = 0) -> Dict[str, Any]:
        """
        预览Excel文件信息（不读取全部数据）
        
        Args:
            sheet_name: 工作表名称或索引
            
        Returns:
            Dict: 包含文件信息的字典
        """
        try:
            # 只读取第一行来获取列信息
            header_df = pd.read_excel(self.file_path, sheet_name=sheet_name, nrows=1, engine='openpyxl')
            
            # 获取工作表名称列表
            xl_file = pd.ExcelFile(self.file_path, engine='openpyxl')
            sheet_names = xl_file.sheet_names
            
            file_info = {
                'file_path': self.file_path,
                'file_size': f"{os.path.getsize(self.file_path) / 1024 / 1024:.2f} MB",
                'sheet_names': sheet_names,
                'columns': list(header_df.columns),
                'column_count': len(header_df.columns)
            }
            
            xl_file.close()
            
            logger.info(f"文件预览信息: {file_info}")
            return file_info
            
        except Exception as e:
            logger.error(f"预览文件信息失败: {str(e)}")
            return {}

    def read_file(self, sheet_name: Optional[Union[str, int, List]] = None, **kwargs) -> bool:
        """
        读取Excel文件到DataFrame
        
        Args:
            sheet_name: 要读取的工作表名称、索引或列表，默认读取所有工作表
            **kwargs: 传递给pd.read_excel的参数
            
        Returns:
            bool: 读取成功返回True，否则返回False
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(self.file_path):
                logger.error(f"文件不存在: {self.file_path}")
                return False
                
            # 读取Excel文件
            default_params = {
                'na_values': ['', 'NA', 'N/A', '#N/A'],
            }
            # 合并默认参数和用户提供的参数
            params = {**default_params, **kwargs}
            
            # 如果未指定sheet_name，则读取所有工作表
            if sheet_name is None:
                result = pd.read_excel(self.file_path, sheet_name=None, **params)
                self.data = result
                sheet_count = len(result)
                total_rows = sum(len(df) for df in result.values())
                logger.info(f"成功读取Excel文件: {self.file_path}, 包含 {sheet_count} 个工作表, 共 {total_rows} 行数据")
                
                # 设置第一个工作表为当前工作表
                if sheet_count > 0:
                    self.current_sheet = list(result.keys())[0]
            else:
                # 读取指定的工作表
                result = pd.read_excel(self.file_path, sheet_name=sheet_name, **params)
                
                if isinstance(result, dict):
                    # 如果结果是字典（多个工作表）
                    self.data = result
                    sheet_count = len(result)
                    total_rows = sum(len(df) for df in result.values())
                    logger.info(f"成功读取Excel文件: {self.file_path}, 包含 {sheet_count} 个工作表, 共 {total_rows} 行数据")
                    
                    # 设置第一个工作表为当前工作表
                    if sheet_count > 0:
                        self.current_sheet = list(result.keys())[0]
                else:
                    # 如果结果是单个DataFrame（单个工作表）
                    if isinstance(sheet_name, (str, int)):
                        self.data = {sheet_name: result}
                        self.current_sheet = sheet_name
                        logger.info(f"成功读取Excel工作表: {sheet_name}, 包含 {len(result)} 行数据")
                    else:
                        logger.error(f"无法处理的sheet_name类型: {type(sheet_name)}")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"读取Excel文件失败: {str(e)}")
            return False
    
    def get_sheet_names(self) -> List[str]:
        """
        获取工作表名称列表
        
        Returns:
            List[str]: 工作表名称列表
        """
        return list(self.data.keys())
    
    def set_active_sheet(self, sheet_name: Union[str, int]) -> bool:
        """
        设置当前活动工作表
        
        Args:
            sheet_name: 工作表名称或索引
            
        Returns:
            bool: 设置成功返回True，否则返回False
        """
        if isinstance(sheet_name, int):
            # 如果sheet_name是索引，转换为对应的表名
            sheet_names = self.get_sheet_names()
            if 0 <= sheet_name < len(sheet_names):
                sheet_name = sheet_names[sheet_name]
            else:
                logger.error(f"工作表索引超出范围: {sheet_name}")
                return False
                
        if sheet_name in self.data:
            self.current_sheet = sheet_name
            logger.info(f"当前活动工作表已设置为: {sheet_name}")
            return True
        else:
            logger.error(f"工作表不存在: {sheet_name}")
            return False
    
    def get_data(self, sheet_name: Optional[str] = None) -> Optional[pd.DataFrame]:
        """
        获取指定工作表的数据
        
        Args:
            sheet_name: 工作表名称，默认为当前活动工作表
            
        Returns:
            pd.DataFrame: 工作表数据，如果工作表不存在则返回None
        """
        target_sheet = sheet_name or self.current_sheet
        
        if target_sheet is None:
            logger.warning("未设置活动工作表")
            return None
            
        if target_sheet in self.data:
            return self.data[target_sheet]
        else:
            logger.warning(f"工作表不存在: {target_sheet}")
            return None
    
    def filter_data(self, conditions: Dict, sheet_name: Optional[str] = None) -> pd.DataFrame:
        """
        根据条件筛选工作表数据
        
        Args:
            conditions: 筛选条件，格式为 {'列名': 值} 或 {'列名': [值1, 值2, ...]}
            sheet_name: 工作表名称，默认为当前活动工作表
            
        Returns:
            pd.DataFrame: 筛选后的数据
        """
        data = self.get_data(sheet_name)
        
        if data is None:
            return pd.DataFrame()
            
        filtered_data = data.copy()
        
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
    
    def save_to_excel(self, output_path: str, data: Optional[Dict[str, pd.DataFrame]] = None, **kwargs) -> bool:
        """
        保存数据到Excel文件
        
        Args:
            output_path: 输出文件路径
            data: 要保存的数据字典 {工作表名: DataFrame}，默认为当前数据
            **kwargs: 传递给ExcelWriter的参数
            
        Returns:
            bool: 保存成功返回True，否则返回False
        """
        try:
            save_data = data if data is not None else self.data
            
            if not save_data:
                logger.warning("没有数据可保存")
                return False
                
            # 确保输出目录存在
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            
            # 设置默认参数
            default_params = {
                'engine': 'openpyxl'
            }
            # 合并默认参数和用户提供的参数
            params = {**default_params, **kwargs}
            
            with pd.ExcelWriter(output_path, **params) as writer:
                for sheet_name, df in save_data.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    
            logger.info(f"数据已保存至: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存数据失败: {str(e)}")
            return False
    
    def save_sheet_to_csv(self, output_path: str, sheet_name: Optional[str] = None, data: Optional[pd.DataFrame] = None, **kwargs) -> bool:
        """
        将工作表数据保存为CSV文件
        
        Args:
            output_path: 输出CSV文件路径
            sheet_name: 工作表名称，默认为当前活动工作表
            data: 要保存的数据，优先级高于sheet_name
            **kwargs: 传递给to_csv的参数
            
        Returns:
            bool: 保存成功返回True，否则返回False
        """
        try:
            if data is not None:
                save_data = data
            else:
                save_data = self.get_data(sheet_name)
                
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
    
    def filter_null_values(self, column_name: str, nrows: Optional[int] = None, sheet_name: Optional[str] = None) -> pd.DataFrame:
        """
        筛选指定列为空值的数据
        
        Args:
            column_name: 要筛选的列名
            nrows: 限制返回的行数
            sheet_name: 工作表名称，默认为当前活动工作表
            
        Returns:
            pd.DataFrame: 筛选后的数据
        """
        data = self.get_data(sheet_name)
        
        if data is None:
            logger.warning("没有数据可筛选")
            return pd.DataFrame()
            
        try:
            # 检查列是否存在
            if column_name not in data.columns:
                logger.error(f"列 '{column_name}' 不存在于数据中")
                logger.info(f"可用的列名: {', '.join(data.columns)}")
                return pd.DataFrame()
                
            # 筛选指定列为空的数据
            # 考虑多种空值情况：NaN, None, 空字符串, 只包含空格的字符串
            null_condition = (
                data[column_name].isnull() | 
                (data[column_name] == '') | 
                (data[column_name].astype(str).str.strip() == '') |
                (data[column_name].astype(str).str.lower() == 'nan')
            )
            
            filtered_data = data[null_condition].copy()
            
            # 如果指定了行数限制
            if nrows is not None and nrows > 0:
                filtered_data = filtered_data.head(nrows)
                
            logger.info(f"筛选出列 '{column_name}' 为空的数据: {len(filtered_data)} 行")
            return filtered_data
            
        except Exception as e:
            logger.error(f"筛选数据时出错: {str(e)}")
            return pd.DataFrame()
    
    def analyze_column_values(self, column_name: str, sheet_name: Optional[str] = None) -> Dict[str, Any]:
        """
        分析指定列的值分布情况
        
        Args:
            column_name: 要分析的列名
            sheet_name: 工作表名称，默认为当前活动工作表
            
        Returns:
            Dict: 包含列分析信息的字典
        """
        data = self.get_data(sheet_name)
        
        if data is None:
            return {}
            
        if column_name not in data.columns:
            logger.error(f"列 '{column_name}' 不存在于数据中")
            return {}
            
        try:
            total_count = len(data)
            null_count = data[column_name].isnull().sum()
            empty_string_count = (data[column_name] == '').sum()
            whitespace_count = (data[column_name].astype(str).str.strip() == '').sum()
            
            analysis = {
                'column_name': column_name,
                'total_count': total_count,
                'null_count': int(null_count),
                'empty_string_count': int(empty_string_count),
                'whitespace_count': int(whitespace_count),
                'non_null_count': int(total_count - null_count),
                'unique_values': data[column_name].nunique(),
                'value_counts': data[column_name].value_counts().head(10).to_dict()
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"分析列数据时出错: {str(e)}")
            return {} 