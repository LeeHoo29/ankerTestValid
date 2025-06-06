#!/usr/bin/env python3
"""
Shulex-Anker数据验证工具主程序入口
"""
import os
import sys
import logging
import argparse
import json
import requests
from pathlib import Path
from typing import Dict, List, Optional, Any

import pandas as pd
from tabulate import tabulate

# 添加项目根目录到系统路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 导入项目模块
from src.db.connector import DatabaseConnector
from src.file_processors.csv_processor import CSVProcessor
from src.file_processors.excel_processor import ExcelProcessor
from config.db_config import REPARSER_API_CONFIG, CRAWLER_API_CONFIG

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_db_connection() -> bool:
    """
    测试数据库连接
    
    Returns:
        bool: 连接成功返回True，否则返回False
    """
    logger.info("测试数据库连接...")
    db = DatabaseConnector()
    result = db.test_connection()
    
    if result:
        logger.info("数据库连接测试成功！")
    else:
        logger.error("数据库连接测试失败！")
        
    return result


def read_excel_chunked(file_path: str, nrows: int = 10, skiprows: int = 0, sheet_name: Optional[str] = None, output_path: Optional[str] = None) -> Optional[pd.DataFrame]:
    """
    分块读取大Excel文件的前N行数据
    
    Args:
        file_path: Excel文件路径
        nrows: 读取的行数，默认为10
        skiprows: 跳过的行数，默认为0
        sheet_name: 工作表名称，默认为第一个工作表
        output_path: 输出文件路径
        
    Returns:
        pd.DataFrame: 读取的数据，失败返回None
    """
    if not os.path.exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        return None
        
    processor = ExcelProcessor(file_path)
    
    try:
        # 首先预览文件信息
        print("=== Excel文件预览信息 ===")
        file_info = processor.preview_file_info(sheet_name=sheet_name or 0)
        if file_info:
            print(f"文件路径: {file_info['file_path']}")
            print(f"文件大小: {file_info['file_size']}")
            print(f"工作表列表: {', '.join(file_info['sheet_names'])}")
            print(f"列数: {file_info['column_count']}")
            print(f"列名: {', '.join(file_info['columns'])}")
        
        # 使用分块读取方法
        print(f"\n=== 开始读取前 {nrows} 行数据 ===")
        success = processor.read_file_chunked(
            sheet_name=sheet_name or 0,
            nrows=nrows,
            skiprows=skiprows
        )
        
        if not success:
            return None
            
        # 获取读取的数据
        data = processor.get_data()
        if data is not None and len(data) > 0:
            print(f"\n=== 数据摘要 ===")
            print(f"实际读取行数: {len(data)}")
            print(f"列数: {len(data.columns)}")
            
            print(f"\n=== 前 {min(len(data), 10)} 行数据预览 ===")
            print(tabulate(data.head(10), headers='keys', tablefmt='psql', showindex=True))
            
            # 显示数据类型信息
            print(f"\n=== 列数据类型信息 ===")
            dtype_info = pd.DataFrame({
                '列名': data.columns,
                '数据类型': data.dtypes.astype(str),
                '非空值数量': data.count(),
                '空值数量': data.isnull().sum()
            })
            print(tabulate(dtype_info, headers='keys', tablefmt='psql', showindex=False))
            
            # 保存数据
            if output_path:
                if output_path.endswith('.csv'):
                    processor.save_sheet_to_csv(output_path, data=data)
                else:
                    processor.save_to_excel(output_path, data={processor.current_sheet: data})
                    
            return data
        else:
            print("未读取到数据")
            return None
            
    except Exception as e:
        logger.error(f"处理Excel文件时出错: {str(e)}")
        return None


def process_file(file_path: str, file_type: str = None, output_path: Optional[str] = None) -> Optional[pd.DataFrame]:
    """
    处理文件（CSV或Excel）
    
    Args:
        file_path: 文件路径
        file_type: 文件类型（'csv'或'excel'），如果为None则根据文件扩展名判断
        output_path: 输出文件路径，如果提供则将处理结果保存到该文件
        
    Returns:
        pd.DataFrame: 处理后的数据，如果失败则返回None
    """
    if not os.path.exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        return None
        
    # 如果未指定文件类型，根据扩展名判断
    if file_type is None:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.csv']:
            file_type = 'csv'
        elif ext in ['.xlsx', '.xls', '.xlsm']:
            file_type = 'excel'
        else:
            logger.error(f"不支持的文件类型: {ext}")
            return None
    
    # 处理CSV文件
    if file_type.lower() == 'csv':
        processor = CSVProcessor(file_path)
        if not processor.read_file():
            return None
            
        data = processor.get_data()
        logger.info(f"CSV文件处理完成，共 {len(data)} 行数据")
        
        # 如果指定了输出路径，保存处理结果
        if output_path:
            processor.save_to_csv(output_path)
            
        return data
        
    # 处理Excel文件
    elif file_type.lower() == 'excel':
        processor = ExcelProcessor(file_path)
        if not processor.read_file():
            return None
            
        sheet_names = processor.get_sheet_names()
        logger.info(f"Excel文件处理完成，包含工作表: {', '.join(sheet_names)}")
        
        data = processor.get_data()  # 获取第一个工作表数据
        
        # 如果指定了输出路径，保存处理结果
        if output_path:
            if output_path.endswith('.csv'):
                processor.save_sheet_to_csv(output_path)
            else:
                processor.save_to_excel(output_path)
                
        return data
        
    else:
        logger.error(f"不支持的文件类型: {file_type}")
        return None


