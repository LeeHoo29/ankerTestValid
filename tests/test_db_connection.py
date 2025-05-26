#!/usr/bin/env python3
"""
数据库连接测试模块
"""
import os
import sys
import unittest
from pathlib import Path

# 添加项目根目录到系统路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db.connector import DatabaseConnector


class TestDatabaseConnector(unittest.TestCase):
    """数据库连接器测试类"""
    
    def test_connection(self):
        """测试数据库连接"""
        db = DatabaseConnector()
        result = db.test_connection()
        self.assertTrue(result, "数据库连接测试失败")
        
    def test_execute_query(self):
        """测试执行查询"""
        db = DatabaseConnector()
        if not db.connect():
            self.skipTest("数据库连接失败，跳过查询测试")
            
        try:
            # 执行简单查询
            result = db.execute_query("SELECT 1 as test")
            self.assertIsNotNone(result, "查询结果不应为None")
            self.assertEqual(len(result), 1, "查询结果应该有1行")
            self.assertEqual(result[0]['test'], 1, "查询结果应该是1")
            
        finally:
            db.disconnect()
            

if __name__ == '__main__':
    unittest.main() 