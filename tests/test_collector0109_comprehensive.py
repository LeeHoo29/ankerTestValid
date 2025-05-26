#!/usr/bin/env python3
"""
collector0109 存储账户全面测试
修复API问题并全面搜索指定task_id的文件
支持命令行参数输入任务类型和任务ID
"""
import sys
import os
import argparse
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


def test_specific_paths_fixed(reader, task_type, task_id):
    """测试特定路径（修复版本）"""
    print(f"\n🔍 测试特定路径（修复版本）")
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
            print(f"  搜索路径: {prefix}")
            # 修复：不使用max_results参数
            blobs = []
            blob_iter = container_client.list_blobs(name_starts_with=prefix)
            
            # 手动限制结果数量
            count = 0
            for blob in blob_iter:
                blobs.append(blob)
                count += 1
                if count >= 10:  # 限制为10个结果
                    break
            
            results[prefix] = blobs
            print(f"    结果: {len(blobs)} 个文件")
            
            if blobs:
                for i, blob in enumerate(blobs[:3]):  # 只显示前3个
                    print(f"      📄 {blob.name}")
                    print(f"         📊 大小: {blob.size} 字节")
                if len(blobs) > 3:
                    print(f"      ... 还有 {len(blobs) - 3} 个文件")
            print()
            
        except Exception as e:
            print(f"    错误: {e}")
            results[prefix] = []
    
    return results


def search_task_id_broadly(reader, task_id):
    """广泛搜索包含task_id的文件"""
    print(f"\n🔍 广泛搜索包含task_id {task_id}的文件")
    print("=" * 60)
    
    try:
        container_client = reader.blob_service_client.get_container_client('parse')
        
        # 搜索不同的可能路径前缀
        search_prefixes = [
            "parse/parse/",
            "parse/",
            "",  # 搜索根目录
        ]
        
        all_matches = []
        
        for prefix in search_prefixes:
            print(f"  搜索前缀: '{prefix}'")
            try:
                blob_iter = container_client.list_blobs(name_starts_with=prefix)
                
                matches = []
                count = 0
                for blob in blob_iter:
                    if task_id in blob.name:
                        matches.append(blob)
                        print(f"    ✅ 找到: {blob.name}")
                        print(f"       📊 大小: {blob.size} 字节")
                        print(f"       📅 修改: {blob.last_modified}")
                        print()
                    
                    count += 1
                    # 限制搜索范围，避免超时
                    if count >= 1000:
                        print(f"    ⚠️  已搜索 {count} 个文件，停止搜索此前缀")
                        break
                
                all_matches.extend(matches)
                print(f"    前缀 '{prefix}' 找到 {len(matches)} 个匹配文件")
                print()
                
            except Exception as e:
                print(f"    前缀 '{prefix}' 搜索失败: {e}")
                print()
        
        return all_matches
        
    except Exception as e:
        print(f"❌ 广泛搜索失败: {e}")
        return []


def search_task_type_files(reader, task_type):
    """搜索指定任务类型相关的所有文件"""
    print(f"\n🔍 搜索{task_type}相关文件")
    print("=" * 60)
    
    try:
        container_client = reader.blob_service_client.get_container_client('parse')
        
        search_prefixes = [
            f"parse/parse/{task_type}/",
            f"parse/{task_type}/",
            f"{task_type}/",
        ]
        
        all_matches = []
        
        for prefix in search_prefixes:
            print(f"  搜索前缀: '{prefix}'")
            try:
                blob_iter = container_client.list_blobs(name_starts_with=prefix)
                
                matches = []
                count = 0
                for blob in blob_iter:
                    matches.append(blob)
                    if count < 5:  # 只显示前5个
                        print(f"    📄 {blob.name}")
                        print(f"       📊 大小: {blob.size} 字节")
                        print(f"       📅 修改: {blob.last_modified}")
                        print()
                    
                    count += 1
                    # 限制搜索数量
                    if count >= 20:
                        break
                
                all_matches.extend(matches)
                print(f"    前缀 '{prefix}' 找到 {len(matches)} 个文件")
                if len(matches) > 5:
                    print(f"    （只显示了前5个文件）")
                print()
                
            except Exception as e:
                print(f"    前缀 '{prefix}' 搜索失败: {e}")
                print()
        
        return all_matches
        
    except Exception as e:
        print(f"❌ {task_type}搜索失败: {e}")
        return []


