#!/usr/bin/env python3
"""
Azure Resource Reader Web界面
提供web表单来提交和执行Azure Resource Reader命令
"""

import os
import subprocess
import threading
import time
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session
from pathlib import Path
import uuid

app = Flask(__name__)
app.secret_key = 'azure_resource_reader_web_2024'

# 全局变量存储任务状态
tasks = {}

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
    """读取已完成任务的映射文件"""
    mapping_file = Path('data/output/task_mapping.json')
    
    if not mapping_file.exists():
        return []
    
    try:
        with open(mapping_file, 'r', encoding='utf-8') as f:
            mapping_data = json.load(f)
        
        completed_tasks = []
        for job_id, task_info in mapping_data.items():
            # 检查任务目录是否存在
            relative_path = task_info.get('relative_path', '')
            if relative_path.startswith('./'):
                relative_path = relative_path[2:]
            
            full_path = Path('data/output') / relative_path
            
            # 统计文件数量
            file_count = 0
            has_parse_file = False
            if full_path.exists():
                files = [f for f in full_path.iterdir() if f.is_file()]
                file_count = len(files)
                has_parse_file = any(f.name == 'parse_result.json' for f in files)
            
            completed_tasks.append({
                'job_id': job_id,
                'task_type': task_info.get('task_type', 'Unknown'),
                'actual_task_id': task_info.get('actual_task_id', ''),
                'last_updated': format_timestamp(task_info.get('last_updated', '')),
                'relative_path': relative_path,
                'full_path': str(full_path),
                'file_count': file_count,
                'has_parse_file': has_parse_file,
                'directory_exists': full_path.exists()
            })
        
        # 按最后更新时间倒序排列
        completed_tasks.sort(key=lambda x: x['last_updated'], reverse=True)
        return completed_tasks
        
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"读取任务映射文件失败: {e}")
        return []

@app.route('/')
def index():
    """主页面"""
    completed_tasks = read_completed_tasks()
    return render_template('index.html', completed_tasks=completed_tasks)

@app.route('/api/completed_tasks')
def get_completed_tasks():
    """获取已完成任务的API接口"""
    completed_tasks = read_completed_tasks()
    return jsonify({
        'success': True,
        'tasks': completed_tasks,
        'total_count': len(completed_tasks)
    })

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
        
        from flask import send_file
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
        
        if file_ext in ['.html', '.htm']:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            return jsonify({
                'success': True,
                'content': content,
                'type': 'html',
                'filename': path.name
            })
        elif file_ext == '.json':
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            return jsonify({
                'success': True,
                'content': content,
                'type': 'json',
                'filename': path.name
            })
        elif file_ext == '.txt':
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            return jsonify({
                'success': True,
                'content': content,
                'type': 'text',
                'filename': path.name
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
        task_type = request.form.get('task_type', '').strip()
        task_id_input = request.form.get('task_id', '').strip()
        output_type = request.form.get('output_type', 'html')
        use_parse = request.form.get('use_parse') == 'on'
        
        # 验证输入
        if not task_type or not task_id_input:
            return jsonify({
                'success': False,
                'error': '请填写任务类型和任务ID'
            })
        
        # 构建命令
        command_parts = [
            'python3',
            'src/azure_resource_reader.py',
            task_type,
            task_id_input,
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

@app.route('/api/check_task_exists')
def check_task_exists():
    """检查任务ID是否已存在"""
    try:
        task_id = request.args.get('task_id')
        if not task_id:
            return jsonify({'success': False, 'error': '缺少任务ID参数'})
        
        mapping_file = Path('data/output/task_mapping.json')
        
        if not mapping_file.exists():
            return jsonify({
                'success': True, 
                'exists': False,
                'task_id': task_id
            })
        
        with open(mapping_file, 'r', encoding='utf-8') as f:
            mapping_data = json.load(f)
        
        # 检查任务ID是否存在
        exists = task_id in mapping_data
        task_info = mapping_data.get(task_id, {}) if exists else {}
        
        return jsonify({
            'success': True,
            'exists': exists,
            'task_id': task_id,
            'task_info': task_info
        })
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': f'检查任务时出错: {str(e)}'
        })

if __name__ == '__main__':
    # 确保模板和静态文件目录存在
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    print("🌐 Azure Resource Reader Web界面启动中...")
    print("📋 访问地址: http://localhost:5001")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5001) 