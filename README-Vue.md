# 任务检查工具看板 - Vue.js 前端

## 🎯 项目概述

这是一个基于 **Vue.js 3 + Element Plus** 重构的任务管理和监控平台前端，提供现代化的用户界面和更好的用户体验。

## 🚀 技术栈

### 前端技术
- **Vue.js 3** - 渐进式JavaScript框架
- **Element Plus** - 企业级UI组件库
- **Vue Router** - 官方路由管理器
- **Axios** - HTTP客户端
- **Vite** - 现代化构建工具
- **Day.js** - 轻量级日期处理库

### 后端技术
- **Flask** - Python Web框架
- **Azure SDK** - Azure资源访问

## 📦 快速开始

### 环境要求
- Node.js 16+ 
- npm 或 yarn
- Python 3.9+

### 1. 安装前端依赖

```bash
# 使用自动化脚本（推荐）
chmod +x setup-vue.sh
./setup-vue.sh

# 或手动安装
npm install
```

### 2. 启动开发环境

```bash
# 启动后端服务（终端1）
python3 web_app.py

# 启动前端开发服务器（终端2）
npm run dev
```

### 3. 访问应用

- **前端开发服务器**: http://localhost:3000
- **后端API服务器**: http://localhost:5001

## 🏗️ 项目结构

```
├── src/
│   ├── api/                 # API接口
│   │   ├── index.js        # Axios配置
│   │   └── tasks.js        # 任务相关API
│   ├── components/         # 公共组件
│   │   ├── TaskResultDialog.vue
│   │   ├── FileViewDialog.vue
│   │   └── TaskExistsDialog.vue
│   ├── layout/             # 布局组件
│   │   └── index.vue       # 主布局
│   ├── router/             # 路由配置
│   │   └── index.js
│   ├── styles/             # 样式文件
│   │   └── index.css
│   ├── views/              # 页面组件
│   │   ├── Dashboard.vue   # 主仪表板
│   │   └── Tasks.vue       # 任务历史
│   ├── App.vue             # 根组件
│   └── main.js             # 入口文件
├── package.json            # 项目配置
├── vite.config.js          # Vite配置
└── index.html              # HTML模板
```

## 🎨 界面特性

### 🎯 主仪表板 (Dashboard)
- **现代化表单设计**: 使用Element Plus组件
- **实时任务状态**: 支持任务执行进度监控
- **命令预览**: 实时显示将要执行的命令
- **已完成任务**: 右侧显示最近完成的任务
- **响应式布局**: 适配桌面和移动设备

### 📋 任务历史 (Tasks)
- **卡片式布局**: 美观的任务卡片展示
- **详细信息**: 显示任务类型、ID、文件数量等
- **操作菜单**: 支持查看、重跑、下载等操作
- **批量管理**: 支持清空历史记录

### 🔧 文件管理
- **文件列表**: 表格形式展示任务文件
- **在线预览**: 支持HTML、JSON、文本文件预览
- **下载功能**: 单文件下载支持
- **对比查看**: HTML和JSON并排对比（开发中）

## 🛠️ 开发命令

```bash
# 开发模式
npm run dev

# 构建生产版本
npm run build

# 预览生产版本
npm run preview
```

## 🎯 核心功能

### ✨ Azure Resource Reader
- **任务类型选择**: AmazonReviewStarJob / AmazonListingJob
- **智能ID转换**: 支持长任务ID和Job ID自动转换
- **多种输出格式**: HTML、TXT、JSON、RAW
- **解析模式**: 可选择启用--with-parse参数
- **任务验证**: 提交前检查任务是否已存在

### 📊 任务监控
- **实时状态更新**: WebSocket式的状态轮询
- **进度显示**: 可视化任务执行进度
- **结果展示**: 命令输出实时显示
- **错误处理**: 友好的错误信息展示

### 📁 文件管理
- **文件浏览**: 树形结构文件浏览
- **多格式预览**: 支持多种文件格式预览
- **批量操作**: 支持批量下载和管理
- **对比功能**: HTML和JSON文件对比查看

## 🎨 UI/UX 特性

### 🎯 设计原则
- **现代化**: 采用最新的设计趋势
- **一致性**: 统一的视觉语言和交互模式
- **易用性**: 直观的操作流程和反馈
- **响应式**: 完美适配各种设备尺寸

### 🌈 视觉特色
- **渐变背景**: 美观的渐变色彩搭配
- **卡片设计**: 清晰的信息层次结构
- **图标系统**: 丰富的图标语言
- **动画效果**: 流畅的过渡动画

### 📱 响应式设计
- **桌面端**: 完整功能和最佳体验
- **平板端**: 优化的布局和交互
- **移动端**: 简化界面和触摸友好

## 🔧 配置说明

### Vite 配置
```javascript
// vite.config.js
export default defineConfig({
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://localhost:5001'
    }
  }
})
```

### API 代理
前端开发服务器会自动代理API请求到后端服务器，无需额外配置。

## 🚀 部署说明

### 开发环境
1. 启动后端: `python3 web_app.py`
2. 启动前端: `npm run dev`

### 生产环境
1. 构建前端: `npm run build`
2. 静态文件会生成到 `static/dist/` 目录
3. Flask会自动服务这些静态文件

## 🎯 未来规划

### 🔮 即将推出
- **实时通知**: WebSocket实时通知系统
- **主题切换**: 支持明暗主题切换
- **多语言**: 国际化支持
- **高级搜索**: 任务历史高级搜索和过滤
- **数据可视化**: 任务执行统计图表

### 🚀 长期规划
- **插件系统**: 支持第三方工具集成
- **工作流**: 可视化任务流程编排
- **团队协作**: 多用户和权限管理
- **API文档**: 完整的API文档和SDK

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进项目！

### 开发规范
- 使用Vue 3 Composition API
- 遵循Element Plus设计规范
- 保持代码简洁和可读性
- 添加适当的注释和文档

## 📄 许可证

MIT License

---

**享受Vue.js + Element Plus带来的现代化开发体验！** 🎉 