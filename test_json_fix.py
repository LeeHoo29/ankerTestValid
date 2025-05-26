#!/usr/bin/env python3
"""
测试JSON文件格式修复
验证解析文件现在正确保存为.json格式
"""
import os
import json
from pathlib import Path

def test_json_files():
    """测试JSON文件是否正确保存"""
    print("🔍 测试JSON文件格式修复")
    print("=" * 50)
    
    # 测试目录
    test_dirs = [
        "data/output/parse/",
        "data/output/AmazonReviewStarJob/",
        "data/examples/parse/"
    ]
    
    json_files_found = []
    non_json_with_json_content = []
    
    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            print(f"\n📂 检查目录: {test_dir}")
            
            # 递归查找所有文件
            for root, dirs, files in os.walk(test_dir):
                for file in files:
                    file_path = Path(root) / file
                    
                    # 检查文件扩展名和内容
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read().strip()
                        
                        # 检查是否为JSON内容
                        is_json_content = False
                        if content.startswith('{') or content.startswith('['):
                            try:
                                json.loads(content)
                                is_json_content = True
                            except json.JSONDecodeError:
                                pass
                        
                        if is_json_content:
                            if file.endswith('.json'):
                                json_files_found.append(str(file_path))
                                print(f"  ✅ {file} - 正确的JSON文件")
                            else:
                                non_json_with_json_content.append(str(file_path))
                                print(f"  ❌ {file} - JSON内容但扩展名错误!")
                        else:
                            print(f"  📄 {file} - 非JSON文件")
                            
                    except Exception as e:
                        print(f"  ⚠️  无法读取 {file}: {e}")
    
    # 总结结果
    print("\n" + "=" * 50)
    print("📊 测试结果总结")
    print("=" * 50)
    
    print(f"✅ 正确的JSON文件数量: {len(json_files_found)}")
    if json_files_found:
        for f in json_files_found:
            print(f"  📄 {f}")
    
    print(f"\n❌ 需要修复的文件数量: {len(non_json_with_json_content)}")
    if non_json_with_json_content:
        for f in non_json_with_json_content:
            print(f"  📄 {f}")
    
    if len(non_json_with_json_content) == 0:
        print("\n🎉 所有JSON内容都正确保存为.json文件!")
    else:
        print(f"\n⚠️  发现 {len(non_json_with_json_content)} 个需要修复的文件")
    
    return len(non_json_with_json_content) == 0

if __name__ == '__main__':
    success = test_json_files()
    exit(0 if success else 1) 