import request from './index'

// 获取已完成任务列表
export const getCompletedTasks = () => {
  return request({
    url: '/api/completed_tasks',
    method: 'get'
  })
}

// 提交任务
export const submitTask = (data) => {
  const formData = new FormData()
  formData.append('task_type', data.task_type)
  formData.append('task_id', data.task_id)
  formData.append('output_type', data.output_type)
  if (data.use_parse) {
    formData.append('use_parse', 'on')
  }
  
  return request({
    url: '/submit',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 获取任务状态
export const getTaskStatus = (taskId) => {
  return request({
    url: `/status/${taskId}`,
    method: 'get'
  })
}

// 检查任务是否存在
export const checkTaskExists = (taskId) => {
  return request({
    url: '/api/check_task_exists',
    method: 'get',
    params: { task_id: taskId }
  })
}

// 获取文件列表
export const getFileList = (path) => {
  return request({
    url: '/api/list_files',
    method: 'get',
    params: { path }
  })
}

// 获取文件内容
export const getFileContent = (path) => {
  return request({
    url: '/api/file_content',
    method: 'get',
    params: { path }
  })
}

// 下载文件
export const downloadFile = (path) => {
  return request({
    url: '/api/download_file',
    method: 'get',
    params: { path },
    responseType: 'blob'
  })
}

// 清空任务历史
export const clearTasks = () => {
  return request({
    url: '/clear_tasks',
    method: 'post'
  })
} 