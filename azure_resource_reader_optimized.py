#!/usr/bin/env python3
"""
Azure Storage 资源读取器 - 优化版本包装器
在 --with-parse 模式下自动使用优化版本，其他模式使用原版本
"""
import sys
import subprocess
from pathlib import Path

def main():
    """主函数：根据参数决定使用优化版本还是原版本"""
    
    # 检查是否使用 --with-parse 模式
    if '--with-parse' in sys.argv:
        print("🚀 检测到 --with-parse 模式，使用优化版本...")
        
        # 移除 --with-parse 参数，因为优化版本不需要这个参数
        args = [arg for arg in sys.argv[1:] if arg != '--with-parse']
        
        # 调用优化版本
        cmd = ['python3', 'src/azure_resource_reader_with_parse_optimization.py'] + args
        result = subprocess.run(cmd)
        sys.exit(result.returncode)
    else:
        # 使用原版本
        cmd = ['python3', 'src/azure_resource_reader.py'] + sys.argv[1:]
        result = subprocess.run(cmd)
        sys.exit(result.returncode)

if __name__ == '__main__':
    main() 