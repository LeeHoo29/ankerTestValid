#!/usr/bin/env python3
"""
collector0109 存储账户单元测试
专门测试解析文件读取功能
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


def test_collector0109_connection():
    """测试collector0109连接"""
    print("🔍 测试collector0109存储账户连接")
    print("=" * 60)
    
    try:
        reader = AzureResourceReader('collector0109')
        print("✅ collector0109连接成功")
        return reader
    except Exception as e:
        print(f"❌ collector0109连接失败: {e}")
        return None


def test_list_container_contents(reader):
    """测试列出容器内容"""
    print("\n🔍 列出parse容器的根目录内容")
    print("=" * 60)
    
    try:
        container_client = reader.blob_service_client.get_container_client('parse')
        
        # 列出根目录内容（限制50个）
        blobs = list(container_client.list_blobs(name_starts_with='parse/', max_results=50))
        
        print(f"✅ 找到 {len(blobs)} 个文件/目录")
        for blob in blobs[:10]:  # 只显示前10个
            print(f"  📄 {blob.name}")
            print(f"     📊 大小: {blob.size} 字节")
            print(f"     📅 修改: {blob.last_modified}")
            print()
            
        return blobs
    except Exception as e:
        print(f"❌ 列出容器内容失败: {e}")
        return []


def test_specific_path(reader, task_type, task_id):
    """测试特定路径下的文件"""
    print(f"\n🔍 测试特定路径: parse/parse/{task_type}/{task_id}/")
    print("=" * 60)
    
    try:
        # 使用现有的方法列出文件
        files = reader.list_parse_files(task_type, task_id)
        
        if files:
            print(f"✅ 找到 {len(files)} 个文件:")
            for file_info in files:
                print(f"  📄 文件: {file_info['name']}")
                print(f"     📊 大小: {file_info['size']} 字节")
                print(f"     📅 修改: {file_info['last_modified']}")
                print()
        else:
            print("❌ 未找到文件")
            
        # 直接使用container client测试
        print(f"\n🔍 直接测试路径前缀:")
        container_client = reader.blob_service_client.get_container_client('parse')
        prefix = f"parse/parse/{task_type}/{task_id}/"
        print(f"  前缀: {prefix}")
        
        direct_blobs = list(container_client.list_blobs(name_starts_with=prefix))
        
        if direct_blobs:
            print(f"✅ 直接查询找到 {len(direct_blobs)} 个文件:")
            for blob in direct_blobs:
                print(f"  📄 直接查询: {blob.name}")
                print(f"     📊 大小: {blob.size} 字节")
                print(f"     📅 修改: {blob.last_modified}")
                print()
        else:
            print("❌ 直接查询也未找到文件")
            
        return files, direct_blobs
        
    except Exception as e:
        print(f"❌ 测试特定路径失败: {e}")
        return [], []


def test_path_variations(reader, task_type, task_id):
    """测试不同的路径变体"""
    print(f"\n🔍 测试路径变体")
    print("=" * 60)
    
    path_variations = [
        f"parse/parse/{task_type}/{task_id}/",
        f"parse/parse/{task_type}/{task_id}",
        f"parse/{task_type}/{task_id}/",
        f"parse/{task_type}/{task_id}",
        f"{task_type}/{task_id}/",
        f"{task_type}/{task_id}",
    ]
    
    container_client = reader.blob_service_client.get_container_client('parse')
    
    for prefix in path_variations:
        try:
            blobs = list(container_client.list_blobs(name_starts_with=prefix, max_results=10))
            print(f"  路径: {prefix}")
            print(f"  结果: {len(blobs)} 个文件")
            if blobs:
                for blob in blobs[:3]:  # 只显示前3个
                    print(f"    📄 {blob.name}")
            print()
        except Exception as e:
            print(f"  路径: {prefix} - 错误: {e}")


def test_search_task_files(reader, task_id):
    """搜索包含特定task_id的所有文件"""
    print(f"\n🔍 搜索包含task_id {task_id}的所有文件")
    print("=" * 60)
    
    try:
        container_client = reader.blob_service_client.get_container_client('parse')
        
        # 搜索所有包含task_id的文件
        all_blobs = container_client.list_blobs(name_starts_with='parse/')
        
        matching_blobs = []
        for blob in all_blobs:
            if task_id in blob.name:
                matching_blobs.append(blob)
                
        if matching_blobs:
            print(f"✅ 找到 {len(matching_blobs)} 个包含task_id的文件:")
            for blob in matching_blobs:
                print(f"  📄 {blob.name}")
                print(f"     📊 大小: {blob.size} 字节")
                print(f"     📅 修改: {blob.last_modified}")
                print()
        else:
            print(f"❌ 未找到包含task_id {task_id}的文件")
            
        return matching_blobs
        
    except Exception as e:
        print(f"❌ 搜索task_id文件失败: {e}")
        return []


def main():
    """主测试函数"""
    print("🧪 collector0109 存储账户单元测试")
    print("=" * 80)
    
    # 测试参数
    task_type = "AmazonReviewStarJob"
    task_id = "1910598939612549120"
    
    # 1. 测试连接
    reader = test_collector0109_connection()
    if not reader:
        return
    
    # 2. 列出容器内容
    test_list_container_contents(reader)
    
    # 3. 测试特定路径
    files, direct_blobs = test_specific_path(reader, task_type, task_id)
    
    # 4. 测试路径变体
    test_path_variations(reader, task_type, task_id)
    
    # 5. 搜索task_id相关文件
    matching_blobs = test_search_task_files(reader, task_id)
    
    # 总结
    print("\n" + "=" * 80)
    print("📊 测试总结")
    print("=" * 80)
    print(f"目标路径: parse/parse/{task_type}/{task_id}/")
    print(f"现有方法找到文件数: {len(files)}")
    print(f"直接查询找到文件数: {len(direct_blobs)}")
    print(f"包含task_id的文件数: {len(matching_blobs)}")
    
    if matching_blobs:
        print("\n🎯 实际存在的文件路径:")
        for blob in matching_blobs:
            print(f"  📄 {blob.name}")


if __name__ == '__main__':
    main() 