def validate_data(file_path: str, output_path: Optional[str] = None) -> bool:
    """
    验证数据文件与数据库中的数据
    
    Args:
        file_path: 文件路径
        output_path: 输出文件路径
        
    Returns:
        bool: 验证成功返回True，否则返回False
    """
    # 处理文件
    file_data = process_file(file_path)
    if file_data is None:
        return False
        
    # 显示文件摘要信息
    print("\n文件摘要信息:")
    print(f"- 行数: {len(file_data)}")
    print(f"- 列数: {len(file_data.columns)}")
    print(f"- 列名: {', '.join(file_data.columns)}")
    
    # 连接数据库
    db = DatabaseConnector()
    if not db.connect():
        return False
        
    try:
        # 获取数据库信息
        db_info = db.execute_query("SELECT database() as db_name")
        if db_info:
            print(f"\n当前数据库: {db_info[0]['db_name']}")
        
        # 获取数据库表信息
        tables = db.execute_query("SHOW TABLES")
        if tables:
            print("\n数据库表列表:")
            for table in tables:
                table_name = list(table.values())[0]
                print(f"- {table_name}")
        
        # 提示用户输入SQL查询
        print("\n请输入要执行的SQL查询来验证数据 (留空跳过):")
        sql_query = input("> ")
        
        if sql_query:
            result = db.execute_query(sql_query)
            if result:
                # 将结果转换为DataFrame并显示
                result_df = pd.DataFrame(result)
                print("\n查询结果 (前10行):")
                print(tabulate(result_df.head(10), headers='keys', tablefmt='psql'))
                
                # 保存结果
                if output_path:
                    result_df.to_csv(output_path, index=False)
                    print(f"\n查询结果已保存至: {output_path}")
                    
                return True
            else:
                print("查询未返回结果")
                return False
                
        return True
        
    finally:
        # 关闭数据库连接
        db.disconnect()


def filter_null_column(file_path: str, column_name: str, nrows: int = 10, sheet_name: Optional[str] = None, output_path: Optional[str] = None, prepare_db_query: bool = False) -> Optional[pd.DataFrame]:
    """
    筛选指定列为空的数据
    
    Args:
        file_path: Excel文件路径
        column_name: 要筛选的列名
        nrows: 返回的行数，默认为10
        sheet_name: 工作表名称，默认为第一个工作表
        output_path: 输出文件路径
        prepare_db_query: 是否准备数据库查询信息
        
    Returns:
        pd.DataFrame: 筛选后的数据，失败返回None
    """
    if not os.path.exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        return None
        
    processor = ExcelProcessor(file_path)
    
    try:
        # 首先读取足够的数据以进行筛选（读取更多行以确保能找到足够的空值记录）
        print("=== 正在读取Excel文件并分析列信息 ===")
        
        # 先读取一部分数据进行分析
        success = processor.read_file_chunked(
            sheet_name=sheet_name or 0,
            nrows=1000  # 先读取1000行进行分析
        )
        
        if not success:
            return None
            
        # 分析指定列的情况
        print(f"\n=== 分析列 '{column_name}' 的数据分布 ===")
        analysis = processor.analyze_column_values(column_name)
        if analysis:
            print(f"总行数: {analysis['total_count']}")
            print(f"空值数量: {analysis['null_count']}")
            print(f"空字符串数量: {analysis['empty_string_count']}")
            print(f"非空值数量: {analysis['non_null_count']}")
            print(f"唯一值数量: {analysis['unique_values']}")
        
        # 如果1000行中空值数量不够，需要读取更多数据
        if analysis and analysis['null_count'] < nrows:
            print(f"\n当前读取的数据中空值数量({analysis['null_count']})不足{nrows}条，尝试读取更多数据...")
            success = processor.read_file_chunked(
                sheet_name=sheet_name or 0,
                nrows=5000  # 读取更多数据
            )
            if not success:
                print("读取更多数据失败，使用当前已读取的数据")
        
        # 筛选空值数据
        print(f"\n=== 筛选 '{column_name}' 列为空的前 {nrows} 条数据 ===")
        filtered_data = processor.filter_null_values(column_name, nrows)
        
        if filtered_data is not None and len(filtered_data) > 0:
            print(f"\n=== 筛选结果摘要 ===")
            print(f"找到 {len(filtered_data)} 条 '{column_name}' 为空的记录")
            
            print(f"\n=== 筛选出的数据预览 ===")
            print(tabulate(filtered_data, headers='keys', tablefmt='psql', showindex=True))
            
            # 为数据库查询准备关键字段信息
            if prepare_db_query:
                print(f"\n=== 数据库查询准备信息 ===")
                
                # 显示可能用于数据库查询的关键列
                key_columns = []
                for col in filtered_data.columns:
                    col_lower = col.lower()
                    if any(keyword in col_lower for keyword in ['id', 'number', 'code', '编号', '订单', 'order', 'listing']):
                        key_columns.append(col)
                
                if key_columns:
                    print(f"建议用于数据库查询的关键列: {', '.join(key_columns)}")
                    
                    for key_col in key_columns:
                        unique_values = filtered_data[key_col].dropna().unique()
                        if len(unique_values) > 0:
                            print(f"\n{key_col} 的唯一值 (前10个):")
                            for i, value in enumerate(unique_values[:10]):
                                print(f"  {i+1}. {value}")
                            
                            # 生成SQL查询示例
                            if len(unique_values) <= 5:
                                values_str = "', '".join(str(v) for v in unique_values)
                                print(f"\n示例SQL查询 (基于 {key_col}):")
                                print(f"SELECT * FROM your_table WHERE {key_col} IN ('{values_str}');")
                else:
                    print("未找到明显的关键列，显示所有列信息供参考:")
                    for col in filtered_data.columns:
                        non_null_count = filtered_data[col].count()
                        if non_null_count > 0:
                            sample_values = filtered_data[col].dropna().head(3).tolist()
                            print(f"  {col}: {non_null_count}个非空值, 示例: {sample_values}")
            
            # 保存筛选结果
            if output_path:
                if output_path.endswith('.csv'):
                    processor.save_sheet_to_csv(output_path, data=filtered_data)
                else:
                    processor.save_to_excel(output_path, data={f"filtered_{column_name}": filtered_data})
                    
            return filtered_data
        else:
            print(f"未找到 '{column_name}' 列为空的数据")
            return None
            
    except Exception as e:
        logger.error(f"筛选数据时出错: {str(e)}")
        return None


