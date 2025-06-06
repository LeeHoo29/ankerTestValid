#!/usr/bin/env python3
"""
任务统计配置文件
包含数据库分表、任务类型、租户信息等配置
"""

# 数据库分表配置
DATABASE_TABLES = [
    'job_a',
    'job_b', 
    'job_c',
    'job_d'
]

# 任务类型配置
TASK_TYPES = [
    'AmazonListingJob',
    'AmazonReviewStarJob',
    'AmazonReviewJob',
    'AmazonSearchRankJob',
    'AmazonTop100Job',
    'AmazonSearchrankSponsorJob',
    'GoogleSearchJob'
]

# 租户配置
TENANT_CONFIG = [
    {
        'id': 'ShulexTicket',
        'app_id': '3qbbyha7ht6snrmd',
        'header_token': 'Q&dMRF5Y#gCfxoMp',
        'display_name': 'Shulex Ticket'
    },
    {
        'id': 'Anker',
        'app_id': 'cnetlsmxfkcke9q7',
        'header_token': 'jE@#tkHo!T9R?!sJ',
        'display_name': 'Anker'
    },
    {
        'id': 'AnkerATIT',
        'app_id': 'X4Yc2ZtXjFSvqczM',
        'header_token': 'hW1ZccW&D^zWOvtC',
        'display_name': 'Anker ATIT'
    },
    {
        'id': 'AnkerCS',
        'app_id': 'ihHijWWkNZNpNKIA',
        'header_token': 'dTXuo@3jMYFzToj$',
        'display_name': 'Anker CS'
    }
]

# 统计查询SQL模板
SQL_TEMPLATES = {
    # 失败/超时总数
    'failed_timeout_count': """
        SELECT 
            COUNT(*) as count,
            DATE(created_at) AS date,
            type as task_type
        FROM {table} 
        WHERE created_at >= %s 
            AND created_at <= %s
            AND tenant_id IN ({tenant_ids})
            AND type IN ({task_types})
            AND (
                (break_at < DATE_FORMAT(UTC_TIMESTAMP(), '%%Y-%%m-%%d %%H:%%i:%%s')
                    AND (deliver_at IS NULL OR deliver_at > break_at)
                    AND `status` != "FAILED") 
                OR `status` = "FAILED"
            )
        GROUP BY date, task_type
        ORDER BY date DESC, task_type
    """,
    
    # 失败总数
    'failed_count': """
        SELECT 
            COUNT(*) as count,
            DATE(created_at) AS date,
            type as task_type
        FROM {table} 
        WHERE created_at >= %s 
            AND created_at <= %s
            AND tenant_id IN ({tenant_ids})
            AND type IN ({task_types})
            AND `status` = "FAILED"
        GROUP BY date, task_type
        ORDER BY date DESC, task_type
    """,
    
    # 超时总数
    'timeout_count': """
        SELECT 
            COUNT(*) as count,
            DATE(created_at) AS date,
            type as task_type
        FROM {table} 
        WHERE created_at >= %s 
            AND created_at <= %s
            AND tenant_id IN ({tenant_ids})
            AND type IN ({task_types})
            AND break_at < DATE_FORMAT(UTC_TIMESTAMP(), '%%Y-%%m-%%d %%H:%%i:%%s')
            AND (deliver_at IS NULL OR deliver_at > break_at)
            AND `status` != "FAILED"
        GROUP BY date, task_type
        ORDER BY date DESC, task_type
    """,
    
    # 超时未完成（已超时且未完成）
    'timeout_not_succeed': """
        SELECT 
            COUNT(*) as count,
            DATE(created_at) AS date,
            type as task_type
        FROM {table} 
        WHERE created_at >= %s 
            AND created_at <= %s
            AND tenant_id IN ({tenant_ids})
            AND type IN ({task_types})
            AND break_at < DATE_FORMAT(UTC_TIMESTAMP(), '%%Y-%%m-%%d %%H:%%i:%%s')
            AND deliver_at IS NULL
            AND `status` != "FAILED"
        GROUP BY date, task_type
        ORDER BY date DESC, task_type
    """,
    
    # 总数
    'total_count': """
        SELECT 
            COUNT(*) as count,
            DATE(created_at) AS date,
            type as task_type
        FROM {table} 
        WHERE created_at >= %s 
            AND created_at <= %s
            AND tenant_id IN ({tenant_ids})
            AND type IN ({task_types})
        GROUP BY date, task_type
        ORDER BY date DESC, task_type
    """,
    
    # 合并查询模板（一次查询获取所有统计）
    'combined_statistics': """
        SELECT 
            DATE(a.created_at) AS date,
            a.type as task_type,
            COUNT(*) as total_count,
            SUM(CASE WHEN a.status = 'FAILED' THEN 1 ELSE 0 END) as failed_count,
            SUM(CASE WHEN a.break_at < %s 
                     AND (a.deliver_at IS NULL OR a.deliver_at > a.break_at)
                     AND a.status != 'FAILED' THEN 1 ELSE 0 END) as timeout_count,
            SUM(CASE WHEN a.deliver_at IS NOT NULL AND a.status != 'FAILED' THEN 1 ELSE 0 END) as succeed_count,
            SUM(CASE WHEN a.break_at < %s 
                     AND a.deliver_at IS NOT NULL 
                     AND a.deliver_at > a.break_at
                     AND a.status != 'FAILED' THEN 1 ELSE 0 END) as timeout_but_succeed,
            SUM(CASE WHEN (a.break_at >= %s OR a.break_at IS NULL)
                     AND a.deliver_at IS NOT NULL 
                     AND a.status != 'FAILED' THEN 1 ELSE 0 END) as succeed_not_timeout,
            SUM(CASE WHEN a.break_at < %s 
                     AND a.deliver_at IS NULL
                     AND a.status != 'FAILED' THEN 1 ELSE 0 END) as timeout_not_succeed
        FROM {table} a
        WHERE a.created_at >= %s 
            AND a.created_at <= %s
            AND a.tenant_id IN ({tenant_ids})
            AND a.type IN ({task_types})
        GROUP BY date, task_type
        ORDER BY date DESC, task_type
    """
}


