import request from './index'

// 获取统计配置信息
export const getStatisticsConfig = () => {
  return request({
    url: '/api/statistics/config',
    method: 'get'
  })
}

// 获取统计数据
export const getStatisticsData = (params) => {
  return request({
    url: '/api/statistics/data',
    method: 'post',
    data: params,
    timeout: 360000 // 6分钟超时
  })
}

// 获取统计汇总数据
export const getStatisticsSummary = (params) => {
  return request({
    url: '/api/statistics/summary',
    method: 'post',
    data: params,
    timeout: 360000 // 6分钟超时
  })
}

// 获取统计详细数据
export const getStatisticsDetails = (params) => {
  return request({
    url: '/api/statistics/details',
    method: 'post',
    data: params,
    timeout: 360000 // 6分钟超时
  })
} 