def analyze_tasks_with_db(file_path: str, column_name: str, nrows: int = 10, sheet_name: Optional[str] = None, output_path: Optional[str] = None) -> Optional[pd.DataFrame]:
    """
    分析任务数据并查询数据库进行问题诊断
    
    Args:
        file_path: Excel文件路径
        column_name: 要筛选的列名（如"解决进度"）
        nrows: 分析的任务数量，默认为10
        sheet_name: 工作表名称，默认为第一个工作表
        output_path: 输出分析结果的文件路径
        
    Returns:
        pd.DataFrame: 分析结果，失败返回None
    """
    import json
    
    if not os.path.exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        return None
        
    # 第一步：筛选空值数据
    print("=" * 60)
    print("第一步：筛选待处理任务")
    print("=" * 60)
    
    processor = ExcelProcessor(file_path)
    
    try:
        # 读取数据并筛选
        success = processor.read_file_chunked(
            sheet_name=sheet_name or 0,
            nrows=5000  # 读取足够的数据确保能找到空值记录
        )
        
        if not success:
            return None
            
        # 筛选空值数据
        filtered_data = processor.filter_null_values(column_name, nrows)
        
        if filtered_data is None or len(filtered_data) == 0:
            print(f"未找到 '{column_name}' 列为空的数据")
            return None
            
        print(f"找到 {len(filtered_data)} 条待处理任务")
        
        # 检查是否有shulex_ssn列
        if 'shulex_ssn' not in filtered_data.columns:
            logger.error("数据中缺少 'shulex_ssn' 列")
            return None
            
        # 在开始数据库查询前，标记所有筛选出的任务为"解决中"
        print(f"\n标记 {len(filtered_data)} 个任务状态为'解决中'...")
        
        # 获取完整数据进行更新
        full_data = processor.get_data()
        if full_data is not None and column_name in full_data.columns:
            # 更新筛选出的任务的状态
            for index in filtered_data.index:
                if index < len(full_data):
                    full_data.loc[index, column_name] = "解决中"
            
            # 保存更新后的文件
            updated_file_path = file_path.replace('.xlsx', '_已更新.xlsx')
            processor.save_to_excel(updated_file_path, data={processor.current_sheet: full_data})
            print(f"已更新文件保存至: {updated_file_path}")
        
        # 第二步：连接数据库
        print("\n" + "=" * 60)
        print("第二步：连接数据库进行查询分析")
        print("=" * 60)
        
        # 创建数据库连接，指定数据库
        from config.db_config import DB_CONFIG
        db_config = DB_CONFIG.copy()
        db_config['database'] = 'shulex_collector_prod'
        
        db = DatabaseConnector(db_config)
        if not db.connect():
            logger.error("无法连接到数据库 shulex_collector_prod")
            return None
            
        try:
            # 准备分析结果
            analysis_results = []
            
            # 定义要查询的表
            tables_to_check = ['log_a', 'log_b', 'log_c', 'log_d']
            
            print(f"开始分析 {len(filtered_data)} 个任务...")
            
            for index, row in filtered_data.iterrows():
                shulex_ssn = row['shulex_ssn']
                task_id = row['id']
                
                print(f"\n--- 分析任务 {task_id} (SSN: {shulex_ssn}) ---")
                
                # 初始化结果记录
                result_record = {
                    'id': task_id,
                    'shulex_ssn': shulex_ssn,
                    'asin': row.get('asin', ''),
                    'market': row.get('market', ''),
                    'type': row.get('type', ''),
                    'status': row.get('status', ''),
                    'task_id': '',  # 新增列存储从log中提取的ext_ssn
                    '问题分析结果': '',
                    '问题直接原因': '',
                    'error_details': '',
                    'error_msg': ''  # 新增列存储完整错误信息
                }
                
                # 查询各个表
                table_results = {}
                total_records = 0
                
                for table_name in tables_to_check:
                    query = f"SELECT * FROM {table_name} WHERE req_ssn = %s"
                    try:
                        records = db.execute_query(query, (shulex_ssn,))
                        record_count = len(records) if records else 0
                        table_results[table_name] = {
                            'count': record_count,
                            'records': records
                        }
                        total_records += record_count
                        print(f"  {table_name}: {record_count} 条记录")
                        
                    except Exception as e:
                        logger.error(f"查询表 {table_name} 失败: {str(e)}")
                        table_results[table_name] = {
                            'count': 0,
                            'records': []
                        }
                
                # 分析查询结果
                if total_records == 0:
                    result_record['问题分析结果'] = "所有日志表中都没有找到相关记录"
                    result_record['问题直接原因'] = "查询的结果为空"
                    print(f"  ❌ 问题诊断: 查询的结果为空")
                    
                elif total_records == 1:
                    # 找到唯一记录，进行详细分析
                    found_table = None
                    found_record = None
                    for table_name, table_result in table_results.items():
                        if table_result['count'] == 1:
                            found_table = table_name
                            found_record = table_result['records'][0]
                            break
                    
                    print(f"  ✅ 找到唯一记录在表: {found_table}")
                    
                    if found_record:
                        # 提取task_id (ext_ssn)
                        ext_ssn = found_record.get('ext_ssn', '')
                        result_record['task_id'] = ext_ssn
                        
                        # 详细分析记录
                        print("  📋 基本信息:")
                        print(f"    ID: {found_record.get('id')}")
                        print(f"    Task ID (ext_ssn): {ext_ssn}")
                        print(f"    State: {found_record.get('state')}")
                        print(f"    Created: {found_record.get('created_at')}")
                        print(f"    Completed: {found_record.get('completed_at')}")
                        
                        # 检查state是否为FAILURE
                        if found_record.get('state') == 'FAILURE':
                            print("  ❌ 任务状态: FAILURE")
                            
                            # 检查analysis_response是否不为空
                            analysis_response = found_record.get('analysis_response')
                            if analysis_response:
                                print("  📄 分析响应存在，开始解析...")
                                
                                try:
                                    # 解析JSON并格式化打印
                                    if isinstance(analysis_response, str):
                                        response_data = json.loads(analysis_response)
                                    else:
                                        response_data = analysis_response
                                    
                                    print("  📊 Analysis Response (格式化):")
                                    print(json.dumps(response_data, indent=2, ensure_ascii=False))
                                    
                                    # 判断code
                                    code = response_data.get('code')
                                    meta = response_data.get('meta', {})
                                    error_msg = meta.get('error_msg', '')
                                    
                                    print(f"  🔍 Response Code: {code}")
                                    
                                    if code != 500:
                                        print(f"  ⚠️  Code不等于500，Error Message:")
                                        print(f"     {error_msg}")
                                        result_record['问题分析结果'] = f"在 {found_table} 中找到记录，状态FAILURE，Code: {code}"
                                        result_record['问题直接原因'] = f"Code不等于500: {error_msg[:100]}..."
                                        result_record['error_details'] = json.dumps(response_data, ensure_ascii=False)
                                        result_record['error_msg'] = error_msg
                                    else:
                                        print(f"  🔴 Code等于500，系统错误:")
                                        # 提取关键错误信息
                                        if error_msg:
                                            # 提取最关键的错误行
                                            error_lines = error_msg.split('\n')
                                            key_error = ""
                                            for line in error_lines:
                                                if any(keyword in line for keyword in ['Error:', 'Exception:', 'IndexError:', 'KeyError:']):
                                                    key_error = line.strip()
                                                    break
                                            
                                            print(f"     关键错误: {key_error}")
                                            result_record['问题分析结果'] = f"在 {found_table} 中找到记录，状态FAILURE，Code: 500"
                                            result_record['问题直接原因'] = f"系统错误: {key_error[:100]}..."
                                            result_record['error_details'] = json.dumps(response_data, ensure_ascii=False)
                                            result_record['error_msg'] = error_msg
                                        else:
                                            result_record['问题分析结果'] = f"在 {found_table} 中找到记录，状态FAILURE，Code: 500"
                                            result_record['问题直接原因'] = "系统错误，但无详细错误信息"
                                            result_record['error_details'] = json.dumps(response_data, ensure_ascii=False)
                                            result_record['error_msg'] = ""
                                    
                                except json.JSONDecodeError as e:
                                    print(f"  ❌ JSON解析失败: {e}")
                                    print(f"  原始数据: {analysis_response}")
                                    result_record['问题分析结果'] = f"在 {found_table} 中找到记录，状态FAILURE，但JSON解析失败"
                                    result_record['问题直接原因'] = "JSON解析错误"
                                    result_record['error_details'] = ""
                                    result_record['error_msg'] = ""
                                    
                            else:
                                print("  📭 Analysis Response 为空")
                                result_record['问题分析结果'] = f"在 {found_table} 中找到记录，状态FAILURE，但无分析响应"
                                result_record['问题直接原因'] = "FAILURE状态但无分析响应"
                                result_record['error_details'] = ""
                                result_record['error_msg'] = ""
                                
                        else:
                            print(f"  ✅ 任务状态: {found_record.get('state', 'Unknown')}")
                            result_record['问题分析结果'] = f"在 {found_table} 中找到记录，状态正常"
                            result_record['问题直接原因'] = "状态正常"
                            result_record['error_details'] = ""
                            result_record['error_msg'] = ""
                            
                else:
                    result_record['问题分析结果'] = f"找到 {total_records} 条记录，分布在多个表中"
                    result_record['问题直接原因'] = "任务数量错误"
                    print(f"  ❌ 问题诊断: 任务数量错误 (找到 {total_records} 条记录)")
                    
                    # 尝试从第一条记录中提取task_id
                    first_record = None
                    for table_name, table_result in table_results.items():
                        if table_result['count'] > 0 and table_result['records']:
                            first_record = table_result['records'][0]
                            break
                    
                    if first_record:
                        ext_ssn = first_record.get('ext_ssn', '')
                        result_record['task_id'] = ext_ssn
                        print(f"    提取到的Task ID (ext_ssn): {ext_ssn}")
                    
                    # 显示各表的记录分布
                    for table_name, table_result in table_results.items():
                        if table_result['count'] > 0:
                            print(f"    {table_name}: {table_result['count']} 条记录")
                
                analysis_results.append(result_record)
            
            # 第三步：生成分析报告
            print("\n" + "=" * 60)
            print("第三步：分析结果汇总")
            print("=" * 60)
            
            # 转换为DataFrame
            results_df = pd.DataFrame(analysis_results)
            
            # 统计问题类型
            problem_summary = results_df['问题直接原因'].value_counts()
            print("\n问题类型统计:")
            for problem_type, count in problem_summary.items():
                print(f"  {problem_type}: {count} 个任务")
            
            # 显示详细结果表
            print(f"\n详细分析结果:")
            display_columns = ['id', 'shulex_ssn', 'task_id', 'asin', 'market', '问题分析结果', '问题直接原因']
            print(tabulate(results_df[display_columns], headers='keys', tablefmt='psql', showindex=False))
            
            # 保存结果
            if output_path:
                # 将原始数据和分析结果合并
                final_results = filtered_data.copy()
                for i, result in enumerate(analysis_results):
                    final_results.loc[final_results.index[i], '解决进度'] = "已分析"
                    final_results.loc[final_results.index[i], 'task_id'] = result['task_id']
                    final_results.loc[final_results.index[i], '问题分析结果'] = result['问题分析结果']
                    final_results.loc[final_results.index[i], '问题直接原因'] = result['问题直接原因']
                    final_results.loc[final_results.index[i], 'error_msg'] = result['error_msg']
                
                if output_path.endswith('.csv'):
                    final_results.to_csv(output_path, index=False, encoding='utf-8')
                else:
                    processor.save_to_excel(output_path, data={"分析结果": final_results})
                
                print(f"\n分析结果已保存至: {output_path}")
            
            return results_df
            
        finally:
            # 关闭数据库连接
            db.disconnect()
            
    except Exception as e:
        logger.error(f"分析过程中出错: {str(e)}")
        return None


