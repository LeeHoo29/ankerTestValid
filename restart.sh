#!/bin/bash

# 任务管理平台 - 前后端重启脚本
# 作者: 系统管理员
# 版本: 1.0.0
# 描述: 一键重启前后端服务，自动处理端口冲突和环境检查

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 配置变量
BACKEND_PORT=5001
FRONTEND_PORT=3000
FRONTEND_ALT_PORT=3001
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="${PROJECT_DIR}/.venv"
LOG_FILE="${PROJECT_DIR}/restart.log"

# 日志函数
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "${LOG_FILE}"
}

info() {
    log "INFO" "${BLUE}ℹ️  $*${NC}"
}

success() {
    log "SUCCESS" "${GREEN}✅ $*${NC}"
}

warning() {
    log "WARNING" "${YELLOW}⚠️  $*${NC}"
}

error() {
    log "ERROR" "${RED}❌ $*${NC}"
}

# 清屏和显示标题
clear
echo -e "${CYAN}"
cat << 'EOF'
╔══════════════════════════════════════════════════════════════╗
║                  任务管理平台重启工具                        ║
║                  Vue.js + Flask 全栈应用                    ║
╚══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# 初始化日志文件
echo "==================== 重启会话开始 ====================" > "${LOG_FILE}"
info "开始重启任务管理平台..."
info "项目目录: ${PROJECT_DIR}"

# 1. 环境检查
info "🔍 正在进行环境检查..."

# 检查是否在正确的目录
if [[ ! -f "${PROJECT_DIR}/web_app.py" ]] || [[ ! -f "${PROJECT_DIR}/package.json" ]]; then
    error "错误：请在项目根目录下运行此脚本"
    exit 1
fi

# 检查Python虚拟环境
if [[ ! -d "${VENV_PATH}" ]]; then
    error "Python虚拟环境不存在: ${VENV_PATH}"
    error "请先运行: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# 检查Node.js和npm
if ! command -v node &> /dev/null || ! command -v npm &> /dev/null; then
    error "Node.js 或 npm 未安装，请先安装 Node.js"
    exit 1
fi

# 检查依赖文件
if [[ ! -f "${PROJECT_DIR}/requirements.txt" ]]; then
    warning "requirements.txt 不存在"
fi

if [[ ! -f "${PROJECT_DIR}/package.json" ]]; then
    error "package.json 不存在"
    exit 1
fi

success "环境检查完成"

# 2. 端口检查和进程清理函数
kill_port_process() {
    local port=$1
    local process_name=$2
    
    info "🔍 检查端口 ${port} 占用情况..."
    
    # 查找占用端口的进程
    local pids=$(lsof -ti:${port} 2>/dev/null || true)
    
    if [[ -n "${pids}" ]]; then
        warning "端口 ${port} 被占用，进程PID: ${pids}"
        info "正在终止 ${process_name} 进程..."
        
        # 首先尝试优雅终止
        echo "${pids}" | xargs -r kill -TERM 2>/dev/null || true
        sleep 2
        
        # 检查是否还有进程存在
        local remaining_pids=$(lsof -ti:${port} 2>/dev/null || true)
        if [[ -n "${remaining_pids}" ]]; then
            warning "优雅终止失败，强制终止进程..."
            echo "${remaining_pids}" | xargs -r kill -KILL 2>/dev/null || true
            sleep 1
        fi
        
        # 最终检查
        local final_pids=$(lsof -ti:${port} 2>/dev/null || true)
        if [[ -n "${final_pids}" ]]; then
            error "无法终止端口 ${port} 上的进程"
            return 1
        else
            success "端口 ${port} 已清理"
        fi
    else
        info "端口 ${port} 未被占用"
    fi
}

# 3. 清理现有进程
info "🧹 正在清理现有进程..."

# 清理后端进程
kill_port_process ${BACKEND_PORT} "Flask后端"

# 清理前端进程
kill_port_process ${FRONTEND_PORT} "Vite前端"
kill_port_process ${FRONTEND_ALT_PORT} "Vite前端(备用端口)"

# 额外清理：根据进程名查找并终止
info "🔍 检查残留的Flask和Vite进程..."
pkill -f "web_app.py" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true
sleep 1

success "进程清理完成"

# 4. 检查并安装依赖
info "📦 正在检查和安装依赖..."

# 激活Python虚拟环境
source "${VENV_PATH}/bin/activate"
info "Python虚拟环境已激活: $(which python)"

# 安装/更新Python依赖
if [[ -f "${PROJECT_DIR}/requirements.txt" ]]; then
    info "正在检查Python依赖..."
    pip install -r requirements.txt --quiet
    success "Python依赖检查完成"
fi

# 安装/更新Node.js依赖
info "正在检查Node.js依赖..."
if [[ ! -d "${PROJECT_DIR}/node_modules" ]] || [[ "${PROJECT_DIR}/package.json" -nt "${PROJECT_DIR}/node_modules" ]]; then
    info "安装Node.js依赖..."
    npm install --silent
else
    info "Node.js依赖已是最新"
fi
success "依赖检查完成"

