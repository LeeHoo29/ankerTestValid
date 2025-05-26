#!/usr/bin/env python3
"""
collector0109 存储账户专项测试
专门测试特定路径下的解析文件
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


def test_specific_path_direct(reader, task_type, task_id):
    """直接测试特定路径下的文件"""
    print(f"\n🔍 直接测试路径: parse/parse/{task_type}/{task_id}/")
    print("=" * 60)
    
    try:
        container_client = reader.blob_service_client.get_container_client('parse')
        prefix = f"parse/parse/{task_type}/{task_id}/"
        print(f"  搜索前缀: {prefix}")
        
        # 限制结果数量，避免超时
        blobs = list(container_client.list_blobs(name_starts_with=prefix, max_results=100))
        
        if blobs:
            print(f"✅ 找到 {len(blobs)} 个文件:")
            for i, blob in enumerate(blobs):
                print(f"  📄 [{i+1}] {blob.name}")
                print(f"      📊 大小: {blob.size} 字节")
                print(f"      📅 修改: {blob.last_modified}")
                print()
                
                # 只显示前10个文件，避免输出过多
                if i >= 9:
                    if len(blobs) > 10:
                        print(f"  ... 还有 {len(blobs) - 10} 个文件")
                    break
        else:
            print("❌ 未找到文件")
            
        return blobs
        
    except Exception as e:
        print(f"❌ 测试特定路径失败: {e}")
        return []


def test_path_variations_focused(reader, task_type, task_id):
    """测试不同的路径变体（限制结果）"""
    print(f"\n🔍 测试路径变体（限制结果）")
    print("=" * 60)
    
    path_variations = [
        f"parse/parse/{task_type}/{task_id}/",
        f"parse/parse/{task_type}/{task_id}",
        f"parse/{task_type}/{task_id}/",
        f"parse/{task_type}/{task_id}",
    ]
    
    container_client = reader.blob_service_client.get_container_client('parse')
    results = {}
    
    for prefix in path_variations:
        try:
            blobs = list(container_client.list_blobs(name_starts_with=prefix, max_results=5))
            results[prefix] = blobs
            print(f"  路径: {prefix}")
            print(f"  结果: {len(blobs)} 个文件")
            if blobs:
                for blob in blobs[:3]:  # 只显示前3个
                    print(f"    📄 {blob.name}")
            print()
        except Exception as e:
            print(f"  路径: {prefix} - 错误: {e}")
            results[prefix] = []
    
    return results


def test_existing_method(reader, task_type, task_id):
    """测试现有的list_parse_files方法"""
    print(f"\n🔍 测试现有的list_parse_files方法")
    print("=" * 60)
    
    try:
        files = reader.list_parse_files(task_type, task_id)
        
        if files:
            print(f"✅ 现有方法找到 {len(files)} 个文件:")
            for i, file_info in enumerate(files):
                print(f"  📄 [{i+1}] {file_info['name']}")
                print(f"      📊 大小: {file_info['size']} 字节")
                print(f"      📅 修改: {file_info['last_modified']}")
                print()
                
                # 只显示前5个文件
                if i >= 4:
                    if len(files) > 5:
                        print(f"  ... 还有 {len(files) - 5} 个文件")
                    break
        else:
            print("❌ 现有方法未找到文件")
            
        return files
        
    except Exception as e:
        print(f"❌ 测试现有方法失败: {e}")
        return []


def test_sample_file_download(reader, task_type, task_id, blobs):
    """测试下载一个示例文件"""
    if not blobs:
        print("\n❌ 没有文件可供下载测试")
        return
        
    print(f"\n🔍 测试下载示例文件")
    print("=" * 60)
    
    # 选择第一个文件进行下载测试
    sample_blob = blobs[0]
    print(f"  选择文件: {sample_blob.name}")
    
    try:
        # 创建输出目录
        output_dir = Path("data/test_output")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 获取文件名
        file_name = Path(sample_blob.name).name
        output_path = output_dir / file_name
        
        # 下载文件
        container_client = reader.blob_service_client.get_container_client('parse')
        blob_client = container_client.get_blob_client(sample_blob.name)
        
        with open(output_path, 'wb') as f:
            download_stream = blob_client.download_blob()
            f.write(download_stream.readall())
        
        print(f"✅ 文件下载成功: {output_path}")
        print(f"   文件大小: {output_path.stat().st_size} 字节")
        
        # 显示文件内容的前几行（如果是文本文件）
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read(500)  # 读取前500个字符
                print(f"   文件内容预览:")
                print("   " + "-" * 40)
                for line in content.split('\n')[:5]:  # 显示前5行
                    print(f"   {line}")
                if len(content) >= 500:
                    print("   ...")
                print("   " + "-" * 40)
        except:
            print("   文件内容无法以文本形式显示（可能是二进制文件）")
            
        return output_path
        
    except Exception as e:
        print(f"❌ 下载文件失败: {e}")
        return None


def main():
    """主测试函数"""
    print("🧪 collector0109 存储账户专项测试")
    print("=" * 80)
    
    # 测试参数
    task_type = "AmazonReviewStarJob"
    task_id = "1910598939612549120"
    
    print(f"目标任务类型: {task_type}")
    print(f"目标任务ID: {task_id}")
    print(f"预期路径: parse/parse/{task_type}/{task_id}/")
    
    # 1. 测试连接
    reader = test_collector0109_connection()
    if not reader:
        return
    
    # 2. 测试现有方法
    existing_files = test_existing_method(reader, task_type, task_id)
    
    # 3. 直接测试特定路径
    direct_blobs = test_specific_path_direct(reader, task_type, task_id)
    
    # 4. 测试路径变体
    path_results = test_path_variations_focused(reader, task_type, task_id)
    
    # 5. 如果找到文件，测试下载
    if direct_blobs:
        test_sample_file_download(reader, task_type, task_id, direct_blobs)
    
    # 总结
    print("\n" + "=" * 80)
    print("📊 测试总结")
    print("=" * 80)
    print(f"目标路径: parse/parse/{task_type}/{task_id}/")
    print(f"现有方法找到文件数: {len(existing_files)}")
    print(f"直接查询找到文件数: {len(direct_blobs)}")
    
    # 显示各路径变体的结果
    print("\n🎯 路径变体测试结果:")
    for path, blobs in path_results.items():
        print(f"  {path}: {len(blobs)} 个文件")
    
    if direct_blobs:
        print("\n✅ 确认：该路径下确实存在文件！")
        print("🎯 实际存在的文件:")
        for i, blob in enumerate(direct_blobs[:5]):  # 只显示前5个
            print(f"  📄 {blob.name}")
        if len(direct_blobs) > 5:
            print(f"  ... 还有 {len(direct_blobs) - 5} 个文件")
    else:
        print("\n❌ 该路径下未找到文件")


if __name__ == '__main__':
    main() 