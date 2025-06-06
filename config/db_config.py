"""
数据库连接配置模块
"""
import os
from dotenv import load_dotenv

# 尝试加载.env文件中的环境变量（如果存在）
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# 数据库连接配置
DB_CONFIG = {
    'host': 'azure-shulex-prod-usw3-mysql-1219.mysql.database.azure.com',
    'user': 'yiya_developer_0428',
    'password': 'fAqGLZkH7jdmq',
    'port': 3306,
    'charset': 'utf8mb4',
    'autocommit': True,
    'connect_timeout': 30,
    'read_timeout': 30,
    'write_timeout': 30
}

# 应用配置
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# 重新提交解析任务API配置
REPARSER_API_CONFIG = {
    'url': 'http://voc-prod-collector-v2.shulex.com/job/reparser',
    'x_token': 'jE@#tkHo!T9R?!sJ',
    'headers': {
        'Content-Type': 'application/json',
        'Accept': '*/*',
        'Host': 'voc-prod-collector-v2.shulex.com',
        'Connection': 'keep-alive'
    },
    'timeout': 30
}

# 重新提交爬虫任务API配置
CRAWLER_API_CONFIG = {
    'url': 'http://voc-prod-collector-v2.shulex.com/job/resubmit_failed',
    'x_token': 'jE@#tkHo!T9R?!sJ',
    'headers': {
        'Content-Type': 'application/json',
        'Accept': '*/*',
        'Host': 'voc-prod-collector-v2.shulex.com',
        'Connection': 'keep-alive'
    },
    'timeout': 30
} 