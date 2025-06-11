#!/usr/bin/env python3
"""
任务检查工具看板 - Web界面
统一的任务管理和监控平台
支持多种工具模块，包括Azure Resource Reader等
"""

import os
import subprocess
import threading
import time
import json
import hashlib
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, request, jsonify, session, send_file
from flask_cors import CORS
from pathlib import Path
import uuid
import logging

# 配置日志系统
def setup_logger():
    """设置应用程序日志配置"""
    # 创建logs目录（如果不存在）
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    # 配置日志格式
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # 配置根logger
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            # 控制台输出
            logging.StreamHandler(),
            # 文件输出
            logging.FileHandler(log_dir / 'web_app.log', encoding='utf-8')
        ]
    )
    
    # 创建应用专用logger
    logger = logging.getLogger('web_app')
    return logger

# 初始化logger
logger = setup_logger()

# 导入数据库连接器和配置
from src.db.connector import DatabaseConnector
from config.db_config import DB_CONFIG
from config.task_statistics_config import (
    DATABASE_TABLES, TASK_TYPES, TENANT_CONFIG, 
    get_sql_template, get_all_tenant_ids, TASK_STATISTICS_CONFIG
)

# 添加本地数据库连接器导入
try:
    from src.db.local_connector import LocalDatabaseConnector
    LOCAL_DB_AVAILABLE = True
except ImportError:
    LOCAL_DB_AVAILABLE = False
    logger.warning("⚠️  本地数据库模块不可用，部分功能将被禁用")

app = Flask(__name__)
app.secret_key = 'azure_resource_reader_web_2024'

# 配置CORS，允许前端跨域访问
CORS(app, origins=['http://localhost:3000', 'http://localhost:3001'])

# 全局变量存储任务状态
tasks = {}

# 简单的内存缓存机制
statistics_cache = {}
CACHE_DURATION = 21600  # 缓存6小时（6 * 60 * 60 = 21600秒）

def get_utc_now():
    """获取当前UTC时间字符串"""
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

def convert_to_utc_datetime(date_str, time_str="00:00:00"):
    """
    将日期字符串转换为UTC时间字符串
    
    Args:
        date_str: 日期字符串，格式如 "2025-05-27"
        time_str: 时间字符串，格式如 "00:00:00" 或 "23:59:59"
    
    Returns:
        str: UTC时间字符串，格式如 "2025-05-27 00:00:00"
    """
    return f"{date_str} {time_str}"

def get_timeout_condition(reference_time=None):
    """
    获取超时查询条件
    
    Args:
        reference_time: 参考时间，如果为None则使用当前UTC时间
    
    Returns:
        tuple: (condition_sql, reference_time_value)
    """
    if reference_time is None:
        reference_time = get_utc_now()
    
    condition_sql = """break_at < %s
        AND (deliver_at IS NULL OR deliver_at > break_at)
        AND `status` != 'FAILED'"""
    
    return condition_sql.strip(), reference_time

def clean_sql_for_debug(sql_string):
    """
    清理SQL字符串，去掉换行符和多余空格，方便复制
    """
    if not sql_string:
        return sql_string
    
    # 去掉换行符、制表符和多余空格，保持单行格式
    cleaned = ' '.join(sql_string.replace('\n', ' ').replace('\t', ' ').split())
    return cleaned

def execute_command(task_id, command, working_dir):
    """在后台执行命令"""
    try:
        tasks[task_id]['status'] = 'running'
        tasks[task_id]['start_time'] = datetime.now()
        
        # 执行命令
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=working_dir,
            bufsize=1,
            universal_newlines=True
        )
        
        # 实时读取输出
        output_lines = []
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                line = output.strip()
                output_lines.append(line)
                tasks[task_id]['output'] = '\n'.join(output_lines)
        
        # 获取返回码
        return_code = process.poll()
        
        tasks[task_id]['status'] = 'completed' if return_code == 0 else 'failed'
        tasks[task_id]['return_code'] = return_code
        tasks[task_id]['end_time'] = datetime.now()
        
    except Exception as e:
        tasks[task_id]['status'] = 'error'
        tasks[task_id]['error'] = str(e)
        tasks[task_id]['end_time'] = datetime.now()

def format_timestamp(iso_timestamp):
    """格式化ISO时间戳为易读格式"""
    try:
        if not iso_timestamp:
            return '未知时间'
        
        # 解析ISO格式时间戳
        dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
        
        # 格式化为易读格式: 年-月-日 时:分:秒
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        # 如果解析失败，返回原始字符串
        return iso_timestamp

def read_completed_tasks():
    """读取已完成任务（仅从数据库获取）"""
    try:
        if not LOCAL_DB_AVAILABLE:
            logger.warning("本地数据库不可用，返回空任务列表")
            return []
        
        db = LocalDatabaseConnector()
        
        # 获取所有任务映射
        cursor = db.cursor
        query = """
            SELECT job_id, task_type, actual_task_id, relative_path, 
                   full_path, file_count, has_parse_file, 
                   download_method, status, created_at, updated_at
            FROM task_mapping 
            ORDER BY updated_at DESC
        """
        cursor.execute(query)
        mappings = cursor.fetchall()
        
        completed_tasks = []
        for mapping in mappings:
            # 检查目录是否存在
            full_path = Path(mapping['full_path']) if mapping['full_path'] else None
            directory_exists = full_path.exists() if full_path else False
            
            # 格式化相对路径
            relative_path = mapping['relative_path']
            if relative_path.startswith('./'):
                relative_path = relative_path[2:]
            
            completed_tasks.append({
                'job_id': mapping['job_id'],
                'task_type': mapping['task_type'],
                'actual_task_id': mapping['actual_task_id'],
                'last_updated': format_timestamp(mapping['updated_at'].isoformat() if mapping['updated_at'] else ''),
                'relative_path': relative_path,
                'full_path': str(full_path) if full_path else '',
                'file_count': mapping['file_count'],
                'has_parse_file': mapping['has_parse_file'],
                'directory_exists': directory_exists
            })
        
        db.disconnect()
        return completed_tasks
        
    except Exception as e:
        logger.warning(f"读取任务失败: {str(e)}")
        return []

@app.route('/')
def index():
    """主页面"""
    completed_tasks = read_completed_tasks()
    return render_template('index.html', completed_tasks=completed_tasks)

@app.route('/api/completed_tasks')
def get_completed_tasks():
    """获取已完成任务的API接口（仅从数据库获取）"""
    logger.info("📥 收到获取已完成任务列表请求")
    try:
        if not LOCAL_DB_AVAILABLE:
            logger.warning("本地数据库不可用")
            return jsonify({
                'success': False,
                'error': '本地数据库不可用',
                'tasks': [],
                'total_count': 0
            }), 500
        
        db = LocalDatabaseConnector()
        
        # 确保数据库连接成功
        if not db.connect():
            logger.warning("数据库连接失败")
            return jsonify({
                'success': False,
                'error': '数据库连接失败',
                'tasks': [],
                'total_count': 0
            }), 500
        
        # 获取所有任务映射
        cursor = db.cursor
        if cursor is None:
            logger.warning("获取数据库游标失败")
            db.disconnect()
            return jsonify({
                'success': False,
                'error': '获取数据库游标失败',
                'tasks': [],
                'total_count': 0
            }), 500
            
        query = """
            SELECT job_id, task_type, actual_task_id, relative_path, 
                   full_path, file_count, has_parse_file, 
                   download_method, status, created_at, updated_at
            FROM task_mapping 
            ORDER BY updated_at DESC
        """
        cursor.execute(query)
        mappings = cursor.fetchall()
        
        tasks = []
        for mapping in mappings:
            task = {
                'job_id': mapping['job_id'],
                'task_type': mapping['task_type'],
                'actual_task_id': mapping['actual_task_id'],
                'relative_path': mapping['relative_path'],
                'full_path': mapping['full_path'],
                'file_count': mapping['file_count'],
                'has_parse_file': mapping['has_parse_file'],
                'download_method': mapping['download_method'],
                'status': mapping['status'],
                'last_updated': mapping['updated_at'].isoformat() if mapping['updated_at'] else None,
                'created_at': mapping['created_at'].isoformat() if mapping['created_at'] else None,
                'directory_exists': True  # 兼容前端字段
            }
            tasks.append(task)
        
        db.disconnect()
        
        logger.info(f"✅ 成功返回 {len(tasks)} 个已完成任务")
        return jsonify({
            'success': True,
            'tasks': tasks,
            'total_count': len(tasks),
            'source': 'database'
        })
        
    except Exception as e:
        logger.error(f"获取已完成任务失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'tasks': [],
            'total_count': 0
        }), 500

