#!/usr/bin/env python3
"""
优化版本的解析文件获取脚本
支持从 analysis_response 中的链接优先下载，失败时回退到Azure存储
"""
import sys
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.azure_resource_reader import AzureResourceReader, is_valid_task_id
from src.azure_resource_reader_optimizer import convert_job_id_to_task_info, fetch_and_save_parse_files_optimized


def main():
    """主函数：处理命令行参数并执行优化版解析文件获取"""
    parser = argparse.ArgumentParser(
        description='Azure Storage 解析文件获取器 (优化版本)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 使用任务ID直接获取解析文件
  python3 src/azure_fetch_parse_optimized.py AmazonReviewStarJob 1887037115222994944
  
  # 使用job_id获取解析文件（优先从analysis_response链接下载）
  python3 src/azure_fetch_parse_optimized.py AmazonReviewStarJob 2796867471
  
  # 指定保存目录
  python3 src/azure_fetch_parse_optimized.py AmazonReviewStarJob 2796867471 --save-dir data/test_output

优化功能说明:
  1. 自动查询数据库获取 analysis_response 字段
  2. 如果任务类型支持且有有效链接，优先从 analysis_response 中的链接下载
  3. 如果链接失效或任务类型不支持，自动回退到 Azure 存储方法
  4. 支持自动JSON格式检测和文件扩展名修正
        """
    )
    
    parser.add_argument('task_type', 
                       help='任务类型（如: AmazonReviewStarJob）')
    parser.add_argument('task_id_or_job_id', 
                       help='任务ID（长数字串）或job_id（如: 2796867471）')
    parser.add_argument('--save-dir', '-s',
                       default='data/output',
                       help='保存目录，默认: data/output')
    parser.add_argument('--no-decompress',
                       action='store_true',
                       help='不自动解压缩文件')
    
    args = parser.parse_args()
    
    task_type = args.task_type
    input_param = args.task_id_or_job_id
    decompress = not args.no_decompress
    
    print(f"🔍 Azure Storage 解析文件获取器 (优化版本)")
    print(f"📋 任务类型: {task_type}")
    print(f"📋 输入参数: {input_param}")
    print("=" * 80)
    
    # 第一步：确定task_id和获取analysis_response
    task_id = None
    analysis_response = None
    job_id = None
    
    if is_valid_task_id(input_param):
        # 直接使用作为任务ID
        task_id = input_param
        print(f"✅ 检测到有效的任务ID: {task_id}")
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
            print(f"✅ 获得 analysis_response 数据")
            
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
    print("=" * 80)
    
    # 第二步：使用优化的方法获取解析文件
    print(f"📥 开始获取解析文件...")
    
    # 创建collector0109读取器
    reader = AzureResourceReader('collector0109')
    
    # 使用优化方法
    result = fetch_and_save_parse_files_optimized(
        reader=reader,
        task_type=task_type,
        task_id=task_id,
        save_dir=args.save_dir,
        decompress=decompress,
        job_id=job_id,
        analysis_response=analysis_response
    )
    
    # 第三步：显示结果
    print("\n" + "=" * 80)
    print("📊 获取结果")
    print("=" * 80)
    
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
                
        print(f"\n💡 提示:")
        print(f"   文件已保存到: {result['save_path']}")
        if 'method_used' in result and result['method_used'] == 'analysis_response':
            print(f"   🚀 使用 analysis_response 链接下载，速度更快！")
        
    else:
        print(f"❌ 解析文件获取失败!")
        print(f"🔍 错误信息: {result.get('error', '未知错误')}")
        print(f"\n💡 建议:")
        print(f"   1. 检查网络连接")
        print(f"   2. 验证任务ID或job_id是否正确")
        print(f"   3. 确认Azure存储访问权限")


if __name__ == '__main__':
    main()