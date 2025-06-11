"""
本地数据库连接配置模块
用于任务映射数据的本地存储
"""

# 本地数据库连接配置
LOCAL_DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',
    'port': 3306,
    'database': 'local_anker_valid',
    'charset': 'utf8mb4',
    'autocommit': True,
    'connect_timeout': 30,
    'read_timeout': 30,
    'write_timeout': 30
}

# 数据库表配置
TABLE_CONFIG = {
    'task_mapping': 'task_mapping',
    'file_details': 'task_file_details'
}

# 应用配置
LOCAL_DEBUG = True
LOCAL_LOG_LEVEL = "INFO" 