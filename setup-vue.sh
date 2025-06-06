#!/bin/bash

echo "🚀 开始设置Vue.js前端项目..."

# 检查Node.js是否安装
if ! command -v node &> /dev/null; then
    echo "❌ Node.js未安装，请先安装Node.js (https://nodejs.org/)"
    exit 1
fi

# 检查npm是否安装
if ! command -v npm &> /dev/null; then
    echo "❌ npm未安装，请先安装npm"
    exit 1
fi

echo "✅ Node.js版本: $(node --version)"
echo "✅ npm版本: $(npm --version)"

# 安装依赖
echo "📦 安装项目依赖..."
npm install

if [ $? -eq 0 ]; then
    echo "✅ 依赖安装成功"
else
    echo "❌ 依赖安装失败"
    exit 1
fi

# 创建必要的目录
mkdir -p src/styles
mkdir -p src/utils
mkdir -p src/composables

# 创建基础样式文件
cat > src/styles/index.css << 'EOF'
/* 全局样式 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background-color: #f5f7fa;
  color: #2c3e50;
}

/* 滚动条样式 */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* Element Plus 自定义样式 */
.el-card {
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.el-button {
  border-radius: 6px;
}

.el-input__wrapper {
  border-radius: 6px;
}

.el-select .el-input__wrapper {
  border-radius: 6px;
}
EOF

# 创建vite配置的路径别名解析
cat > vite.config.js << 'EOF'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:5001',
        changeOrigin: true
      },
      '/submit': {
        target: 'http://localhost:5001',
        changeOrigin: true
      },
      '/status': {
        target: 'http://localhost:5001',
        changeOrigin: true
      },
      '/tasks': {
        target: 'http://localhost:5001',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'static/dist',
    assetsDir: 'assets',
    sourcemap: false
  }
})
EOF

echo "🎉 Vue.js前端项目设置完成！"
echo ""
echo "📋 接下来的步骤："
echo "1. 启动后端服务: python3 web_app.py"
echo "2. 启动前端开发服务器: npm run dev"
echo "3. 访问 http://localhost:3000"
echo ""
echo "🔧 可用的命令："
echo "  npm run dev     - 启动开发服务器"
echo "  npm run build   - 构建生产版本"
echo "  npm run preview - 预览生产版本"
echo ""
echo "✨ 享受Vue.js + Element Plus的开发体验！" 