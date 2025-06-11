import { createRouter, createWebHistory } from 'vue-router'
import Layout from '@/layout/index.vue'

const routes = [
  {
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { 
          title: '仪表板',
          icon: 'House'
        }
      },
      {
        path: 'tasks',
        name: 'Tasks',
        component: () => import('@/views/Tasks.vue'),
        meta: { 
          title: '任务管理',
          icon: 'List'
        }
      },
      {
        path: 'statistics',
        name: 'Statistics',
        component: () => import('@/views/Statistics.vue'),
        meta: { 
          title: '任务统计',
          icon: 'DataAnalysis'
        }
      },
      {
        path: 'database',
        name: 'DatabaseManager',
        component: () => import('@/views/DatabaseManager.vue'),
        meta: { 
          title: '数据库管理',
          icon: 'Connection'
        }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router 