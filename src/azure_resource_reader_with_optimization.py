#!/usr/bin/env python3
"""
Azure Storage 资源读取器的 --with-parse 模式优化版本
专门用于同时获取原始数据和解析数据，集成了analysis_response优化功能
"""
import sys
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.azure_resource_reader import (
    AzureResourceReader, 
    is_valid_task_id, 
    convert_job_id_to_task_id,
    get_default_files_for_task_type,
    update_task_mapping,
    print_task_mapping_info,
    _generate_save_filename,
    _save_content_to_file
)
import json


def handle_with_parse_mode_optimized(args) -> None:
    """
    处理同时获取原始数据和解析数据的模式 (集成优化版本)
    
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
            from src.azure_resource_reader_optimizer import convert_job_id_to_task_info
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


def main():
    """主函数：处理命令行参数并执行优化版 --with-parse 模式"""
    parser = argparse.ArgumentParser(
        description='Azure Storage 资源读取器 --with-parse 模式优化版本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 使用任务ID直接获取原始文件和解析文件
  python3 src/azure_resource_reader_with_optimization.py AmazonReviewStarJob 1887037115222994944 html
  
  # 使用job_id获取（优先从analysis_response链接下载解析文件）
  python3 src/azure_resource_reader_with_optimization.py AmazonReviewStarJob 2796867471 html
  
  # 指定保存目录和特定文件
  python3 src/azure_resource_reader_with_optimization.py AmazonReviewStarJob 2796867471 html --save-dir data/test_output --files page_1.gz

优化功能说明:
  1. 自动查询数据库获取 analysis_response 字段
  2. 如果任务类型支持且有有效链接，优先从 analysis_response 中的链接下载解析文件
  3. 如果链接失效或任务类型不支持，自动回退到 Azure 存储方法
  4. 支持自动JSON格式检测和文件扩展名修正
  5. 解析文件和原始文件保存在同一目录下
        """
    )
    
    parser.add_argument('task_type_or_job_id', 
                       help='任务类型（如: AmazonReviewStarJob）')
    parser.add_argument('task_id_or_task_id', 
                       help='任务ID（长数字串）或job_id（如: 2796867471）')
    parser.add_argument('output_type',
                       choices=['html', 'txt', 'json', 'binary'],
                       help='输出格式：html, txt, json, binary')
    parser.add_argument('--save-dir', '-s',
                       default='data/output',
                       help='保存目录，默认: data/output')
    parser.add_argument('--files', '-f',
                       nargs='+',
                       help='指定要读取的文件名（多个文件用空格分隔）')
    parser.add_argument('--info-only',
                       action='store_true',
                       help='仅显示文件信息，不下载')
    parser.add_argument('--no-mapping',
                       action='store_true',
                       help='不生成映射文件')
    
    args = parser.parse_args()
    
    # 执行优化版 --with-parse 模式
    handle_with_parse_mode_optimized(args)


if __name__ == '__main__':
    main() 