#!/usr/bin/env python3
"""
清理重复的解析文件映射
移除 --with-parse 模式下生成的重复 _parse 映射
"""
import json
import os
from pathlib import Path
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def clean_duplicate_mappings(mapping_file_path: str = 'data/output/task_mapping.json'):
    """
    清理重复的解析文件映射
    
    Args:
        mapping_file_path: 映射文件路径
    """
    if not os.path.exists(mapping_file_path):
        print(f"❌ 映射文件不存在: {mapping_file_path}")
        return False
    
    print(f"🔍 清理重复映射: {mapping_file_path}")
    print("=" * 60)
    
    try:
        # 读取现有映射
        with open(mapping_file_path, 'r', encoding='utf-8') as f:
            mapping = json.load(f)
        
        # 查找需要移除的 _parse 映射
        keys_to_remove = []
        parse_mappings = {}
        
        for key, info in mapping.items():
            if key.endswith('_parse'):
                base_key = key[:-6]  # 移除 '_parse' 后缀
                if base_key in mapping:
                    # 检查是否为 --with-parse 模式的重复映射
                    base_info = mapping[base_key]
                    parse_info = info
                    
                    # 如果解析文件映射的任务类型和ID与原始映射相同，则为重复
                    if (parse_info.get('task_type') == 'parse' and
                        parse_info.get('job_id') == base_info.get('task_type') and
                        parse_info.get('task_id') == base_info.get('actual_task_id')):
                        
                        keys_to_remove.append(key)
                        parse_mappings[key] = {
                            'base_key': base_key,
                            'base_path': base_info.get('relative_path'),
                            'parse_path': parse_info.get('relative_path')
                        }
        
        # 显示将要移除的映射
        if keys_to_remove:
            print(f"📋 发现 {len(keys_to_remove)} 个重复的解析映射:")
            for key in keys_to_remove:
                info = parse_mappings[key]
                print(f"  🗑️  {key}")
                print(f"     原始映射: {info['base_key']} -> {info['base_path']}")
                print(f"     重复映射: {key} -> {info['parse_path']}")
                print(f"     说明: 解析文件已在原始目录中")
                print()
            
            # 移除重复映射
            for key in keys_to_remove:
                del mapping[key]
            
            # 保存清理后的映射
            with open(mapping_file_path, 'w', encoding='utf-8') as f:
                json.dump(mapping, f, indent=2, ensure_ascii=False)
            
            print(f"✅ 成功移除 {len(keys_to_remove)} 个重复映射")
            print(f"📄 更新后的映射文件: {mapping_file_path}")
            
        else:
            print("✅ 未发现重复映射，无需清理")
        
        # 显示清理后的统计
        print(f"\n📊 清理后统计:")
        print(f"  总映射数量: {len(mapping)}")
        
        # 按类型分组统计
        original_count = 0
        parse_only_count = 0
        
        for key, info in mapping.items():
            if info.get('task_type') == 'parse':
                parse_only_count += 1
            else:
                original_count += 1
        
        print(f"  原始文件映射: {original_count}")
        print(f"  纯解析映射: {parse_only_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ 清理映射失败: {str(e)}")
        return False

def main():
    """主函数"""
    print("🧹 清理重复解析文件映射工具")
    print("=" * 60)
    print("说明: 在 --with-parse 模式下，解析文件和原始文件保存在同一目录")
    print("      因此不需要单独的 _parse 映射")
    print()
    
    # 清理默认映射文件
    success = clean_duplicate_mappings()
    
    if success:
        print("\n🎉 清理完成!")
        print("\n💡 现在映射更简洁:")
        print("  输入参数 -> 统一目录（包含原始文件和解析文件）")
        print("  例如: 2829160096 -> ./AmazonReviewStarJob/1925096011652927488/")
        print("       包含: page_1.html, page_2.html, parse_result.json")
    else:
        print("\n❌ 清理失败")

if __name__ == '__main__':
    main() 