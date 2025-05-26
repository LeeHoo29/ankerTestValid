#!/usr/bin/env python3
"""
Azure Storage --with-parse 模式优化版本
集成 analysis_response 优化功能
"""
import sys
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.azure_resource_reader import AzureResourceReader
import json


def process_with_parse_optimized(task_type, task_id_param, output_type, save_dir="data/output"):
    """
    优化版本的 --with-parse 处理
    """
    print(f"🔍 Azure Storage 资源读取器 (原始数据 + 解析数据 - 优化版本)")
    print(f"📋 任务类型: {task_type}")
    print(f"📋 输入参数: {task_id_param}")
    
    # 第一步：处理任务ID转换并获取analysis_response
    task_id = None
    analysis_response = None
    job_id = None
    
    # 检查是否为有效任务ID
    if len(task_id_param) >= 15 and task_id_param.isdigit():
        task_id = task_id_param
        print(f"✅ 检测到有效的任务ID: {task_id}")
    else:
        # 需要转换
        job_id = task_id_param
        if job_id.isdigit():
            job_id = f"SL{job_id}"
            print(f"🔄 添加SL前缀: {job_id}")
        
        print(f"🔍 查询数据库转换 job_id: {job_id}")
        
        # 尝试使用优化器
        try:
            from src.azure_resource_reader_optimizer import convert_job_id_to_task_info
            task_info = convert_job_id_to_task_info(job_id)
            
            if task_info is None:
                print(f"❌ 无法找到对应的任务ID")
                return
            
            task_id, analysis_response = task_info
            print(f"✅ 获得任务ID: {task_id}")
            
            if analysis_response:
                print(f"✅ 获得 analysis_response 数据")
                
                # 检查是否启用
                try:
                    from config.analysis_response_config import is_analysis_response_enabled
                    if is_analysis_response_enabled(task_type):
                        print(f"✅ 任务类型 {task_type} 已启用 analysis_response 解析")
                    else:
                        print(f"⚠️  任务类型 {task_type} 未启用，使用传统方法")
                        analysis_response = None
                except ImportError:
                    print(f"⚠️  配置模块不可用，使用传统方法")
                    analysis_response = None
        except ImportError:
            print(f"⚠️  优化器不可用，使用传统方法")
            # 回退到基础方法 (简化版本)
            from src.azure_resource_reader import convert_job_id_to_task_id
            task_id = convert_job_id_to_task_id(job_id)
            if not task_id:
                print(f"❌ 转换失败")
                return
    
    print(f"📁 路径: yiya0110/download/compress/{task_type}/{task_id}/")
    print(f"📁 解析: collector0109/parse/{task_type}/{task_id}/")
    print("=" * 60)
    
    # 第二步：优先使用优化方法获取解析文件
    parse_success = False
    try:
        if analysis_response:
            print(f"🚀 步骤1: 尝试优化方法获取解析文件")
            
            from src.azure_resource_reader_optimizer import fetch_and_save_parse_files_optimized
            parse_reader = AzureResourceReader('collector0109')
            
            parse_result = fetch_and_save_parse_files_optimized(
                reader=parse_reader,
                task_type=task_type,
                task_id=task_id,
                save_dir=save_dir,
                decompress=True,
                job_id=job_id,
                analysis_response=analysis_response
            )
            
            if parse_result['success']:
                print(f"✅ 解析文件获取成功!")
                method_name = "analysis_response链接" if parse_result.get('method_used') == 'analysis_response' else "Azure存储"
                print(f"📡 获取方式: {method_name}")
                parse_success = True
                
                for file_info in parse_result.get('files_downloaded', []):
                    print(f"  ✅ {file_info['saved_name']} ({file_info.get('size', 0)} 字节)")
            else:
                print(f"❌ 优化方法失败: {parse_result.get('error')}")
    except ImportError:
        print(f"⚠️  优化功能不可用")
    
    # 第三步：获取原始文件
    print(f"\n📄 步骤2: 获取原始文件")
    
    # 获取默认文件列表
    if task_type == 'AmazonReviewStarJob':
        files_to_process = ['page_1.gz', 'page_2.gz', 'page_3.gz', 'page_4.gz', 'page_5.gz']
    else:
        files_to_process = ['login.gz', 'normal.gz']
    
    print(f"📄 处理文件: {', '.join(files_to_process)}")
    
    reader = AzureResourceReader('yiya0110')
    decompress = output_type in ['html', 'txt', 'json']
    downloaded_files = []
    
    for filename in files_to_process:
        print(f"\n  📄 {filename}")
        content = reader.read_task_file(task_type, task_id, filename, decompress)
        
        if content is not None:
            print(f"    ✅ 读取成功 ({len(content)} {'字符' if isinstance(content, str) else '字节'})")
            
            # 生成保存文件名
            if output_type == 'html':
                save_name = f"{filename.replace('.gz', '')}.html"
            elif output_type == 'txt':
                save_name = f"{filename.replace('.gz', '')}.txt"
            elif output_type == 'json':
                save_name = f"{filename.replace('.gz', '')}.json"
            else:
                save_name = filename
            
            # 保存文件
            local_path = f"{save_dir}/{task_type}/{task_id}/{save_name}"
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            
            if isinstance(content, str):
                with open(local_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            else:
                with open(local_path, 'wb') as f:
                    f.write(content)
            
            print(f"    💾 已保存: {local_path}")
            downloaded_files.append(filename)
        else:
            print(f"    ❌ 读取失败")
    
    # 如果没有通过优化方法获取解析文件，使用传统方法
    if not parse_success:
        print(f"\n🔄 步骤3: 传统方法获取解析文件")
        
        if downloaded_files:
            # 使用第一个文件来获取解析数据
            combined_content = reader.read_task_file_with_parse(task_type, task_id, downloaded_files[0], True)
            parse_content = combined_content.get('parse')
            
            if parse_content:
                print(f"✅ 解析文件读取成功 ({len(parse_content)} 字符)")
                
                # 保存解析文件
                parse_path = f"{save_dir}/{task_type}/{task_id}/parse_result.json"
                with open(parse_path, 'w', encoding='utf-8') as f:
                    f.write(parse_content)
                print(f"💾 解析文件已保存: {parse_path}")
                parse_success = True
            else:
                print(f"❌ 解析文件获取失败")
    
    # 结果总结
    print(f"\n" + "=" * 60)
    print(f"📊 处理结果")
    print(f"=" * 60)
    print(f"✅ 原始文件: {len(downloaded_files)} 个")
    print(f"✅ 解析文件: {'1 个' if parse_success else '0 个'}")
    print(f"📂 保存目录: {save_dir}/{task_type}/{task_id}/")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Azure Storage --with-parse 优化版本')
    parser.add_argument('task_type', help='任务类型')
    parser.add_argument('task_id', help='任务ID或job_id')
    parser.add_argument('output_type', choices=['html', 'txt', 'json', 'binary'], help='输出格式')
    parser.add_argument('--save-dir', default='data/output', help='保存目录')
    
    args = parser.parse_args()
    
    process_with_parse_optimized(
        task_type=args.task_type,
        task_id_param=args.task_id,
        output_type=args.output_type,
        save_dir=args.save_dir
    )


if __name__ == '__main__':
    main() 