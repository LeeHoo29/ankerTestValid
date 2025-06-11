#!/bin/bash

# 任务管理平台 - 服务停止脚本
# 作者: 系统管理员
# 版本: 1.0.0
# 描述: 安全停止前后端服务

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 配置变量
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PID_FILE="${PROJECT_DIR}/.backend.pid"
FRONTEND_PID_FILE="${PROJECT_DIR}/.frontend.pid"

echo -e "${CYAN}⏹️  正在停止任务管理平台服务...${NC}"

# 停止函数
stop_service() {
    local pid_file=$1
    local service_name=$2
    
    if [[ -f "${pid_file}" ]]; then
        local pid=$(cat "${pid_file}")
        if kill -0 "${pid}" 2>/dev/null; then
            echo -e "${BLUE}停止 ${service_name} (PID: ${pid})...${NC}"
            kill -TERM "${pid}" 2>/dev/null || true
            sleep 2
            
            # 检查是否还在运行
            if kill -0 "${pid}" 2>/dev/null; then
                echo -e "${YELLOW}强制停止 ${service_name}...${NC}"
                kill -KILL "${pid}" 2>/dev/null || true
            fi
            
            echo -e "${GREEN}✅ ${service_name} 已停止${NC}"
        else
            echo -e "${YELLOW}⚠️  ${service_name} 进程不存在${NC}"
        fi
        rm -f "${pid_file}"
    else
        echo -e "${YELLOW}⚠️  ${service_name} PID文件不存在${NC}"
    fi
}

# 停止服务
stop_service "${BACKEND_PID_FILE}" "后端服务"
stop_service "${FRONTEND_PID_FILE}" "前端服务"

# 清理端口
echo -e "${BLUE}🧹 清理残留进程...${NC}"
pkill -f "web_app.py" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true

echo -e "${GREEN}✅ 所有服务已停止${NC}" 