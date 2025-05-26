#!/usr/bin/env python3
"""
示例：使用优化的方法从collector0109获取解析文件
基于测试结果优化，仅使用正确的路径结构
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.azure_resource_reader import AzureResourceReader
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_fetch_parse_files():
    """演示如何获取解析文件"""
    print("🔍 collector0109 解析文件获取示例")
    print("=" * 80)
    
    # 示例任务参数 - 基于测试成功的案例
    examples = [
        {
            'task_type': 'AmazonReviewStarJob',
            'task_id': '1887037115222994944',
            'description': '测试成功的任务'
        },
        {
            'task_type': 'AmazonListingJob', 
            'task_id': '1925464883027513344',
            'description': '示例任务'
        }
    ]
    
    # 创建collector0109读取器
    reader = AzureResourceReader('collector0109')
    
    for i, example in enumerate(examples, 1):
        print(f"\n📋 示例 {i}: {example['description']}")
        print(f"任务类型: {example['task_type']}")
        print(f"任务ID: {example['task_id']}")
        print("-" * 60)
        
        # 使用优化的方法获取解析文件
        result = reader.fetch_and_save_parse_files(
            task_type=example['task_type'],
            task_id=example['task_id'],
            save_dir='data/examples',
            decompress=True
        )
        
        # 显示结果
        if result['success']:
            print(f"✅ 成功获取解析文件!")
            print(f"📂 保存路径: {result['save_path']}")
            print(f"📊 找到文件数: {result['total_files_found']}")
            print(f"📥 下载文件数: {result['total_files_downloaded']}")
            
            if result['files_downloaded']:
                print(f"📄 已下载的文件:")
                for file_info in result['files_downloaded']:
                    print(f"  • {file_info['saved_name']}")
                    print(f"    大小: {file_info['size']} 字节")
                    print(f"    路径: {file_info['local_path']}")
        else:
            print(f"❌ 获取失败: {result.get('error', '未知错误')}")


def example_direct_api_usage():
    """演示直接使用API的方法"""
    print("\n🔧 直接API使用示例")
    print("=" * 80)
    
    # 创建collector0109读取器
    reader = AzureResourceReader('collector0109')
    
    task_type = 'AmazonReviewStarJob'
    task_id = '1887037115222994944'
    
    print(f"📋 任务类型: {task_type}")
    print(f"📋 任务ID: {task_id}")
    
    # 方法1: 列出解析文件
    print("\n方法1: 列出解析文件")
    files = reader.list_parse_files(task_type, task_id)
    if files:
        print(f"✅ 找到 {len(files)} 个解析文件:")
        for file_info in files:
            print(f"  📄 {file_info['name']}")
            print(f"     大小: {file_info['size']} 字节")
    else:
        print("❌ 未找到解析文件")
    
    # 方法2: 读取单个解析文件
    print("\n方法2: 读取解析文件内容")
    content = reader.read_parse_file(task_type, task_id, decompress=True)
    if content:
        print(f"✅ 读取成功!")
        if isinstance(content, str):
            print(f"📝 内容长度: {len(content)} 字符")
            print(f"🔍 内容预览: {content[:100]}...")
        else:
            print(f"📊 数据长度: {len(content)} 字节")
    else:
        print("❌ 读取失败")


def main():
    """主函数"""
    print("🧪 collector0109 解析文件获取器示例")
    print("基于测试结果优化，使用正确的路径结构")
    print("=" * 80)
    
    try:
        # 示例1: 使用优化的批量获取方法
        example_fetch_parse_files()
        
        # 示例2: 直接使用API
        example_direct_api_usage()
        
        print("\n" + "=" * 80)
        print("✅ 示例运行完成!")
        print("📂 文件保存在: data/examples/parse/ 目录下")
        print("\n💡 命令行使用方式:")
        print("python3 src/azure_resource_reader.py AmazonReviewStarJob 1887037115222994944 --fetch-parse")
        
    except Exception as e:
        logger.error(f"❌ 示例运行失败: {str(e)}")


if __name__ == '__main__':
    main() 