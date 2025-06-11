#!/usr/bin/env python3
"""
本地数据库初始化脚本
创建数据库、数据表并提供数据迁移功能
"""
import os
import sys
import json
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db.local_connector import LocalDatabaseConnector
from config.local_db_config import LOCAL_DB_CONFIG


def create_database():
    """创建数据库"""
    import mysql.connector
    from mysql.connector import Error as MySQLError
    
    try:
        # 连接到MySQL服务器（不指定数据库）
        connection_config = LOCAL_DB_CONFIG.copy()
        database_name = connection_config.pop('database')
        
        connection = mysql.connector.connect(**connection_config)
        cursor = connection.cursor()
        
        # 创建数据库
        create_db_query = f"CREATE DATABASE IF NOT EXISTS {database_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        cursor.execute(create_db_query)
        
        print(f"✅ 数据库 '{database_name}' 创建成功或已存在")
        
        cursor.close()
        connection.close()
        
        return True
        
    except MySQLError as err:
        print(f"❌ 创建数据库失败: {err}")
        return False


def create_tables():
    """创建数据表"""
    try:
        db = LocalDatabaseConnector()
        if db.create_tables():
            print("✅ 数据表创建成功")
            return True
        else:
            print("❌ 数据表创建失败")
            return False
    except Exception as e:
        print(f"❌ 创建数据表失败: {str(e)}")
        return False


def migrate_from_json(json_file_path: str = 'data/output/task_mapping.json'):
    """从现有的JSON文件迁移数据到数据库"""
    if not os.path.exists(json_file_path):
        print(f"⚠️  JSON文件不存在: {json_file_path}")
        return True  # 没有数据需要迁移，不算错误
    
    try:
        # 读取JSON文件
        with open(json_file_path, 'r', encoding='utf-8') as f:
            mapping_data = json.load(f)
        
        if not mapping_data:
            print("📋 JSON文件为空，无需迁移")
            return True
        
        print(f"📊 开始迁移 {len(mapping_data)} 条记录...")
        
        # 连接数据库
        db = LocalDatabaseConnector()
        
        success_count = 0
        error_count = 0
        
        for job_id, task_info in mapping_data.items():
            try:
                # 准备数据
                task_type = task_info.get('task_type', 'Unknown')
                actual_task_id = task_info.get('actual_task_id', '')
                relative_path = task_info.get('relative_path', '')
                
                # 计算完整路径
                if relative_path.startswith('./'):
                    full_path = f"data/output/{relative_path[2:]}"
                else:
                    full_path = f"data/output/{relative_path}"
                
                # 检查目录是否存在并统计文件
                file_count = 0
                has_parse_file = False
                if os.path.exists(full_path):
                    files = [f for f in os.listdir(full_path) if os.path.isfile(os.path.join(full_path, f))]
                    file_count = len(files)
                    has_parse_file = any(f.name == 'parse_result.json' for f in Path(full_path).iterdir() if f.is_file())
                
                # 插入数据库记录
                mapping_id = db.insert_task_mapping(
                    job_id=job_id,
                    task_type=task_type,
                    actual_task_id=actual_task_id,
                    relative_path=relative_path,
                    full_path=full_path,
                    file_count=file_count,
                    has_parse_file=has_parse_file,
                    download_method='azure_storage',
                    status='success'
                )
                
                if mapping_id:
                    # 如果目录存在，插入文件详情
                    if os.path.exists(full_path):
                        files_info = []
                        for file_path in Path(full_path).iterdir():
                            if file_path.is_file():
                                file_type = 'parse' if file_path.name == 'parse_result.json' else 'original'
                                files_info.append({
                                    'file_name': file_path.name,
                                    'file_type': file_type,
                                    'file_size': file_path.stat().st_size,
                                    'file_path': str(file_path),
                                    'download_success': True
                                })
                        
                        if files_info:
                            db.insert_file_details(mapping_id, files_info)
                    
                    success_count += 1
                    print(f"  ✅ {job_id} -> {task_type}")
                else:
                    error_count += 1
                    print(f"  ❌ {job_id} -> 插入失败")
                    
            except Exception as e:
                error_count += 1
                print(f"  ❌ {job_id} -> 错误: {str(e)}")
        
        db.disconnect()
        
        print(f"\n📊 迁移完成:")
        print(f"  ✅ 成功: {success_count} 条")
        print(f"  ❌ 失败: {error_count} 条")
        
        return error_count == 0
        
    except Exception as e:
        print(f"❌ 迁移失败: {str(e)}")
        return False


def test_connection():
    """测试数据库连接"""
    try:
        db = LocalDatabaseConnector()
        if db.test_connection():
            print("✅ 数据库连接测试成功")
            return True
        else:
            print("❌ 数据库连接测试失败")
            return False
    except Exception as e:
        print(f"❌ 数据库连接测试失败: {str(e)}")
        return False


def main():
    """主函数"""
    print("🚀 本地数据库初始化脚本")
    print("=" * 60)
    
    # 测试连接
    print("\n步骤1: 测试MySQL连接...")
    if not test_connection():
        print("❌ 请检查MySQL服务是否启动，配置是否正确")
        return False
    
    # 创建数据库
    print("\n步骤2: 创建数据库...")
    if not create_database():
        return False
    
    # 创建数据表
    print("\n步骤3: 创建数据表...")
    if not create_tables():
        return False
    
    # 迁移数据
    print("\n步骤4: 迁移现有数据...")
    if not migrate_from_json():
        print("⚠️  数据迁移失败，但不影响后续使用")
    
    print("\n🎉 本地数据库初始化完成!")
    print("\n📋 数据库信息:")
    print(f"  🔗 连接地址: {LOCAL_DB_CONFIG['host']}:{LOCAL_DB_CONFIG['port']}")
    print(f"  📊 数据库名: {LOCAL_DB_CONFIG['database']}")
    print(f"  👤 用户名: {LOCAL_DB_CONFIG['user']}")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 