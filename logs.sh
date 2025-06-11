#!/bin/bash

# 任务管理平台 - 日志查看脚本
# 作者: 系统管理员
# 版本: 1.0.0
# 描述: 实时查看前后端日志

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 配置变量
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_LOG="${PROJECT_DIR}/backend.log"
FRONTEND_LOG="${PROJECT_DIR}/frontend.log"
RESTART_LOG="${PROJECT_DIR}/restart.log"

# 显示使用说明
show_usage() {
    echo -e "${CYAN}📋 日志查看工具${NC}"
    echo -e "${BLUE}用法: $0 [选项]${NC}"
    echo ""
    echo -e "${YELLOW}选项:${NC}"
    echo "  backend, be     - 查看后端日志"
    echo "  frontend, fe    - 查看前端日志" 
    echo "  restart, rs     - 查看重启日志"
    echo "  all, a          - 同时查看所有日志"
    echo "  help, h         - 显示此帮助信息"
    echo ""
    echo -e "${GREEN}示例:${NC}"
    echo "  $0 backend      # 查看后端日志"
    echo "  $0 all          # 查看所有日志"
}

# 检查日志文件是否存在
check_log_file() {
    local log_file=$1
    local log_name=$2
    
    if [[ ! -f "${log_file}" ]]; then
        echo -e "${RED}❌ ${log_name}日志文件不存在: ${log_file}${NC}"
        echo -e "${YELLOW}💡 请先运行 ./restart.sh 启动服务${NC}"
        return 1
    fi
    return 0
}

# 查看单个日志文件
view_single_log() {
    local log_file=$1
    local log_name=$2
    
    if check_log_file "${log_file}" "${log_name}"; then
        echo -e "${GREEN}📖 正在查看${log_name}日志...${NC}"
        echo -e "${BLUE}文件路径: ${log_file}${NC}"
        echo -e "${YELLOW}按 Ctrl+C 退出${NC}"
        echo "----------------------------------------"
        tail -f "${log_file}"
    fi
}

# 查看所有日志
view_all_logs() {
    echo -e "${GREEN}📖 正在查看所有日志...${NC}"
    echo -e "${YELLOW}按 Ctrl+C 退出${NC}"
    echo "========================================"
    
    # 使用 multitail 如果可用，否则使用 tail
    if command -v multitail &> /dev/null; then
        multitail \
            -cT ANSI \
            -t "后端日志" "${BACKEND_LOG}" \
            -t "前端日志" "${FRONTEND_LOG}" \
            -t "重启日志" "${RESTART_LOG}"
    else
        echo -e "${YELLOW}💡 安装 multitail 可获得更好的多日志查看体验${NC}"
        echo "   brew install multitail  # macOS"
        echo "   sudo apt install multitail  # Ubuntu"
        echo ""
        echo -e "${BLUE}当前使用基础模式查看后端日志...${NC}"
        tail -f "${BACKEND_LOG}"
    fi
}

# 处理参数
case "${1:-help}" in
    "backend"|"be")
        view_single_log "${BACKEND_LOG}" "后端"
        ;;
    "frontend"|"fe")
        view_single_log "${FRONTEND_LOG}" "前端"
        ;;
    "restart"|"rs")
        view_single_log "${RESTART_LOG}" "重启"
        ;;
    "all"|"a")
        view_all_logs
        ;;
    "help"|"h"|*)
        show_usage
        ;;
esac 