@app.route('/api/list_files')
def list_files():
    """列出指定目录下的文件"""
    try:
        dir_path = request.args.get('path')
        if not dir_path:
            return jsonify({'success': False, 'error': '缺少路径参数'})
        
        path = Path(dir_path)
        if not path.exists():
            return jsonify({'success': False, 'error': '目录不存在'})
        
        if not path.is_dir():
            return jsonify({'success': False, 'error': '路径不是目录'})
        
        files = []
        for file_path in path.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    'name': file_path.name,
                    'path': str(file_path),
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
                })
        
        # 按名称排序
        files.sort(key=lambda x: x['name'])
        
        return jsonify({
            'success': True,
            'files': files,
            'directory': str(path)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/download_file')
def download_file():
    """下载文件"""
    try:
        file_path = request.args.get('path')
        if not file_path:
            return jsonify({'success': False, 'error': '缺少文件路径参数'})
        
        path = Path(file_path)
        if not path.exists():
            return jsonify({'success': False, 'error': '文件不存在'})
        
        if not path.is_file():
            return jsonify({'success': False, 'error': '路径不是文件'})
        
        # 安全检查：确保文件在data/output目录下
        data_output_path = Path('data/output').resolve()
        try:
            path.resolve().relative_to(data_output_path)
        except ValueError:
            return jsonify({'success': False, 'error': '文件访问权限不足'})
        
        return send_file(path, as_attachment=True, download_name=path.name)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/file_content')
def get_file_content():
    """获取文件内容"""
    try:
        file_path = request.args.get('path')
        if not file_path:
            return jsonify({'success': False, 'error': '缺少文件路径参数'})
        
        path = Path(file_path)
        if not path.exists():
            return jsonify({'success': False, 'error': '文件不存在'})
        
        if not path.is_file():
            return jsonify({'success': False, 'error': '路径不是文件'})
        
        # 安全检查：确保文件在data/output目录下
        data_output_path = Path('data/output').resolve()
        try:
            path.resolve().relative_to(data_output_path)
        except ValueError:
            return jsonify({'success': False, 'error': '文件访问权限不足'})
        
        # 根据文件类型读取内容
        file_ext = path.suffix.lower()
        
        def read_file_with_encoding_detection(file_path):
            """智能读取文件，自动检测编码"""
            # 尝试多种编码方式读取文件
            encodings_to_try = ['utf-8', 'shift_jis', 'gbk', 'big5', 'iso-8859-1', 'cp1252']
            content = None
            used_encoding = None
            
            for encoding in encodings_to_try:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                        used_encoding = encoding
                        break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                # 如果所有编码都失败，尝试二进制模式读取
                try:
                    with open(file_path, 'rb') as f:
                        raw_data = f.read()
                        # 尝试自动检测编码
                        try:
                            import chardet
                            detected = chardet.detect(raw_data)
                            if detected['encoding'] and detected['confidence'] > 0.7:
                                content = raw_data.decode(detected['encoding'])
                                used_encoding = f"{detected['encoding']} (detected)"
                        except ImportError:
                            pass
                        
                        # 如果检测失败，使用UTF-8并忽略错误
                        if content is None:
                            content = raw_data.decode('utf-8', errors='ignore')
                            used_encoding = 'utf-8 (with errors ignored)'
                except Exception:
                    raise Exception('无法读取文件内容')
            
            return content, used_encoding
        
        if file_ext in ['.html', '.htm']:
            content, encoding = read_file_with_encoding_detection(path)
            return jsonify({
                'success': True,
                'content': content,
                'type': 'html',
                'filename': path.name,
                'encoding': encoding
            })
        elif file_ext == '.json':
            content, encoding = read_file_with_encoding_detection(path)
            
            # 检测JSON内容是否为空或无意义
            is_empty_json = False
            empty_json_type = None
            
            try:
                parsed_content = json.loads(content)
                # 检测各种"空"情况
                if parsed_content == "":
                    is_empty_json = True
                    empty_json_type = "empty_string"
                elif parsed_content == {}:
                    is_empty_json = True
                    empty_json_type = "empty_object"
                elif parsed_content == []:
                    is_empty_json = True
                    empty_json_type = "empty_array"
                elif parsed_content is None:
                    is_empty_json = True
                    empty_json_type = "null"
            except json.JSONDecodeError:
                pass
            
            return jsonify({
                'success': True,
                'content': content,
                'type': 'json',
                'filename': path.name,
                'encoding': encoding,
                'is_empty_json': is_empty_json,
                'empty_json_type': empty_json_type
            })
        elif file_ext == '.txt':
            content, encoding = read_file_with_encoding_detection(path)
            return jsonify({
                'success': True,
                'content': content,
                'type': 'text',
                'filename': path.name,
                'encoding': encoding
            })
        else:
            return jsonify({'success': False, 'error': '不支持的文件类型'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/compare')
def compare_view():
    """对比查看页面"""
    task_path = request.args.get('path')
    if not task_path:
        return "缺少任务路径参数", 400
    
    # 获取任务目录下的文件列表
    try:
        path = Path(task_path)
        if not path.exists() or not path.is_dir():
            return "任务目录不存在", 404
        
        files = []
        for file_path in path.iterdir():
            if file_path.is_file():
                files.append({
                    'name': file_path.name,
                    'path': str(file_path),
                    'type': file_path.suffix.lower()
                })
        
        # 按类型分组
        html_files = [f for f in files if f['type'] in ['.html', '.htm']]
        json_files = [f for f in files if f['type'] == '.json']
        
        return render_template('compare.html', 
                             task_path=task_path,
                             html_files=html_files,
                             json_files=json_files)
        
    except Exception as e:
        return f"加载失败: {str(e)}", 500

@app.route('/submit', methods=['POST'])
def submit_command():
    """提交命令执行"""
    try:
        # 获取表单数据
        task_id_input = request.form.get('task_id', '').strip()
        output_type = request.form.get('output_type', 'html')
        use_parse = request.form.get('use_parse') == 'on'
        
        # 验证输入
        if not task_id_input:
            return jsonify({
                'success': False,
                'error': '请填写任务ID'
            })
        
        # 自动获取任务类型
        from src.azure_resource_reader import get_task_type_by_job_id
        task_type = get_task_type_by_job_id(task_id_input)
        
        if not task_type:
            return jsonify({
                'success': False,
                'error': f'无法找到任务ID {task_id_input} 对应的任务类型，请检查任务ID是否正确'
            })
        
        # 构建智能模式命令（直接使用job_id，让脚本自动识别任务类型）
        command_parts = [
            'python3',
            'src/azure_resource_reader.py',
            task_id_input,  # 直接使用job_id
            output_type
        ]
        
        if use_parse:
            command_parts.append('--with-parse')
        
        command = ' '.join(command_parts)
        
        # 生成任务ID
        execution_id = str(uuid.uuid4())
        
        # 初始化任务状态
        tasks[execution_id] = {
            'command': command,
            'status': 'pending',
            'output': '',
            'created_time': datetime.now(),
            'task_type': task_type,
            'task_id': task_id_input,
            'output_type': output_type,
            'use_parse': use_parse
        }
        
        # 在后台线程中执行命令
        thread = threading.Thread(
            target=execute_command,
            args=(execution_id, command, os.getcwd())
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'task_id': execution_id,
            'command': command
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'提交失败: {str(e)}'
        })

@app.route('/status/<task_id>')
def get_status(task_id):
    """获取任务状态"""
    if task_id not in tasks:
        return jsonify({
            'success': False,
            'error': '任务不存在'
        })
    
    task = tasks[task_id]
    
    # 计算执行时间
    duration = None
    if 'start_time' in task:
        end_time = task.get('end_time', datetime.now())
        duration = str(end_time - task['start_time'])
    
    return jsonify({
        'success': True,
        'status': task['status'],
        'output': task.get('output', ''),
        'command': task['command'],
        'created_time': task['created_time'].strftime('%Y-%m-%d %H:%M:%S'),
        'duration': duration,
        'return_code': task.get('return_code'),
        'error': task.get('error')
    })

@app.route('/tasks')
def list_tasks():
    """列出所有任务"""
    task_list = []
    for task_id, task in tasks.items():
        duration = None
        if 'start_time' in task:
            end_time = task.get('end_time', datetime.now())
            duration = str(end_time - task['start_time'])
        
        task_list.append({
            'id': task_id,
            'command': task['command'],
            'status': task['status'],
            'created_time': task['created_time'].strftime('%Y-%m-%d %H:%M:%S'),
            'duration': duration,
            'task_type': task.get('task_type'),
            'task_id': task.get('task_id'),
            'use_parse': task.get('use_parse', False)
        })
    
    # 按创建时间倒序排列
    task_list.sort(key=lambda x: x['created_time'], reverse=True)
    
    return render_template('tasks.html', tasks=task_list)

@app.route('/clear_tasks', methods=['POST'])
def clear_tasks():
    """清空任务历史"""
    global tasks
    tasks = {}
    return jsonify({'success': True})

@app.route('/api/get_task_type')
def get_task_type():
    """根据任务ID获取任务类型"""
    try:
        task_id = request.args.get('task_id')
        if not task_id:
            return jsonify({'success': False, 'error': '缺少任务ID参数'})
        
        # 导入函数
        from src.azure_resource_reader import get_task_type_by_job_id
        
        # 查询任务类型
        task_type = get_task_type_by_job_id(task_id)
        
        if task_type:
            return jsonify({
                'success': True,
                'task_type': task_type,
                'task_id': task_id
            })
        else:
            return jsonify({
                'success': False,
                'error': f'未找到任务ID {task_id} 对应的任务类型',
                'task_id': task_id
            })
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': f'查询任务类型时出错: {str(e)}'
        })

@app.route('/api/check_task_exists')
def check_task_exists():
    """检查任务ID是否已存在（仅使用数据库）"""
    try:
        task_id = request.args.get('task_id')
        if not task_id:
            return jsonify({'success': False, 'error': '缺少任务ID参数'})
        
        if not LOCAL_DB_AVAILABLE:
            return jsonify({
                'success': True, 
                'exists': False,
                'task_id': task_id,
                'message': '数据库不可用，无法检查任务'
            })
        
        db = LocalDatabaseConnector()
        mapping = db.get_task_mapping_by_job_id(task_id)
        db.disconnect()
        
        # 检查任务ID是否存在
        exists = mapping is not None
        task_info = mapping if exists else {}
        
        return jsonify({
            'success': True,
            'exists': exists,
            'task_id': task_id,
            'task': task_info  # 与前端期望的字段名保持一致
        })
        
    except Exception as e:
        logger.warning(f"检查任务存在性失败: {str(e)}")
        return jsonify({
            'success': False, 
            'error': f'检查任务时出错: {str(e)}'
        })

@app.route('/api/statistics/config', methods=['GET'])
def get_statistics_config():
    """获取统计配置信息"""
    try:
        return jsonify({
            'success': True,
            'data': {
                'task_types': TASK_TYPES,
                'tenants': TENANT_CONFIG,
                'database_tables': DATABASE_TABLES
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/statistics/data', methods=['POST'])
def get_statistics_data():
    """获取任务统计数据"""
    try:
        data = request.get_json()
        
        # 获取参数
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        tenant_ids = data.get('tenant_ids', [])
        task_type = data.get('task_type', '')  # 改为单个任务类型
        refresh_timestamp = data.get('_refresh')  # 刷新时间戳
        
        # 参数验证
        if not start_date or not end_date:
            return jsonify({'success': False, 'error': '开始日期和结束日期不能为空'})
        
        if not tenant_ids:
            return jsonify({'success': False, 'error': '至少选择一个租户'})
        
        if not task_type:
            return jsonify({'success': False, 'error': '请选择任务类型'})
        
        # 生成缓存键（如果有刷新时间戳，则包含在缓存键中以绕过缓存）
        cache_key_params = ['statistics_data', start_date, end_date, tenant_ids, task_type]
        if refresh_timestamp:
            cache_key_params.append(refresh_timestamp)
        cache_key = generate_cache_key(*cache_key_params)
        
        # 检查缓存（如果是刷新请求，跳过缓存检查）
        if not refresh_timestamp:
            cached_result = get_from_cache(cache_key)
            if cached_result:
                return jsonify({
                    'success': True,
                    'data': cached_result['data'],
                    'from_cache': True,
                    'cache_time': cached_result['cache_time'],
                    '_debug': cached_result['debug_info']
                })
        
        # 创建数据库连接
        db_config = DB_CONFIG.copy()
        db_config['database'] = 'shulex_collector_prod'
        
        db = DatabaseConnector(db_config)
        if not db.connect():
            return jsonify({'success': False, 'error': '数据库连接失败'})
        
        try:
            # 使用优化的查询策略
            statistics_data, debug_info = get_optimized_statistics_data(db, start_date, end_date, tenant_ids, task_type)
            
            # 存入缓存
            set_to_cache(cache_key, statistics_data, debug_info)
            
            return jsonify({
                'success': True,
                'data': statistics_data,
                'cache_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                '_debug': debug_info
            })
            
        finally:
            db.disconnect()
            
    except Exception as e:
        logger.error(f"获取统计数据失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


def generate_cache_key(*args):
    """生成缓存键"""
    key_string = '|'.join(str(arg) for arg in args)
    return hashlib.md5(key_string.encode()).hexdigest()


def get_from_cache(cache_key):
    """从缓存获取数据"""
    if cache_key in statistics_cache:
        cache_entry = statistics_cache[cache_key]
        if time.time() - cache_entry['timestamp'] < CACHE_DURATION:
            return {
                'data': cache_entry['data'],
                'cache_time': cache_entry['cache_time'],
                'debug_info': cache_entry['debug_info']
            }
        else:
            # 缓存过期，删除
            del statistics_cache[cache_key]
    return None


def set_to_cache(cache_key, data, debug_info=None):
    """设置缓存数据"""
    cache_time = datetime.now()
    statistics_cache[cache_key] = {
        'data': data,
        'timestamp': time.time(),
        'cache_time': cache_time.strftime('%Y-%m-%d %H:%M:%S'),
        'debug_info': debug_info or []
    }


def get_optimized_statistics_data(db, start_date, end_date, tenant_ids, task_type):
    """
    优化的统计数据查询
    使用单个查询获取所有统计数据，减少数据库往返次数
    """
    statistics_data = {
        'failed_count': [],
        'timeout_count': [],
        'total_count': [],
        'timeout_but_succeed': [],  # 已超时但已完成
        'succeed_count': [],        # 已完成数量
        'succeed_not_timeout': [],  # 未超时且已完成数量
        'timeout_not_succeed': []   # 超时未完成数量
    }
    
    debug_info = []
    
    # 超时判断应该使用当前UTC时间，而不是查询日期
    # 这样可以反映截至当前时间的真实超时状态
    current_utc_time = get_utc_now()
    timeout_condition, _ = get_timeout_condition(current_utc_time)
    
    # 转换查询日期为UTC时间
    utc_start_date = convert_to_utc_datetime(start_date, "00:00:00")
    utc_end_date = convert_to_utc_datetime(end_date, "23:59:59")
    
    # 遍历所有分表
    for table in DATABASE_TABLES:
        # 使用单个复合查询获取所有统计数据
        optimized_sql = f"""
            SELECT 
                DATE(created_at) AS date,
                type as task_type,
                COUNT(*) as total_count,
                SUM(CASE WHEN `status` = 'FAILED' THEN 1 ELSE 0 END) as failed_count,
                SUM(CASE WHEN {timeout_condition} THEN 1 ELSE 0 END) as timeout_count,
                SUM(CASE WHEN `status` = 'SUCCEED' THEN 1 ELSE 0 END) as succeed_count,
                SUM(CASE WHEN ({timeout_condition}) AND `status` = 'SUCCEED' THEN 1 ELSE 0 END) as timeout_but_succeed,
                SUM(CASE WHEN NOT ({timeout_condition}) AND `status` = 'SUCCEED' THEN 1 ELSE 0 END) as succeed_not_timeout,
                SUM(CASE WHEN ({timeout_condition}) AND `status` != 'SUCCEED' AND `status` != 'FAILED' THEN 1 ELSE 0 END) as timeout_not_succeed
            FROM {table}
            WHERE created_at >= %s 
                AND created_at <= %s
                AND tenant_id IN ({','.join(['%s'] * len(tenant_ids))})
                AND type = %s
            GROUP BY date, task_type
            ORDER BY date DESC, task_type
        """
        
        # 参数：current_utc_time (4次), utc_start_date, utc_end_date, tenant_ids, task_type
        params = [current_utc_time, current_utc_time, current_utc_time, current_utc_time, utc_start_date, utc_end_date] + tenant_ids + [task_type]
        
        # 记录调试信息
        debug_info.append({
            'table': table,
            'sql': clean_sql_for_debug(optimized_sql),
            'params': params,
            'query_time': get_utc_now(),
            'timeout_reference_time': current_utc_time
        })
        
        # 执行查询
        results = db.execute_query(optimized_sql, params)
        
        # 分解结果到不同的统计类型
        for result in results:
            date_str = str(result['date'])
            task_type = result['task_type']
            
            # 添加表名信息
            base_record = {
                'date': date_str,
                'task_type': task_type,
                'table': table
            }
            
            # 分别添加到不同的统计类型
            statistics_data['total_count'].append({
                **base_record,
                'count': result['total_count']
            })
            
            statistics_data['failed_count'].append({
                **base_record,
                'count': result['failed_count']
            })
            
            statistics_data['timeout_count'].append({
                **base_record,
                'count': result['timeout_count']
            })
            
            statistics_data['succeed_count'].append({
                **base_record,
                'count': result['succeed_count']
            })
            
            statistics_data['timeout_but_succeed'].append({
                **base_record,
                'count': result['timeout_but_succeed']
            })
            
            statistics_data['succeed_not_timeout'].append({
                **base_record,
                'count': result['succeed_not_timeout']
            })
            
            statistics_data['timeout_not_succeed'].append({
                **base_record,
                'count': result['timeout_not_succeed']
            })
    
    # 数据聚合处理
    return aggregate_statistics_data(statistics_data), debug_info


def aggregate_statistics_data(raw_data):
    """
    聚合统计数据
    
    Args:
        raw_data: 原始数据字典
        
    Returns:
        dict: 聚合后的数据
    """
    aggregated = {}
    
    for stat_type, records in raw_data.items():
        # 按日期和任务类型聚合
        date_task_map = {}
        
        for record in records:
            date_str = str(record['date'])
            task_type = record['task_type']
            count = record['count']
            
            if date_str not in date_task_map:
                date_task_map[date_str] = {}
            
            if task_type not in date_task_map[date_str]:
                date_task_map[date_str][task_type] = 0
            
            date_task_map[date_str][task_type] += count
        
        # 转换为前端需要的格式
        aggregated[stat_type] = []
        for date_str in sorted(date_task_map.keys(), reverse=True):
            for task_type, count in date_task_map[date_str].items():
                aggregated[stat_type].append({
                    'date': date_str,
                    'task_type': task_type,
                    'count': count
                })
    
    return aggregated


@app.route('/api/statistics/summary', methods=['POST'])
def get_statistics_summary():
    """获取统计汇总数据"""
    try:
        data = request.get_json()
        
        # 获取参数
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        tenant_ids = data.get('tenant_ids', [])
        task_type = data.get('task_type', '')  # 改为单个任务类型
        refresh_timestamp = data.get('_refresh')  # 刷新时间戳
        
        # 参数验证
        if not start_date or not end_date:
            return jsonify({'success': False, 'error': '开始日期和结束日期不能为空'})
        
        if not tenant_ids:
            return jsonify({'success': False, 'error': '至少选择一个租户'})
        
        if not task_type:
            return jsonify({'success': False, 'error': '请选择任务类型'})
        
        # 生成缓存键（如果有刷新时间戳，则包含在缓存键中以绕过缓存）
        cache_key_params = ['statistics_summary', start_date, end_date, tenant_ids, task_type]
        if refresh_timestamp:
            cache_key_params.append(refresh_timestamp)
        cache_key = generate_cache_key(*cache_key_params)
        
        # 检查缓存（如果是刷新请求，跳过缓存检查）
        if not refresh_timestamp:
            cached_result = get_from_cache(cache_key)
            if cached_result:
                return jsonify({
                    'success': True,
                    'data': cached_result['data'],
                    'from_cache': True,
                    'cache_time': cached_result['cache_time'],
                    '_debug': cached_result['debug_info']
                })
        
        # 创建数据库连接
        db_config = DB_CONFIG.copy()
        db_config['database'] = 'shulex_collector_prod'
        
        db = DatabaseConnector(db_config)
        if not db.connect():
            return jsonify({'success': False, 'error': '数据库连接失败'})
        
        try:
            summary_data = {}
            debug_info = []
            
            # 超时判断应该使用当前UTC时间，而不是查询日期
            # 这样可以反映截至当前时间的真实超时状态
            current_utc_time = get_utc_now()
            timeout_condition, _ = get_timeout_condition(current_utc_time)
            
            # 转换查询日期为UTC时间
            utc_start_date = convert_to_utc_datetime(start_date, "00:00:00")
            utc_end_date = convert_to_utc_datetime(end_date, "23:59:59")
            
            # 遍历所有分表获取汇总数据
            for table in DATABASE_TABLES:
                # 汇总SQL模板（优化版本）
                summary_sql = f"""
                    SELECT 
                        type as task_type,
                        COUNT(*) as total_count,
                        SUM(CASE WHEN `status` = 'FAILED' THEN 1 ELSE 0 END) as failed_count,
                        SUM(CASE WHEN {timeout_condition} THEN 1 ELSE 0 END) as timeout_count,
                        SUM(CASE WHEN `status` = 'SUCCEED' THEN 1 ELSE 0 END) as succeed_count,
                        SUM(CASE WHEN ({timeout_condition}) AND `status` = 'SUCCEED' THEN 1 ELSE 0 END) as timeout_but_succeed,
                        SUM(CASE WHEN NOT ({timeout_condition}) AND `status` = 'SUCCEED' THEN 1 ELSE 0 END) as succeed_not_timeout,
                        SUM(CASE WHEN ({timeout_condition}) AND `status` != 'SUCCEED' AND `status` != 'FAILED' THEN 1 ELSE 0 END) as timeout_not_succeed
                    FROM {table}
                    WHERE created_at >= %s 
                        AND created_at <= %s
                        AND tenant_id IN ({','.join(['%s'] * len(tenant_ids))})
                        AND type = %s
                    GROUP BY task_type
                """
                
                # 参数：current_utc_time (4次), utc_start_date, utc_end_date, tenant_ids, task_type
                params = [current_utc_time, current_utc_time, current_utc_time, current_utc_time, utc_start_date, utc_end_date] + tenant_ids + [task_type]
                
                # 记录调试信息
                debug_info.append({
                    'table': table,
                    'sql': clean_sql_for_debug(summary_sql),
                    'params': params,
                    'query_time': get_utc_now(),
                    'timeout_reference_time': current_utc_time
                })
                
                results = db.execute_query(summary_sql, params)
                
                # 聚合数据
                for result in results:
                    task_type = result['task_type']
                    if task_type not in summary_data:
                        summary_data[task_type] = {
                            'total_count': 0,
                            'failed_count': 0,
                            'timeout_count': 0,
                            'succeed_count': 0,
                            'timeout_but_succeed': 0,
                            'succeed_not_timeout': 0,
                            'timeout_not_succeed': 0
                        }
                    
                    summary_data[task_type]['total_count'] += result['total_count']
                    summary_data[task_type]['failed_count'] += result['failed_count']
                    summary_data[task_type]['timeout_count'] += result['timeout_count']
                    summary_data[task_type]['succeed_count'] += result['succeed_count']
                    summary_data[task_type]['timeout_but_succeed'] += result['timeout_but_succeed']
                    summary_data[task_type]['succeed_not_timeout'] += result['succeed_not_timeout']
                    summary_data[task_type]['timeout_not_succeed'] += result['timeout_not_succeed']
            
            # 存入缓存
            set_to_cache(cache_key, summary_data, debug_info)
            
            return jsonify({
                'success': True,
                'data': summary_data,
                'cache_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                '_debug': debug_info
            })
            
        finally:
            db.disconnect()
            
    except Exception as e:
        logger.error(f"获取汇总数据失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/statistics/details', methods=['POST'])
def get_statistics_details():
    """获取统计详细数据"""
    try:
        data = request.get_json()
        
        # 验证必需参数
        required_fields = ['start_date', 'end_date', 'tenant_ids', 'task_type', 'detail_type', 'date']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'缺少必需参数: {field}'
                }), 400
        
        start_date = data['start_date']
        end_date = data['end_date']
        tenant_ids = data['tenant_ids']
        task_type = data['task_type']
        detail_type = data['detail_type']  # 'failed', 'timeout', 'failed_timeout'
        target_date = data['date']
        page = data.get('page', 1)
        page_size = data.get('page_size', 20)
        target_table = data.get('table')  # 新增：指定查询的表，如果不指定则查询所有表
        
        # 验证参数
        if not isinstance(tenant_ids, list) or len(tenant_ids) == 0:
            return jsonify({
                'success': False,
                'message': '租户ID列表不能为空'
            }), 400
        
        # 获取配置
        tables = TASK_STATISTICS_CONFIG['tables']
        tenants_config = TASK_STATISTICS_CONFIG['tenants']
        
        # 如果指定了表，只查询该表
        if target_table:
            if target_table not in tables:
                return jsonify({
                    'success': False,
                    'message': f'无效的表名: {target_table}'
                }), 400
            tables = [target_table]
        
        # 验证租户ID
        valid_tenant_ids = [t['id'] for t in tenants_config]
        for tenant_id in tenant_ids:
            if tenant_id not in valid_tenant_ids:
                return jsonify({
                    'success': False,
                    'message': f'无效的租户ID: {tenant_id}'
                }), 400
        
        # 创建数据库连接（修复：正确配置数据库）
        db_config = DB_CONFIG.copy()
        db_config['database'] = 'shulex_collector_prod'
        
        all_details = []
        debug_info = []
        
        # 查询每个表的详细数据
        for table in tables:
            job_table = table
            log_table = table.replace('job_', 'log_')
            
            # 构建SQL查询
            tenant_placeholders = ', '.join(['%s'] * len(tenant_ids))
            
            # 根据详情类型构建不同的WHERE条件
            # 转换日期为UTC时间
            target_date_start = convert_to_utc_datetime(target_date, "00:00:00")
            target_date_end = convert_to_utc_datetime(target_date, "23:59:59")
            
            # 计算最终的日期范围（取交集）
            final_start_date = max(convert_to_utc_datetime(start_date, "00:00:00"), target_date_start)
            final_end_date = min(convert_to_utc_datetime(end_date, "23:59:59"), target_date_end)
            
            if detail_type == 'failed':
                where_condition = f"""
                WHERE a.created_at >= %s 
                    AND a.created_at <= %s 
                    AND a.tenant_id IN ({tenant_placeholders})
                    AND a.type = %s
                    AND a.status = 'FAILED'
                """
                params = [
                    final_start_date,
                    final_end_date
                ] + tenant_ids + [
                    task_type
                ]
            elif detail_type == 'timeout':
                # 超时判断应该使用当前UTC时间，而不是目标日期
                # 这样可以反映截至当前时间的真实超时状态
                current_utc_time = get_utc_now()
                timeout_condition, _ = get_timeout_condition(current_utc_time)
                
                where_condition = f"""
                WHERE a.created_at >= %s 
                    AND a.created_at <= %s 
                    AND a.tenant_id IN ({tenant_placeholders})
                    AND a.type = %s
                    AND {timeout_condition}
                """
                params = [
                    final_start_date,
                    final_end_date
                ] + tenant_ids + [
                    task_type,
                    current_utc_time
                ]
            elif detail_type == 'timeout_but_succeed':
                # 已超时但已完成
                current_utc_time = get_utc_now()
                timeout_condition, _ = get_timeout_condition(current_utc_time)
                
                where_condition = f"""
                WHERE a.created_at >= %s 
                    AND a.created_at <= %s 
                    AND a.tenant_id IN ({tenant_placeholders})
                    AND a.type = %s
                    AND {timeout_condition}
                    AND a.status = 'SUCCEED'
                """
                params = [
                    final_start_date,
                    final_end_date
                ] + tenant_ids + [
                    task_type,
                    current_utc_time
                ]
            elif detail_type == 'succeed':
                # 已完成
                where_condition = f"""
                WHERE a.created_at >= %s 
                    AND a.created_at <= %s 
                    AND a.tenant_id IN ({tenant_placeholders})
                    AND a.type = %s
                    AND a.status = 'SUCCEED'
                """
                params = [
                    final_start_date,
                    final_end_date
                ] + tenant_ids + [
                    task_type
                ]
            elif detail_type == 'succeed_not_timeout':
                # 未超时且已完成
                current_utc_time = get_utc_now()
                timeout_condition, _ = get_timeout_condition(current_utc_time)
                
                where_condition = f"""
                WHERE a.created_at >= %s 
                    AND a.created_at <= %s 
                    AND a.tenant_id IN ({tenant_placeholders})
                    AND a.type = %s
                    AND NOT ({timeout_condition})
                    AND a.status = 'SUCCEED'
                """
                params = [
                    final_start_date,
                    final_end_date
                ] + tenant_ids + [
                    task_type,
                    current_utc_time
                ]
            elif detail_type == 'timeout_not_succeed':
                # 超时未完成
                current_utc_time = get_utc_now()
                timeout_condition, _ = get_timeout_condition(current_utc_time)
                
                where_condition = f"""
                WHERE a.created_at >= %s 
                    AND a.created_at <= %s 
                    AND a.tenant_id IN ({tenant_placeholders})
                    AND a.type = %s
                    AND {timeout_condition}
                    AND a.status != 'SUCCEED'
                    AND a.status != 'FAILED'
                """
                params = [
                    final_start_date,
                    final_end_date
                ] + tenant_ids + [
                    task_type,
                    current_utc_time
                ]
            else:
                return jsonify({
                    'success': False,
                    'message': f'不支持的详情类型: {detail_type}'
                }), 400
            
            sql = f"""
            SELECT 
                a.created_at,
                a.break_at,
                a.deliver_at,
                a.req_ssn,
                a.payload,
                a.result,
                b.ext_ssn,
                b.analysis_response,
                b.response,
                a.status,
                b.state as log_state,
                '{table}' as source_table
            FROM {job_table} a 
            LEFT JOIN {log_table} b ON b.req_ssn = a.req_ssn
            {where_condition}
            ORDER BY a.created_at DESC
            LIMIT {page_size} OFFSET {(page - 1) * page_size}
            """
            
            # 记录调试信息
            debug_info.append({
                'table': table,
                'sql': clean_sql_for_debug(sql),
                'params': params,
                'detail_type': detail_type,
                'query_time': get_utc_now()
            })
            
            try:
                # 执行查询
                connector = DatabaseConnector(db_config)
                if not connector.connect():
                    logger.warning(f"数据库连接失败: {table}")
                    continue
                
                results = connector.execute_query(sql, params)
                
                # 处理结果
                for row in results:
                    # 处理字典格式的结果
                    if isinstance(row, dict):
                        # 格式化JSON字段
                        result_formatted = format_json_field(row.get('result'))
                        response_formatted = format_json_field(row.get('response'))
                        
                        # 判断是否显示重爬按钮
                        status = row.get('status') or ''
                        show_recrawl = should_show_recrawl_button(status, result_formatted)
                        
                        detail_item = {
                            'created_at': row.get('created_at').strftime('%Y-%m-%d %H:%M:%S') if row.get('created_at') else '',
                            'break_at': row.get('break_at').strftime('%Y-%m-%d %H:%M:%S') if row.get('break_at') else '',
                            'deliver_at': row.get('deliver_at').strftime('%Y-%m-%d %H:%M:%S') if row.get('deliver_at') else '',
                            'req_ssn': row.get('req_ssn') or '',
                            'payload': row.get('payload') or '',
                            'result': result_formatted,
                            'ext_ssn': row.get('ext_ssn') or '',
                            'analysis_response': row.get('analysis_response') or '',
                            'response': response_formatted,
                            'status': status,
                            'log_state': row.get('log_state') or '',
                            'source_table': row.get('source_table') or table,
                            'show_recrawl_button': show_recrawl
                        }
                    else:
                        # 处理元组格式的结果
                        # 格式化JSON字段
                        result_formatted = format_json_field(row[5] if len(row) > 5 else '')
                        response_formatted = format_json_field(row[8] if len(row) > 8 else '')
                        
                        # 判断是否显示重爬按钮
                        status = row[9] if len(row) > 9 else ''
                        show_recrawl = should_show_recrawl_button(status, result_formatted)
                        
                        detail_item = {
                            'created_at': row[0].strftime('%Y-%m-%d %H:%M:%S') if row[0] else '',
                            'break_at': row[1].strftime('%Y-%m-%d %H:%M:%S') if row[1] else '',
                            'deliver_at': row[2].strftime('%Y-%m-%d %H:%M:%S') if row[2] else '',
                            'req_ssn': row[3] or '',
                            'payload': row[4] or '',
                            'result': result_formatted,
                            'ext_ssn': row[6] or '',
                            'analysis_response': row[7] or '',
                            'response': response_formatted,
                            'status': status,
                            'log_state': row[10] or '',
                            'source_table': row[11] or table,
                            'show_recrawl_button': show_recrawl
                        }
                    all_details.append(detail_item)
                
                connector.disconnect()
                    
            except Exception as e:
                logger.warning(f"查询表 {table} 详细数据失败: {str(e)}")
                debug_info[-1]['error'] = str(e)
                continue
        
        # 按创建时间排序
        all_details.sort(key=lambda x: x['created_at'], reverse=True)
        
        # 分页处理（已在SQL中处理，这里只是为了计算总数）
        total_count = len(all_details)
        
        return jsonify({
            'success': True,
            'data': {
                'details': all_details,
                'total_count': total_count,
                'page': page,
                'page_size': page_size,
                'total_pages': (total_count + page_size - 1) // page_size if total_count > 0 else 0,
                'queried_tables': tables  # 返回查询的表列表
            },
            '_debug': debug_info
        })
        
    except Exception as e:
        logger.error(f"获取统计详细数据失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取详细数据失败: {str(e)}'
        }), 500


def should_show_recrawl_button(status, result_data):
    """
    判断是否应该显示重爬按钮
    
    Args:
        status: 任务状态
        result_data: 格式化后的result数据字典
        
    Returns:
        bool: 是否显示重爬按钮
    """
    # 检查状态是否为FAILED
    if status != 'FAILED':
        return False
    
    # 检查result数据是否有效
    if not result_data or not result_data.get('is_valid_json'):
        return False
    
    try:
        # 解析JSON数据
        if isinstance(result_data.get('raw'), str):
            result_json = json.loads(result_data.get('raw'))
        else:
            result_json = result_data.get('raw')
        
        # 检查是否包含特定的错误信息
        expected_error = "作业提交失败: 408 IORuntimeException - SocketTimeoutException: connect timed out"
        
        if isinstance(result_json, dict) and 'E3001' in result_json:
            actual_error = result_json.get('E3001', '')
            return actual_error == expected_error
        
        return False
        
    except (json.JSONDecodeError, TypeError, AttributeError) as e:
        logger.warning(f"⚠️ 解析result数据失败: {e}")
        return False


def format_json_field(json_str):
    """
    格式化JSON字段
    
    Args:
        json_str: JSON字符串
        
    Returns:
        dict: 包含格式化信息的字典
    """
    if not json_str:
        return {
            'raw': '',
            'formatted': '',
            'is_valid_json': False,
            'error': ''
        }
    
    try:
        # 尝试解析JSON
        if isinstance(json_str, str):
            parsed_json = json.loads(json_str)
        else:
            parsed_json = json_str
        
        # 格式化JSON
        formatted_json = json.dumps(parsed_json, indent=2, ensure_ascii=False)
        
        return {
            'raw': json_str,
            'formatted': formatted_json,
            'is_valid_json': True,
            'error': ''
        }
    except (json.JSONDecodeError, TypeError) as e:
        return {
            'raw': json_str,
            'formatted': str(json_str),
            'is_valid_json': False,
            'error': str(e)
        }


@app.route('/api/resubmit_crawler', methods=['POST'])
def resubmit_crawler():
    """重新提交爬虫任务"""
    try:
        data = request.get_json()
        
        # 验证必需参数
        if 'req_ssn' not in data:
            return jsonify({
                'success': False,
                'message': '缺少必需参数: req_ssn'
            }), 400
        
        req_ssn = data['req_ssn']
        
        # 构建命令
        job_id = f"SL{req_ssn}" if not req_ssn.startswith('SL') else req_ssn
        command = f"python3 src/main.py resubmit_crawler_jobs --job-ids {job_id}"
        
        logger.info(f"🔄 执行重爬命令: {command} (req_ssn: {req_ssn})")
        
        # 异步执行命令
        def run_resubmit_command():
            try:
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=os.getcwd(),
                    bufsize=1,
                    universal_newlines=True
                )
                
                # 读取输出
                output_lines = []
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        line = output.strip()
                        output_lines.append(line)
                        logger.info(f"📝 重爬输出: {line}")
                
                return_code = process.poll()
                
                final_output = '\n'.join(output_lines)
                success = return_code == 0
                
                logger.info(f"✅ 重爬命令完成，返回码: {return_code}")
                logger.info(f"📋 完整输出:\n{final_output}")
                
                return {
                    'success': success,
                    'return_code': return_code,
                    'output': final_output,
                    'job_id': job_id,
                    'req_ssn': req_ssn
                }
                
            except Exception as e:
                error_msg = f"执行重爬命令时出错: {str(e)}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'job_id': job_id,
                    'req_ssn': req_ssn
                }
        
        # 在新线程中执行命令
        thread = threading.Thread(target=run_resubmit_command)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': f'重爬任务已提交，任务ID: {job_id}',
            'job_id': job_id,
            'req_ssn': req_ssn,
            'command': command
        })
        
    except Exception as e:
        error_msg = f"提交重爬任务失败: {str(e)}"
        logger.error(error_msg)
        return jsonify({
            'success': False,
            'message': error_msg
        }), 500