def get_tenant_by_id(tenant_id: str) -> dict:
    """
    根据租户ID获取租户配置
    
    Args:
        tenant_id: 租户ID
        
    Returns:
        dict: 租户配置，如果未找到返回None
    """
    for tenant in TENANT_CONFIG:
        if tenant['id'] == tenant_id:
            return tenant
    return None


def get_all_tenant_ids() -> list:
    """
    获取所有租户ID列表
    
    Returns:
        list: 租户ID列表
    """
    return [tenant['id'] for tenant in TENANT_CONFIG]


def format_sql_placeholders(items: list) -> str:
    """
    格式化SQL占位符
    
    Args:
        items: 项目列表
        
    Returns:
        str: 格式化的占位符字符串
    """
    return ','.join(['%s'] * len(items))


def get_sql_template(template_name: str, table: str, tenant_ids: list, task_types: list) -> str:
    """
    获取格式化的SQL模板
    
    Args:
        template_name: 模板名称
        table: 表名
        tenant_ids: 租户ID列表
        task_types: 任务类型列表
        
    Returns:
        str: 格式化的SQL语句
    """
    if template_name not in SQL_TEMPLATES:
        raise ValueError(f"未知的SQL模板: {template_name}")
    
    template = SQL_TEMPLATES[template_name]
    
    # 格式化占位符
    tenant_placeholders = format_sql_placeholders(tenant_ids)
    task_type_placeholders = format_sql_placeholders(task_types)
    
    return template.format(
        table=table,
        tenant_ids=tenant_placeholders,
        task_types=task_type_placeholders
    )


# 统一配置对象，方便导入使用
TASK_STATISTICS_CONFIG = {
    'tables': DATABASE_TABLES,
    'task_types': TASK_TYPES,
    'tenants': TENANT_CONFIG,
    'sql_templates': SQL_TEMPLATES
} 