def analyze_path_structure(reader):
    """分析parse容器的路径结构"""
    print(f"\n🔍 分析parse容器的路径结构")
    print("=" * 60)
    
    try:
        container_client = reader.blob_service_client.get_container_client('parse')
        
        # 获取根目录下的前几个文件来分析结构
        blob_iter = container_client.list_blobs()
        
        print("  根目录下的文件结构样例:")
        count = 0
        path_patterns = set()
        
        for blob in blob_iter:
            if count < 10:
                print(f"    📄 {blob.name}")
                
                # 分析路径模式
                parts = blob.name.split('/')
                if len(parts) >= 3:
                    pattern = '/'.join(parts[:3]) + '/...'
                    path_patterns.add(pattern)
            
            count += 1
            if count >= 50:  # 只分析前50个文件
                break
        
        print(f"\n  发现的路径模式:")
        for pattern in sorted(path_patterns):
            print(f"    🔍 {pattern}")
        
        print(f"\n  总共分析了 {count} 个文件")
        
    except Exception as e:
        print(f"❌ 路径结构分析失败: {e}")


def test_download_sample_file(reader, task_type, task_id, blobs):
    """测试下载示例文件"""
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
        output_dir = Path(f"data/test_output/{task_type}/{task_id}")
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
    parser = argparse.ArgumentParser(
        description='collector0109 存储账户全面测试',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 测试指定的任务类型和任务ID
  python3 tests/test_collector0109_comprehensive.py AmazonReviewStarJob 1910598939612549120
  
  # 测试其他任务类型
  python3 tests/test_collector0109_comprehensive.py AmazonListingJob 1925464883027513344
  
  # 只下载示例文件（不进行广泛搜索）
  python3 tests/test_collector0109_comprehensive.py AmazonReviewStarJob 1910598939612549120 --download-only
        """
    )
    
    parser.add_argument('task_type', 
                       help='任务类型，如: AmazonReviewStarJob, AmazonListingJob')
    parser.add_argument('task_id', 
                       help='任务ID（长数字串），如: 1910598939612549120')
    parser.add_argument('--download-only', '-d',
                       action='store_true',
                       help='只下载找到的文件，不进行广泛搜索（更快）')
    parser.add_argument('--no-download', '-n',
                       action='store_true',
                       help='不下载文件，只显示文件信息')
    
    args = parser.parse_args()
    
    task_type = args.task_type
    task_id = args.task_id
    
    print("🧪 collector0109 存储账户全面测试")
    print("=" * 80)
    print(f"目标任务类型: {task_type}")
    print(f"目标任务ID: {task_id}")
    print(f"预期路径: parse/parse/{task_type}/{task_id}/")
    
    # 1. 测试连接
    reader = test_collector0109_connection()
    if not reader:
        return
    
    # 2. 分析路径结构（如果不是只下载模式）
    if not args.download_only:
        analyze_path_structure(reader)
    
    # 3. 测试特定路径（修复版本）
    path_results = test_specific_paths_fixed(reader, task_type, task_id)
    
    # 4. 广泛搜索task_id（如果不是只下载模式）
    task_matches = []
    if not args.download_only:
        task_matches = search_task_id_broadly(reader, task_id)
    
    # 5. 搜索任务类型相关文件（如果不是只下载模式）
    type_matches = []
    if not args.download_only:
        type_matches = search_task_type_files(reader, task_type)
    
    # 6. 如果找到文件且未禁用下载，测试下载
    found_files = []
    for path, blobs in path_results.items():
        found_files.extend(blobs)
    
    if found_files and not args.no_download:
        test_download_sample_file(reader, task_type, task_id, found_files)
    
    # 总结
    print("\n" + "=" * 80)
    print("📊 测试总结")
    print("=" * 80)
    print(f"目标路径: parse/parse/{task_type}/{task_id}/")
    
    # 显示各路径变体的结果
    print("\n🎯 特定路径测试结果:")
    total_found = 0
    for path, blobs in path_results.items():
        print(f"  {path}: {len(blobs)} 个文件")
        total_found += len(blobs)
    
    if not args.download_only:
        print(f"\n🔍 task_id搜索结果: {len(task_matches)} 个匹配文件")
        print(f"🔍 {task_type}搜索结果: {len(type_matches)} 个相关文件")
        
        if task_matches:
            print("\n✅ 找到包含task_id的文件:")
            for match in task_matches:
                print(f"  📄 {match.name}")
    
    if total_found > 0 or task_matches:
        print("\n✅ 确认：找到了相关文件！")
        if found_files:
            print("🎯 在特定路径下找到的文件:")
            for blob in found_files[:5]:  # 只显示前5个
                print(f"  📄 {blob.name}")
            if len(found_files) > 5:
                print(f"  ... 还有 {len(found_files) - 5} 个文件")
    else:
        print("\n❌ 未找到指定task_id的文件")
        print("💡 建议检查:")
        print("   1. task_id是否正确")
        print("   2. 文件是否存在于其他路径结构中")
        print("   3. 是否需要搜索其他容器")


if __name__ == '__main__':
    main() 