@app.route('/api/task_mappings', methods=['GET'])
def get_task_mappings():
    """
    获取任务映射记录（优先从数据库，备用JSON文件）
    支持分页和搜索
    """
    try:
        # 获取查询参数
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        search = request.args.get('search', '').strip()
        
        # 🆕 优先尝试从数据库获取
        if LOCAL_DB_AVAILABLE:
            try:
                db = LocalDatabaseConnector()
                offset = (page - 1) * per_page
                
                if search:
                    # 简单的搜索实现（在job_id和task_type中搜索）
                    # 这里简化处理，实际可以扩展更复杂的搜索逻辑
                    mappings = []
                    all_mappings = db.get_all_task_mappings(limit=1000, offset=0)
                    for mapping in all_mappings:
                        if (search.lower() in mapping.get('job_id', '').lower() or 
                            search.lower() in mapping.get('task_type', '').lower()):
                            mappings.append(mapping)
                    
                    # 手动分页
                    total = len(mappings)
                    mappings = mappings[offset:offset + per_page]
                else:
                    mappings = db.get_all_task_mappings(limit=per_page, offset=offset)
                    # 这里应该也查询总数，简化处理
                    total = len(mappings) + offset  # 简化的总数估算
                
                db.disconnect()
                
                # 为每个映射添加文件详情
                for mapping in mappings:
                    mapping_id = mapping.get('id')
                    if mapping_id:
                        db = LocalDatabaseConnector()
                        file_details = db.get_file_details_by_mapping_id(mapping_id)
                        mapping['files'] = file_details
                        db.disconnect()
                
                return jsonify({
                    'success': True,
                    'data': mappings,
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total': total,
                        'pages': (total + per_page - 1) // per_page
                    },
                    'source': 'database'
                })
                
            except Exception as db_error:
                logger.warning(f"数据库查询失败，回退到JSON文件: {str(db_error)}")
        
        # 🔄 回退到JSON文件
        mapping_file = 'data/output/task_mapping.json'
        if not os.path.exists(mapping_file):
            return jsonify({
                'success': True,
                'data': [],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': 0,
                    'pages': 0
                },
                'source': 'json_file'
            })
        
        with open(mapping_file, 'r', encoding='utf-8') as f:
            mapping_data = json.load(f)
        
        # 转换为列表格式并添加文件统计
        mappings = []
        for job_id, info in mapping_data.items():
            if search and search.lower() not in job_id.lower() and search.lower() not in info.get('task_type', '').lower():
                continue
                
            # 统计文件信息
            relative_path = info.get('relative_path', '')
            if relative_path.startswith('./'):
                full_path = f"data/output/{relative_path[2:]}"
            else:
                full_path = f"data/output/{relative_path}"
            
            file_count = 0
            has_parse_file = False
            if os.path.exists(full_path):
                files = [f for f in os.listdir(full_path) if os.path.isfile(os.path.join(full_path, f))]
                file_count = len(files)
                has_parse_file = 'parse_result.json' in files
            
            mapping = {
                'job_id': job_id,
                'task_type': info.get('task_type', ''),
                'actual_task_id': info.get('actual_task_id', ''),
                'relative_path': relative_path,
                'full_path': full_path,
                'file_count': file_count,
                'has_parse_file': has_parse_file,
                'status': 'success',
                'last_updated': info.get('last_updated', ''),
                'source': 'json_file'
            }
            mappings.append(mapping)
        
        # 排序（按最后更新时间倒序）
        mappings.sort(key=lambda x: x.get('last_updated', ''), reverse=True)
        
        # 分页
        total = len(mappings)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        mappings = mappings[start_idx:end_idx]
        
        return jsonify({
            'success': True,
            'data': mappings,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            },
            'source': 'json_file'
        })
        
    except Exception as e:
        logger.error(f"获取任务映射失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/task_mapping/<job_id>', methods=['GET'])
def get_task_mapping_detail(job_id):
    """
    获取单个任务映射的详细信息
    """
    try:
        # 🆕 优先尝试从数据库获取
        if LOCAL_DB_AVAILABLE:
            try:
                db = LocalDatabaseConnector()
                mapping = db.get_task_mapping_by_job_id(job_id)
                
                if mapping:
                    # 获取文件详情
                    file_details = db.get_file_details_by_mapping_id(mapping['id'])
                    mapping['files'] = file_details
                    mapping['source'] = 'database'
                    
                    db.disconnect()
                    return jsonify({
                        'success': True,
                        'data': mapping
                    })
                
                db.disconnect()
                
            except Exception as db_error:
                logger.warning(f"数据库查询失败，回退到JSON文件: {str(db_error)}")
        
        # 🔄 回退到JSON文件
        mapping_file = 'data/output/task_mapping.json'
        if not os.path.exists(mapping_file):
            return jsonify({
                'success': False,
                'error': '任务映射文件不存在'
            }), 404
        
        with open(mapping_file, 'r', encoding='utf-8') as f:
            mapping_data = json.load(f)
        
        if job_id not in mapping_data:
            return jsonify({
                'success': False,
                'error': '任务映射不存在'
            }), 404
        
        info = mapping_data[job_id]
        
        # 统计文件信息
        relative_path = info.get('relative_path', '')
        if relative_path.startswith('./'):
            full_path = f"data/output/{relative_path[2:]}"
        else:
            full_path = f"data/output/{relative_path}"
        
        files = []
        if os.path.exists(full_path):
            for filename in os.listdir(full_path):
                file_path = os.path.join(full_path, filename)
                if os.path.isfile(file_path):
                    file_type = 'parse' if filename == 'parse_result.json' else 'original'
                    files.append({
                        'file_name': filename,
                        'file_type': file_type,
                        'file_size': os.path.getsize(file_path),
                        'file_path': file_path
                    })
        
        mapping = {
            'job_id': job_id,
            'task_type': info.get('task_type', ''),
            'actual_task_id': info.get('actual_task_id', ''),
            'relative_path': relative_path,
            'full_path': full_path,
            'file_count': len(files),
            'has_parse_file': any(f['file_name'] == 'parse_result.json' for f in files),
            'status': 'success',
            'last_updated': info.get('last_updated', ''),
            'files': files,
            'source': 'json_file'
        }
        
        return jsonify({
            'success': True,
            'data': mapping
        })
        
    except Exception as e:
        logger.error(f"获取任务映射详情失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/database_status', methods=['GET'])
def get_database_status():
    """
    获取数据库状态信息
    """
    try:
        if not LOCAL_DB_AVAILABLE:
            return jsonify({
                'success': True,
                'data': {
                    'available': False,
                    'reason': '本地数据库模块不可用'
                }
            })
        
        db = LocalDatabaseConnector()
        connected = db.test_connection()
        
        if connected:
            # 获取统计信息
            db.connect()
            cursor = db.cursor
            
            # 获取任务映射数量
            cursor.execute("SELECT COUNT(*) as total FROM task_mapping")
            total_mappings = cursor.fetchone()['total']
            
            # 获取任务类型分布
            cursor.execute("SELECT task_type, COUNT(*) as count FROM task_mapping GROUP BY task_type")
            task_type_distribution = cursor.fetchall()
            
            # 获取最近更新时间
            cursor.execute("SELECT MAX(updated_at) as last_updated FROM task_mapping")
            last_updated = cursor.fetchone()['last_updated']
            
            db.disconnect()
            
            return jsonify({
                'success': True,
                'data': {
                    'available': True,
                    'connected': True,
                    'statistics': {
                        'total_mappings': total_mappings,
                        'task_type_distribution': task_type_distribution,
                        'last_updated': last_updated.isoformat() if last_updated else None
                    }
                }
            })
        else:
            return jsonify({
                'success': True,
                'data': {
                    'available': True,
                    'connected': False,
                    'reason': '无法连接到数据库'
                }
            })
        
    except Exception as e:
        logger.error(f"获取数据库状态失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/delete_task/<job_id>', methods=['DELETE'])
def delete_task(job_id):
    """删除任务（仅从数据库删除）"""
    logger.info(f"📥 收到删除任务请求: job_id={job_id}")
    try:
        if not LOCAL_DB_AVAILABLE:
            return jsonify({
                'success': False,
                'error': '本地数据库不可用'
            }), 500
        
        db = LocalDatabaseConnector()
        
        # 首先获取任务信息
        mapping = db.get_task_mapping_by_job_id(job_id)
        if not mapping:
            db.disconnect()
            return jsonify({
                'success': False,
                'error': '任务记录不存在'
            }), 404
        
        # 删除物理文件
        full_path = mapping.get('full_path', '')
        if full_path and os.path.exists(full_path):
            try:
                import shutil
                shutil.rmtree(full_path)
                logger.info(f"已删除文件目录: {full_path}")
            except Exception as file_error:
                logger.warning(f"删除文件目录失败: {str(file_error)}")
        
        # 删除数据库记录（由于外键约束，会自动删除相关的文件详情记录）
        cursor = db.cursor
        delete_query = "DELETE FROM task_mapping WHERE job_id = %s"
        cursor.execute(delete_query, (job_id,))
        db.connection.commit()
        
        deleted_rows = cursor.rowcount
        db.disconnect()
        
        if deleted_rows > 0:
            logger.info(f"成功删除任务记录: {job_id}")
            return jsonify({
                'success': True,
                'message': f'任务 {job_id} 删除成功'
            })
        else:
            return jsonify({
                'success': False,
                'error': '删除失败，记录不存在'
            }), 404
        
    except Exception as e:
        logger.error(f"删除任务失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/task_detail/<job_id>', methods=['GET'])
def get_task_detail(job_id):
    """获取任务详情（仅从数据库获取）"""
    logger.info(f"📥 收到获取任务详情请求: job_id={job_id}")
    try:
        if not LOCAL_DB_AVAILABLE:
            return jsonify({
                'success': False,
                'error': '本地数据库不可用'
            }), 500
        
        db = LocalDatabaseConnector()
        mapping = db.get_task_mapping_by_job_id(job_id)
        
        if not mapping:
            db.disconnect()
            return jsonify({
                'success': False,
                'error': '任务记录不存在'
            }), 404
        
        # 获取文件详情
        file_details = db.get_file_details_by_mapping_id(mapping['id'])
        mapping['files'] = file_details
        mapping['source'] = 'database'
        
        db.disconnect()
        
        # 为每个文件添加内容预览
        for file_info in mapping.get('files', []):
            file_path = file_info.get('file_path', '')
            if os.path.exists(file_path):
                try:
                    # 根据文件类型决定预览内容
                    if file_info.get('file_name', '').endswith('.json'):
                        # JSON文件，读取并格式化
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = json.load(f)
                            file_info['preview'] = json.dumps(content, indent=2, ensure_ascii=False)[:1000]
                            file_info['preview_type'] = 'json'
                    elif file_info.get('file_name', '').endswith('.html'):
                        # HTML文件，读取前500字符
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            file_info['preview'] = content[:500] + ('...' if len(content) > 500 else '')
                            file_info['preview_type'] = 'html'
                    else:
                        # 其他文件，简单文本预览
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            file_info['preview'] = content[:300] + ('...' if len(content) > 300 else '')
                            file_info['preview_type'] = 'text'
                except Exception as preview_error:
                    file_info['preview'] = f'预览失败: {str(preview_error)}'
                    file_info['preview_type'] = 'error'
            else:
                file_info['preview'] = '文件不存在'
                file_info['preview_type'] = 'error'
        
        return jsonify({
            'success': True,
            'data': mapping
        })
        
    except Exception as e:
        logger.error(f"获取任务详情失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    # 确保静态文件目录存在
    os.makedirs('static', exist_ok=True)
    
    logger.info("🚀 任务检查工具看板启动中...")
    logger.info("📊 统一的任务管理和监控平台")
    logger.info("📋 访问地址: http://localhost:5001")
    logger.info("=" * 50)
    
    # 检查系统状态
    logger.info("🔍 系统状态检查:")
    logger.info(f"   📁 日志目录: {Path('logs').absolute()}")
    logger.info(f"   🗄️  本地数据库: {'✅ 可用' if LOCAL_DB_AVAILABLE else '❌ 不可用'}")
    
    if LOCAL_DB_AVAILABLE:
        try:
            test_db = LocalDatabaseConnector()
            if test_db.connect():
                logger.info("   🔗 数据库连接: ✅ 测试成功")
                test_db.disconnect()
            else:
                logger.warning("   🔗 数据库连接: ⚠️ 测试失败")
        except Exception as e:
            logger.warning(f"   🔗 数据库连接: ❌ 测试异常 - {str(e)}")
    
    logger.info("🎯 启动完成，开始监听请求...")
    
    app.run(debug=True, host='0.0.0.0', port=5001) 