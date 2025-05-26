#!/usr/bin/env python3
"""
analysis_response 字段解析配置
定义不同任务类型的 analysis_response 字段数据结构和解析规则
"""

# 任务类型的 analysis_response 配置
ANALYSIS_RESPONSE_CONFIG = {
    'AmazonReviewStarJob': {
        'enabled': True,  # 是否启用 analysis_response 解析
        'structure': {
            'code_field': 'code',           # 状态码字段名
            'data_field': 'data',           # 数据链接字段名
            'meta_field': 'meta',           # 元数据字段名
            'task_id_field': 'task_id'      # meta中的task_id字段名
        },
        'success_codes': [200],             # 表示成功的状态码列表
        'description': 'Amazon Review Star Job 解析响应配置',
        'example': {
            "code": 200, 
            "data": "https://collector0109.blob.core.windows.net/parse/parse/AmazonReviewStarJob/1910599147004108800/7c5f4199-0512-48e6-993e-7301ccd4d356.json?st=2025-04-11T15%3A24%3A32Z&se=2025-05-11T15%3A24%3A32Z&sp=r&sv=2023-11-03&sr=b&sig=wtG2ei7xFmnS15pqIO0YjhNEsBg/l/xAavtHOuZt1Bs%3D", 
            "meta": {
                "task_id": "1910599147004108800"
            }
        }
    },
    'AmazonListingJob': {
        'enabled': True,  # 启用 analysis_response 解析
        'structure': {
            'code_field': 'code',           # 状态码字段名
            'data_field': 'data',           # 数据链接字段名
            'meta_field': 'meta',           # 元数据字段名
            'task_id_field': 'task_id'      # meta中的task_id字段名
        },
        'success_codes': [200],             # 表示成功的状态码列表
        'description': 'Amazon Listing Job 解析响应配置',
        'example': {
            "code": 200,
            "data": "https://collector0109.blob.core.windows.net/parse/parse/AmazonListingJob/1925464700260720640/9f700f05-4e10-4cff-8c69-4562b19e15a7.json?st=2025-05-23T03%3A39%3A07Z&se=2025-06-22T03%3A39%3A07Z&sp=r&sv=2023-11-03&sr=b&sig=7PoXG%2BWHlnUQc4NlqnDy7Hgt%2Blqeht1iUwWaeRcDcHo%3D",
            "meta": {
                "task_id": "1925464700260720640",
                "snapshot_url": "http://voc-prod-collector-v2.shulex.com/parse/unpack?url=https%3A%2F%2Fyiya0110.blob.core.windows.net%2Fdownload%2Fcompress%2FAmazonListingJob%2F1925464700260720640%2Fnormal.gz%3Fst%3D2025-05-23T03%253A39%253A06Z%26se%3D2025-06-22T03%253A39%253A06Z%26sp%3Dr%26sv%3D2023-11-03%26sr%3Db%26sig%3DbWuspi2dq3Zjb85q2a%2Fb3326Hg6xMprnnV%2FTb0cvUbg%253D",
                "login_snapshot_url": "http://voc-prod-collector-v2.shulex.com/parse/unpack?url="
            }
        }
    }
    # 可以根据需要添加其他任务类型的配置
    # 'AmazonListingJob': {
    #     'enabled': False,
    #     'description': 'Amazon Listing Job 暂未启用 analysis_response 解析'
    # }
}


def get_analysis_response_config(task_type: str) -> dict:
    """
    获取指定任务类型的 analysis_response 配置
    
    Args:
        task_type: 任务类型，如 'AmazonReviewStarJob'
        
    Returns:
        dict: 配置字典，如果任务类型未配置则返回默认配置
    """
    default_config = {
        'enabled': False,
        'description': f'任务类型 {task_type} 未配置 analysis_response 解析'
    }
    
    return ANALYSIS_RESPONSE_CONFIG.get(task_type, default_config)


def is_analysis_response_enabled(task_type: str) -> bool:
    """
    检查指定任务类型是否启用了 analysis_response 解析
    
    Args:
        task_type: 任务类型
        
    Returns:
        bool: 启用返回True，否则返回False
    """
    config = get_analysis_response_config(task_type)
    return config.get('enabled', False)


def parse_analysis_response(task_type: str, analysis_response_json: str) -> dict:
    """
    解析 analysis_response JSON字符串
    
    Args:
        task_type: 任务类型
        analysis_response_json: analysis_response JSON字符串
        
    Returns:
        dict: 解析结果，包含 success, download_url, task_id, error 等字段
    """
    result = {
        'success': False,
        'download_url': None,
        'task_id': None,
        'error': None
    }
    
    config = get_analysis_response_config(task_type)
    
    if not config.get('enabled', False):
        result['error'] = f'任务类型 {task_type} 未启用 analysis_response 解析'
        return result
    
    try:
        import json
        response_data = json.loads(analysis_response_json)
        
        structure = config.get('structure', {})
        success_codes = config.get('success_codes', [200])
        
        # 获取状态码
        code_field = structure.get('code_field', 'code')
        code = response_data.get(code_field)
        
        if code not in success_codes:
            result['error'] = f'状态码 {code} 不在成功码列表 {success_codes} 中'
            return result
        
        # 获取下载链接
        data_field = structure.get('data_field', 'data')
        download_url = response_data.get(data_field)
        
        if not download_url:
            result['error'] = f'字段 {data_field} 中未找到下载链接'
            return result
        
        # 获取task_id（如果存在）
        meta_field = structure.get('meta_field', 'meta')
        task_id_field = structure.get('task_id_field', 'task_id')
        
        meta_data = response_data.get(meta_field, {})
        if isinstance(meta_data, dict):
            task_id = meta_data.get(task_id_field)
        else:
            task_id = None
        
        result.update({
            'success': True,
            'download_url': download_url,
            'task_id': task_id
        })
        
        return result
        
    except json.JSONDecodeError as e:
        result['error'] = f'JSON解析失败: {str(e)}'
        return result
    except Exception as e:
        result['error'] = f'解析analysis_response失败: {str(e)}'
        return result 