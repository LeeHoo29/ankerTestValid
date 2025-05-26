#!/usr/bin/env python3
"""
Azure Storage 测试脚本
用于验证Azure Storage连接和基本操作
"""
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.azure_storage_client import AzureStorageClient
from config.azure_storage_config import AZURE_STORAGE_CONFIG

def main():
    """主测试函数"""
    print("🗄️ Azure Storage 连接测试")
    print("=" * 50)
    
    # 提示用户输入存储账户名
    print("📝 请输入Azure存储账户名:")
    print("   (如果不知道存储账户名，请联系Azure管理员)")
    storage_account_name = input("存储账户名: ").strip()
    
    if not storage_account_name:
        print("❌ 存储账户名不能为空")
        return
    
    try:
        print(f"\n🔗 尝试连接到存储账户: {storage_account_name}")
        
        # 创建Azure Storage客户端
        client = AzureStorageClient(storage_account_name)
        
        # 测试连接
        print("\n🧪 测试连接...")
        if client.test_connection():
            print("✅ 连接成功!")
            
            # 列出容器
            print("\n📦 列出容器:")
            containers = client.list_containers()
            if containers:
                for container in containers:
                    print(f"   - {container['name']} (修改时间: {container['last_modified']})")
            else:
                print("   没有找到容器")
            
            # 提示后续操作
            print("\n🎉 测试完成!")
            print("📚 接下来可以:")
            print("   1. 查看 notes/azure-storage-guide.md 学习详细操作")
            print("   2. 在代码中使用 AzureStorageClient 进行文件操作")
            print("   3. 参考 src/azure_storage_client.py 中的示例方法")
            
        else:
            print("❌ 连接失败")
            print("🔧 可能的原因:")
            print("   1. 存储账户名不正确")
            print("   2. 认证凭据没有访问该存储账户的权限")
            print("   3. 网络连接问题")
            
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {str(e)}")
        print("🔧 请检查:")
        print("   1. 存储账户名是否正确")
        print("   2. Azure SDK是否正确安装")
        print("   3. 网络连接是否正常")

if __name__ == '__main__':
    main() 