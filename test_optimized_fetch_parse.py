#!/usr/bin/env python3
"""
测试优化版本的解析文件获取功能
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.azure_resource_reader import AzureResourceReader, is_valid_task_id
from src.azure_resource_reader_optimizer import convert_job_id_to_task_info, fetch_and_save_parse_files_optimized


def test_optimized_fetch_parse():
    """
    测试优化版本的解析文件获取功能
    """
    print("🧪 测试优化版本的解析文件获取功能")
    print("=" * 60)
    
    # 测试参数
    task_type = "AmazonReviewStarJob"
    input_param = "2796867471"  # 这是一个需要转换的job_id
    
    print(f"📋 任务类型: {task_type}")
    print(f"📋 输入参数: {input_param}")
    print("-" * 60)
    
    # 第一步：检查是否为有效的任务ID
    if is_valid_task_id(input_param):
        task_id = input_param
        print(f"✅ 检测到有效的任务ID: {task_id}")
        job_id = None
        analysis_response = None
    else:
        # 需要转换为任务ID并获取analysis_response
        job_id = input_param
        
        # 如果是纯数字，添加SL前缀
        if job_id.isdigit():
            job_id = f"SL{job_id}"
            print(f"🔄 添加SL前缀: {job_id}")
        
        print(f"🔍 通过数据库查询转换 job_id: {job_id}")
        
        # 使用优化器的函数获取task_id和analysis_response
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
                
                if is_analysis_response_enabled(task_type):
                    print(f"✅ 任务类型 {task_type} 已启用 analysis_response 解析")
                else:
                    print(f"⚠️  任务类型 {task_type} 未启用 analysis_response 解析，将使用传统方法")
                    analysis_response = None
            except ImportError:
                print(f"⚠️  无法导入 analysis_response 配置，将使用传统方法")
                analysis_response = None
        else:
            print(f"ℹ️  未找到 analysis_response 数据")
    
    print(f"📁 Azure路径: collector0109/parse/{task_type}/{task_id}/")
    print("-" * 60)
    
    # 第二步：使用优化的方法获取解析文件
    print(f"📥 开始使用优化方法获取解析文件...")
    
    # 创建collector0109读取器
    reader = AzureResourceReader('collector0109')
    
    # 使用优化方法
    result = fetch_and_save_parse_files_optimized(
        reader=reader,
        task_type=task_type,
        task_id=task_id,
        save_dir='data/output',
        decompress=True,
        job_id=job_id,
        analysis_response=analysis_response
    )
    
    # 第三步：显示结果
    print("\n" + "=" * 60)
    print("📊 测试结果")
    print("=" * 60)
    
    if result['success']:
        print(f"✅ 解析文件获取成功!")
        print(f"📂 保存路径: {result['save_path']}")
        
        if 'method_used' in result:
            method_name = "analysis_response链接" if result['method_used'] == 'analysis_response' else "Azure存储"
            print(f"📡 获取方式: {method_name}")
        
        print(f"📥 下载文件数: {result['total_files_downloaded']}")
        
        if result['files_downloaded']:
            print(f"\n📄 已下载的文件:")
            for file_info in result['files_downloaded']:
                print(f"  ✅ {file_info['saved_name']}")
                if 'size' in file_info:
                    print(f"     📊 大小: {file_info['size']} 字节")
                print(f"     📁 路径: {file_info['local_path']}")
                if 'download_url' in file_info:
                    print(f"     🔗 来源: analysis_response链接")
                    print(f"     🌐 URL: {file_info['download_url'][:80]}...")
                print()
    else:
        print(f"❌ 解析文件获取失败!")
        print(f"🔍 错误信息: {result.get('error', '未知错误')}")


if __name__ == '__main__':
    test_optimized_fetch_parse() 