# 5. 启动后端服务
info "🚀 正在启动后端服务..."

# 创建后端日志文件
BACKEND_LOG="${PROJECT_DIR}/backend.log"
> "${BACKEND_LOG}"

# 后台启动Flask应用
cd "${PROJECT_DIR}"
nohup python3 web_app.py > "${BACKEND_LOG}" 2>&1 &
BACKEND_PID=$!

# 等待后端启动
info "等待后端服务启动..."
for i in {1..30}; do
    if curl -s "http://localhost:${BACKEND_PORT}" >/dev/null 2>&1; then
        success "后端服务启动成功 (PID: ${BACKEND_PID})"
        break
    fi
    if ! kill -0 ${BACKEND_PID} 2>/dev/null; then
        error "后端服务启动失败"
        info "后端日志："
        tail -n 20 "${BACKEND_LOG}"
        exit 1
    fi
    sleep 1
done

# 最终检查后端是否成功启动
if ! curl -s "http://localhost:${BACKEND_PORT}" >/dev/null 2>&1; then
    error "后端服务启动超时"
    exit 1
fi

# 6. 启动前端服务
info "🌐 正在启动前端服务..."

# 创建前端日志文件
FRONTEND_LOG="${PROJECT_DIR}/frontend.log"
> "${FRONTEND_LOG}"

# 后台启动Vite开发服务器
nohup npm run dev > "${FRONTEND_LOG}" 2>&1 &
FRONTEND_PID=$!

# 等待前端启动
info "等待前端服务启动..."
FRONTEND_URL=""
for i in {1..60}; do
    # 检查前端进程是否还在运行
    if ! kill -0 ${FRONTEND_PID} 2>/dev/null; then
        error "前端服务启动失败"
        info "前端日志："
        tail -n 20 "${FRONTEND_LOG}"
        exit 1
    fi
    
    # 尝试不同端口
    if curl -s "http://localhost:${FRONTEND_PORT}" >/dev/null 2>&1; then
        FRONTEND_URL="http://localhost:${FRONTEND_PORT}"
        break
    elif curl -s "http://localhost:${FRONTEND_ALT_PORT}" >/dev/null 2>&1; then
        FRONTEND_URL="http://localhost:${FRONTEND_ALT_PORT}"
        break
    fi
    
    sleep 1
done

if [[ -z "${FRONTEND_URL}" ]]; then
    error "前端服务启动超时"
    info "前端日志："
    tail -n 20 "${FRONTEND_LOG}"
    exit 1
fi

success "前端服务启动成功 (PID: ${FRONTEND_PID})"

# 7. 健康检查
info "🏥 正在进行健康检查..."

# 检查后端API
if curl -s "http://localhost:${BACKEND_PORT}/api/statistics/config" >/dev/null 2>&1; then
    success "后端API响应正常"
else
    warning "后端API可能存在问题"
fi

# 检查前端页面
if curl -s "${FRONTEND_URL}" >/dev/null 2>&1; then
    success "前端页面响应正常"
else
    warning "前端页面可能存在问题"
fi

# 8. 显示启动信息
echo -e "\n${GREEN}🎉 重启完成！${NC}"
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                        服务信息                              ║${NC}"
echo -e "${CYAN}╠══════════════════════════════════════════════════════════════╣${NC}"
echo -e "${CYAN}║${NC} 🌐 前端地址: ${YELLOW}${FRONTEND_URL}${NC}"
echo -e "${CYAN}║${NC} 🔧 后端地址: ${YELLOW}http://localhost:${BACKEND_PORT}${NC}"
echo -e "${CYAN}║${NC} 📊 后端API:  ${YELLOW}http://localhost:${BACKEND_PORT}/api${NC}"
echo -e "${CYAN}║${NC}"
echo -e "${CYAN}║${NC} 📝 后端PID:  ${BACKEND_PID}"
echo -e "${CYAN}║${NC} 📝 前端PID:  ${FRONTEND_PID}"
echo -e "${CYAN}║${NC}"
echo -e "${CYAN}║${NC} 📋 日志文件:"
echo -e "${CYAN}║${NC}   - 重启日志: ${LOG_FILE}"
echo -e "${CYAN}║${NC}   - 后端日志: ${BACKEND_LOG}"
echo -e "${CYAN}║${NC}   - 前端日志: ${FRONTEND_LOG}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"

# 保存PID文件用于后续管理
echo "${BACKEND_PID}" > "${PROJECT_DIR}/.backend.pid"
echo "${FRONTEND_PID}" > "${PROJECT_DIR}/.frontend.pid"

success "PID文件已保存，可使用 ./stop.sh 停止服务"

# 9. 提供监控选项
echo -e "\n${BLUE}💡 提示：${NC}"
echo "  - 使用 ${YELLOW}./stop.sh${NC} 停止所有服务"
echo "  - 使用 ${YELLOW}./logs.sh${NC} 查看实时日志"
echo "  - 使用 ${YELLOW}Ctrl+C${NC} 停止此脚本但保持服务运行"

echo -e "\n${GREEN}✨ 重启成功！服务已在后台运行${NC}"
info "重启流程完成，服务运行正常" 