def resubmit_parse_jobs(job_ids: List[str], output_path: Optional[str] = None) -> bool:
    """
    重新提交解析任务
    
    Args:
        job_ids: 要重新提交的任务ID列表（如: ["SL2813610252", "SL2789485480"]）
        output_path: 输出结果文件路径（可选）
        
    Returns:
        bool: 提交成功返回True，否则返回False
    """
    if not job_ids:
        logger.error("任务ID列表不能为空")
        return False
    
    print("=" * 60)
    print("重新提交解析任务")
    print("=" * 60)
    
    print(f"准备重新提交 {len(job_ids)} 个任务:")
    for i, job_id in enumerate(job_ids, 1):
        print(f"  {i}. {job_id}")
    
    # 准备请求
    url = REPARSER_API_CONFIG['url']
    headers = REPARSER_API_CONFIG['headers'].copy()
    headers['X-Token'] = REPARSER_API_CONFIG['x_token']
    timeout = REPARSER_API_CONFIG['timeout']
    
    # 准备请求体（JSON数组）
    request_data = job_ids
    
    print(f"\n发送请求到: {url}")
    print(f"请求头:")
    for key, value in headers.items():
        if key == 'X-Token':
            print(f"  {key}: {'*' * len(value[:4]) + value[:4]}...")  # 隐藏大部分token内容
        else:
            print(f"  {key}: {value}")
    
    print(f"请求体: {json.dumps(request_data, indent=2)}")
    
    try:
        # 发送POST请求
        response = requests.post(
            url=url,
            headers=headers,
            json=request_data,
            timeout=timeout
        )
        
        print(f"\n响应状态码: {response.status_code}")
        print(f"响应头:")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")
        
        # 解析响应
        if response.status_code == 200:
            try:
                response_data = response.json()
                print(f"\n✅ 请求成功!")
                print(f"响应内容:")
                print(json.dumps(response_data, indent=2, ensure_ascii=False))
                
                # 创建结果记录
                results = []
                for job_id in job_ids:
                    results.append({
                        'job_id': job_id,
                        'status': 'submitted',
                        'timestamp': pd.Timestamp.now(),
                        'response': json.dumps(response_data, ensure_ascii=False)
                    })
                
                # 保存结果
                if output_path:
                    results_df = pd.DataFrame(results)
                    if output_path.endswith('.csv'):
                        results_df.to_csv(output_path, index=False, encoding='utf-8')
                    else:
                        # 使用ExcelProcessor保存
                        from src.file_processors.excel_processor import ExcelProcessor
                        processor = ExcelProcessor("")  # 创建一个临时处理器
                        processor.save_to_excel(output_path, data={"重新提交结果": results_df})
                    
                    print(f"\n结果已保存至: {output_path}")
                
                return True
                
            except json.JSONDecodeError:
                print(f"\n✅ 请求成功，但响应不是JSON格式:")
                print(f"响应内容: {response.text}")
                return True
                
        else:
            print(f"\n❌ 请求失败!")
            print(f"响应内容: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"网络请求失败: {str(e)}")
        print(f"\n❌ 网络请求失败: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"重新提交任务时出错: {str(e)}")
        print(f"\n❌ 重新提交任务时出错: {str(e)}")
        return False


def resubmit_from_analysis_results(file_path: str, column_name: str = 'shulex_ssn', output_path: Optional[str] = None) -> bool:
    """
    从分析结果文件中提取任务ID并重新提交解析任务
    
    Args:
        file_path: 分析结果Excel文件路径
        column_name: 包含任务ID的列名，默认为'shulex_ssn'
        output_path: 输出结果文件路径（可选）
        
    Returns:
        bool: 提交成功返回True，否则返回False
    """
    if not os.path.exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        return False
    
    print("=" * 60)
    print("从分析结果中提取任务ID并重新提交")
    print("=" * 60)
    
    try:
        # 读取Excel文件
        processor = ExcelProcessor(file_path)
        if not processor.read_file():
            return False
        
        data = processor.get_data()
        if data is None or len(data) == 0:
            logger.error("文件中没有数据")
            return False
        
        # 检查列是否存在
        if column_name not in data.columns:
            logger.error(f"列 '{column_name}' 不存在于文件中")
            print(f"可用列: {', '.join(data.columns)}")
            return False
        
        # 提取任务ID
        job_ids = data[column_name].dropna().unique().tolist()
        job_ids = [str(job_id) for job_id in job_ids if str(job_id).strip()]  # 转换为字符串并去除空值
        
        if not job_ids:
            logger.error(f"从列 '{column_name}' 中未找到有效的任务ID")
            return False
        
        print(f"从文件 {file_path} 的列 '{column_name}' 中提取到 {len(job_ids)} 个任务ID")
        
        # 调用重新提交方法
        return resubmit_parse_jobs(job_ids, output_path)
        
    except Exception as e:
        logger.error(f"处理文件时出错: {str(e)}")
        return False


def resubmit_crawler_jobs(job_ids: List[str], output_path: Optional[str] = None) -> bool:
    """
    重新提交爬虫任务
    
    Args:
        job_ids: 要重新提交的任务ID列表（如: ["SL2813610252", "SL2789485480"]）
        output_path: 输出结果文件路径（可选）
        
    Returns:
        bool: 提交成功返回True，否则返回False
    """
    if not job_ids:
        logger.error("任务ID列表不能为空")
        return False
    
    print("=" * 60)
    print("重新提交爬虫任务")
    print("=" * 60)
    
    print(f"准备重新提交 {len(job_ids)} 个任务:")
    for i, job_id in enumerate(job_ids, 1):
        print(f"  {i}. {job_id}")
    
    # 准备请求
    url = CRAWLER_API_CONFIG['url']
    headers = CRAWLER_API_CONFIG['headers'].copy()
    headers['X-Token'] = CRAWLER_API_CONFIG['x_token']
    timeout = CRAWLER_API_CONFIG['timeout']
    
    print(f"\n发送请求到: {url}")
    print(f"请求头:")
    for key, value in headers.items():
        if key == 'X-Token':
            print(f"  {key}: {'*' * len(value[:4]) + value[:4]}...")  # 隐藏大部分token内容
        else:
            print(f"  {key}: {value}")
    
    # 逐个处理任务ID（因为API要求单个req_ssn格式）
    all_results = []
    success_count = 0
    fail_count = 0
    
    for i, job_id in enumerate(job_ids):
        print(f"\n--- 提交第 {i+1}/{len(job_ids)} 个任务: {job_id} ---")
        
        # 准备单个任务的请求体
        request_data = {"req_ssn": job_id}
        
        print(f"请求体: {json.dumps(request_data, indent=2)}")
        
        try:
            # 发送POST请求
            response = requests.post(
                url=url,
                headers=headers,
                json=request_data,
                timeout=timeout
            )
            
            print(f"响应状态码: {response.status_code}")
            
            # 解析响应
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    print(f"✅ 请求成功!")
                    print(f"响应内容:")
                    print(json.dumps(response_data, indent=2, ensure_ascii=False))
                    
                    # 记录成功结果
                    result_record = {
                        'job_id': job_id,
                        'status': 'submitted',
                        'timestamp': pd.Timestamp.now(),
                        'response': json.dumps(response_data, ensure_ascii=False),
                        'http_status': response.status_code
                    }
                    success_count += 1
                    
                except json.JSONDecodeError:
                    print(f"✅ 请求成功，但响应不是JSON格式:")
                    print(f"响应内容: {response.text}")
                    
                    # 记录成功结果（非JSON响应）
                    result_record = {
                        'job_id': job_id,
                        'status': 'submitted',
                        'timestamp': pd.Timestamp.now(),
                        'response': response.text,
                        'http_status': response.status_code
                    }
                    success_count += 1
                    
            else:
                print(f"❌ 请求失败!")
                print(f"响应内容: {response.text}")
                
                # 记录失败结果
                result_record = {
                    'job_id': job_id,
                    'status': 'failed',
                    'timestamp': pd.Timestamp.now(),
                    'response': response.text,
                    'http_status': response.status_code
                }
                fail_count += 1
                
        except requests.exceptions.RequestException as e:
            logger.error(f"网络请求失败: {str(e)}")
            print(f"❌ 网络请求失败: {str(e)}")
            
            # 记录失败结果
            result_record = {
                'job_id': job_id,
                'status': 'network_error',
                'timestamp': pd.Timestamp.now(),
                'response': str(e),
                'http_status': -1
            }
            fail_count += 1
            
        except Exception as e:
            logger.error(f"处理任务时出错: {str(e)}")
            print(f"❌ 处理任务时出错: {str(e)}")
            
            # 记录失败结果
            result_record = {
                'job_id': job_id,
                'status': 'error',
                'timestamp': pd.Timestamp.now(),
                'response': str(e),
                'http_status': -1
            }
            fail_count += 1
        
        all_results.append(result_record)
    
    # 生成汇总报告
    print("\n" + "=" * 60)
    print("提交结果汇总")
    print("=" * 60)
    print(f"总任务数: {len(job_ids)}")
    print(f"成功提交: {success_count}")
    print(f"失败提交: {fail_count}")
    print(f"成功率: {(success_count/len(job_ids)*100):.1f}%")
    
    # 保存结果
    if output_path:
        results_df = pd.DataFrame(all_results)
        if output_path.endswith('.csv'):
            results_df.to_csv(output_path, index=False, encoding='utf-8')
        else:
            # 使用ExcelProcessor保存
            from src.file_processors.excel_processor import ExcelProcessor
            processor = ExcelProcessor("")  # 创建一个临时处理器
            processor.save_to_excel(output_path, data={"重新提交爬虫结果": results_df})
        
        print(f"\n结果已保存至: {output_path}")
    
    return fail_count == 0  # 所有任务都成功才返回True


def resubmit_crawler_from_txt_file(file_path: str, nrows: int = 1, output_path: Optional[str] = None) -> bool:
    """
    从txt文件中读取任务ID并重新提交爬虫任务
    
    Args:
        file_path: txt文件路径，每行一个任务ID
        nrows: 读取的行数，默认为1
        output_path: 输出结果文件路径（可选）
        
    Returns:
        bool: 提交成功返回True，否则返回False
    """
    if not os.path.exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        return False
    
    print("=" * 60)
    print("从txt文件中读取任务ID并重新提交爬虫任务")
    print("=" * 60)
    
    try:
        # 读取txt文件
        job_ids = []
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        print(f"文件 {file_path} 共有 {len(lines)} 行数据")
        print(f"将读取前 {nrows} 行数据")
        
        # 处理指定行数的数据
        for i, line in enumerate(lines[:nrows]):
            line = line.strip()
            if line:  # 跳过空行
                # 检查是否有SL前缀，如果没有则添加
                if not line.startswith('SL'):
                    job_id = f"SL{line}"
                else:
                    job_id = line
                job_ids.append(job_id)
                print(f"  {i+1}. {line} -> {job_id}")
        
        if not job_ids:
            logger.error("没有读取到有效的任务ID")
            return False
        
        print(f"\n成功处理 {len(job_ids)} 个任务ID")
        
        # 调用重新提交方法
        return resubmit_crawler_jobs(job_ids, output_path)
        
    except Exception as e:
        logger.error(f"处理txt文件时出错: {str(e)}")
        return False


def resubmit_from_txt_file(file_path: str, nrows: int = 1, output_path: Optional[str] = None) -> bool:
    """
    从txt文件中读取任务ID并重新提交爬虫任务（为了保持向后兼容性）
    这个函数实际上调用resubmit_crawler_from_txt_file
    
    Args:
        file_path: txt文件路径，每行一个任务ID
        nrows: 读取的行数，默认为1
        output_path: 输出结果文件路径（可选）
        
    Returns:
        bool: 提交成功返回True，否则返回False
    """
    # 直接调用爬虫任务提交方法
    return resubmit_crawler_from_txt_file(file_path, nrows, output_path)


def resubmit_parse_from_txt_file(file_path: str, nrows: int = 1, output_path: Optional[str] = None) -> bool:
    """
    从txt文件中读取任务ID并重新提交解析任务
    
    Args:
        file_path: txt文件路径，每行一个任务ID
        nrows: 读取的行数，默认为1
        output_path: 输出结果文件路径（可选）
        
    Returns:
        bool: 提交成功返回True，否则返回False
    """
    if not os.path.exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        return False
    
    print("=" * 60)
    print("从txt文件中读取任务ID并重新提交解析任务")
    print("=" * 60)
    
    try:
        # 读取txt文件
        job_ids = []
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        print(f"文件 {file_path} 共有 {len(lines)} 行数据")
        print(f"将读取前 {nrows} 行数据")
        
        # 处理指定行数的数据
        for i, line in enumerate(lines[:nrows]):
            line = line.strip()
            if line:  # 跳过空行
                # 检查是否有SL前缀，如果没有则添加
                if not line.startswith('SL'):
                    job_id = f"SL{line}"
                else:
                    job_id = line
                job_ids.append(job_id)
                print(f"  {i+1}. {line} -> {job_id}")
        
        if not job_ids:
            logger.error("没有读取到有效的任务ID")
            return False
        
        print(f"\n成功处理 {len(job_ids)} 个任务ID")
        
        # 调用重新提交解析任务方法
        return resubmit_parse_jobs(job_ids, output_path)
        
    except Exception as e:
        logger.error(f"处理txt文件时出错: {str(e)}")
        return False


def main():
    """主函数"""
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='Shulex-Anker数据验证工具')
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # 测试数据库连接命令
    test_parser = subparsers.add_parser('test_connection', help='测试数据库连接')
    
    # 处理文件命令
    process_parser = subparsers.add_parser('process_file', help='处理CSV或Excel文件')
    process_parser.add_argument('--file', '-f', required=True, help='输入文件路径')
    process_parser.add_argument('--type', '-t', choices=['csv', 'excel'], help='文件类型，默认根据扩展名判断')
    process_parser.add_argument('--output', '-o', help='输出文件路径')
    
    # 分块读取Excel文件命令
    excel_parser = subparsers.add_parser('read_excel_chunked', help='分块读取大Excel文件')
    excel_parser.add_argument('--file', '-f', required=True, help='Excel文件路径')
    excel_parser.add_argument('--nrows', '-n', type=int, default=10, help='读取的行数，默认为10')
    excel_parser.add_argument('--skiprows', '-s', type=int, default=0, help='跳过的行数，默认为0')
    excel_parser.add_argument('--sheet', help='工作表名称，默认为第一个工作表')
    excel_parser.add_argument('--output', '-o', help='输出文件路径')
    
    # 筛选空值列命令
    filter_parser = subparsers.add_parser('filter_null_column', help='筛选指定列为空的数据')
    filter_parser.add_argument('--file', '-f', required=True, help='Excel文件路径')
    filter_parser.add_argument('--column', '-c', required=True, help='要筛选的列名')
    filter_parser.add_argument('--nrows', '-n', type=int, default=10, help='返回的行数，默认为10')
    filter_parser.add_argument('--sheet', help='工作表名称，默认为第一个工作表')
    filter_parser.add_argument('--output', '-o', help='输出文件路径')
    filter_parser.add_argument('--prepare-db', action='store_true', help='准备数据库查询信息')
    
    # 任务数据库分析命令
    analyze_parser = subparsers.add_parser('analyze_tasks_with_db', help='分析任务数据并查询数据库进行问题诊断')
    analyze_parser.add_argument('--file', '-f', required=True, help='Excel文件路径')
    analyze_parser.add_argument('--column', '-c', default='解决进度', help='要筛选的列名，默认为"解决进度"')
    analyze_parser.add_argument('--nrows', '-n', type=int, default=10, help='分析的任务数量，默认为10')
    analyze_parser.add_argument('--sheet', help='工作表名称，默认为第一个工作表')
    analyze_parser.add_argument('--output', '-o', help='输出分析结果的文件路径')
    
    # 重新提交解析任务命令
    resubmit_parser = subparsers.add_parser('resubmit_parse_jobs', help='重新提交解析任务')
    resubmit_parser.add_argument('--job-ids', nargs='+', required=True, help='要重新提交的任务ID列表，如: SL2813610252 SL2789485480')
    resubmit_parser.add_argument('--output', '-o', help='输出结果文件路径')
    
    # 从分析结果文件重新提交任务命令
    resubmit_from_file_parser = subparsers.add_parser('resubmit_from_analysis_results', help='从分析结果文件中提取任务ID并重新提交解析任务')
    resubmit_from_file_parser.add_argument('--file', '-f', required=True, help='分析结果Excel文件路径')
    resubmit_from_file_parser.add_argument('--column', '-c', default='shulex_ssn', help='包含任务ID的列名，默认为shulex_ssn')
    resubmit_from_file_parser.add_argument('--output', '-o', help='输出结果文件路径')
    
    # 从txt文件重新提交任务命令
    resubmit_from_txt_parser = subparsers.add_parser('resubmit_from_txt_file', help='从txt文件中读取任务ID并重新提交爬虫任务')
    resubmit_from_txt_parser.add_argument('--file', '-f', required=True, help='txt文件路径，每行一个任务ID')
    resubmit_from_txt_parser.add_argument('--nrows', '-n', type=int, default=1, help='读取的行数，默认为1')
    resubmit_from_txt_parser.add_argument('--output', '-o', help='输出结果文件路径')
    
    # 重新提交爬虫任务命令
    resubmit_crawler_parser = subparsers.add_parser('resubmit_crawler_jobs', help='重新提交爬虫任务')
    resubmit_crawler_parser.add_argument('--job-ids', nargs='+', required=True, help='要重新提交的任务ID列表，如: SL2813610252 SL2789485480')
    resubmit_crawler_parser.add_argument('--output', '-o', help='输出结果文件路径')
    
    # 从txt文件重新提交爬虫任务命令
    resubmit_crawler_from_txt_parser = subparsers.add_parser('resubmit_crawler_from_txt_file', help='从txt文件中读取任务ID并重新提交爬虫任务')
    resubmit_crawler_from_txt_parser.add_argument('--file', '-f', required=True, help='txt文件路径，每行一个任务ID')
    resubmit_crawler_from_txt_parser.add_argument('--nrows', '-n', type=int, default=1, help='读取的行数，默认为1')
    resubmit_crawler_from_txt_parser.add_argument('--output', '-o', help='输出结果文件路径')
    
    # 从txt文件重新提交解析任务命令
    resubmit_parse_from_txt_parser = subparsers.add_parser('resubmit_parse_from_txt_file', help='从txt文件中读取任务ID并重新提交解析任务')
    resubmit_parse_from_txt_parser.add_argument('--file', '-f', required=True, help='txt文件路径，每行一个任务ID')
    resubmit_parse_from_txt_parser.add_argument('--nrows', '-n', type=int, default=1, help='读取的行数，默认为1')
    resubmit_parse_from_txt_parser.add_argument('--output', '-o', help='输出结果文件路径')
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 根据命令执行相应的功能
    if args.command == 'test_connection':
        test_db_connection()
    elif args.command == 'process_file':
        process_file(args.file, args.type, args.output)
    elif args.command == 'read_excel_chunked':
        read_excel_chunked(args.file, args.nrows, args.skiprows, args.sheet, args.output)
    elif args.command == 'filter_null_column':
        filter_null_column(args.file, args.column, args.nrows, args.sheet, args.output, args.prepare_db)
    elif args.command == 'validate':
        validate_data(args.file, args.output)
    elif args.command == 'analyze_tasks_with_db':
        analyze_tasks_with_db(args.file, args.column, args.nrows, args.sheet, args.output)
    elif args.command == 'resubmit_parse_jobs':
        resubmit_parse_jobs(args.job_ids, args.output)
    elif args.command == 'resubmit_from_analysis_results':
        resubmit_from_analysis_results(args.file, args.column, args.output)
    elif args.command == 'resubmit_from_txt_file':
        resubmit_from_txt_file(args.file, args.nrows, args.output)
    elif args.command == 'resubmit_crawler_jobs':
        resubmit_crawler_jobs(args.job_ids, args.output)
    elif args.command == 'resubmit_crawler_from_txt_file':
        resubmit_crawler_from_txt_file(args.file, args.nrows, args.output)
    elif args.command == 'resubmit_parse_from_txt_file':
        resubmit_parse_from_txt_file(args.file, args.nrows, args.output)
    else:
        parser.print_help()


if __name__ == '__main__':
    main() 