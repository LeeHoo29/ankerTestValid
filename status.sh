#!/bin/bash

# 任务管理平台 - 状态检查脚本
# 作者: 系统管理员
# 版本: 1.0.0
# 描述: 检查前后端服务运行状态

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 配置变量
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PORT=5001
FRONTEND_PORT=3000
FRONTEND_ALT_PORT=3001
BACKEND_PID_FILE="${PROJECT_DIR}/.backend.pid"
FRONTEND_PID_FILE="${PROJECT_DIR}/.frontend.pid"

echo -e "${CYAN}🔍 任务管理平台状态检查${NC}"
echo "========================================"

# 检查进程状态
check_process_status() {
    local pid_file=$1
    local service_name=$2
    local port=$3
    
    echo -e "\n${BLUE}📋 ${service_name}状态:${NC}"
    
    if [[ -f "${pid_file}" ]]; then
        local pid=$(cat "${pid_file}")
        if kill -0 "${pid}" 2>/dev/null; then
            echo -e "  PID: ${GREEN}${pid} (运行中)${NC}"
            
            # 检查端口
            if lsof -i:${port} &>/dev/null; then
                echo -e "  端口: ${GREEN}${port} (监听中)${NC}"
                
                # 检查HTTP响应
                if curl -s "http://localhost:${port}" >/dev/null 2>&1; then
                    echo -e "  HTTP: ${GREEN}正常响应${NC}"
                else
                    echo -e "  HTTP: ${YELLOW}无响应${NC}"
                fi
            else
                echo -e "  端口: ${RED}${port} (未监听)${NC}"
            fi
        else
            echo -e "  PID: ${RED}${pid} (进程不存在)${NC}"
        fi
    else
        echo -e "  PID: ${RED}无PID文件${NC}"
        
        # 检查是否有进程在端口上运行
        local port_pid=$(lsof -ti:${port} 2>/dev/null || true)
        if [[ -n "${port_pid}" ]]; then
            echo -e "  端口: ${YELLOW}${port} 被其他进程占用 (PID: ${port_pid})${NC}"
        else
            echo -e "  端口: ${RED}${port} (无进程)${NC}"
        fi
    fi
}

# 检查后端状态
check_process_status "${BACKEND_PID_FILE}" "后端服务" "${BACKEND_PORT}"

# 检查前端状态
echo -e "\n${BLUE}📋 前端服务状态:${NC}"

if [[ -f "${FRONTEND_PID_FILE}" ]]; then
    frontend_pid=$(cat "${FRONTEND_PID_FILE}")
    if kill -0 "${frontend_pid}" 2>/dev/null; then
        echo -e "  PID: ${GREEN}${frontend_pid} (运行中)${NC}"
        
        # 检查前端端口（可能是3000或3001）
        frontend_url=""
        if lsof -i:${FRONTEND_PORT} &>/dev/null; then
            echo -e "  端口: ${GREEN}${FRONTEND_PORT} (监听中)${NC}"
            frontend_url="http://localhost:${FRONTEND_PORT}"
        elif lsof -i:${FRONTEND_ALT_PORT} &>/dev/null; then
            echo -e "  端口: ${GREEN}${FRONTEND_ALT_PORT} (监听中)${NC}"
            frontend_url="http://localhost:${FRONTEND_ALT_PORT}"
        else
            echo -e "  端口: ${RED}未在 ${FRONTEND_PORT} 或 ${FRONTEND_ALT_PORT} 监听${NC}"
        fi
        
        if [[ -n "${frontend_url}" ]]; then
            if curl -s "${frontend_url}" >/dev/null 2>&1; then
                echo -e "  HTTP: ${GREEN}正常响应${NC}"
                echo -e "  地址: ${CYAN}${frontend_url}${NC}"
            else
                echo -e "  HTTP: ${YELLOW}无响应${NC}"
            fi
        fi
    else
        echo -e "  PID: ${RED}${frontend_pid} (进程不存在)${NC}"
    fi
else
    echo -e "  PID: ${RED}无PID文件${NC}"
    
    # 检查前端端口
    port_3000_pid=$(lsof -ti:${FRONTEND_PORT} 2>/dev/null || true)
    port_3001_pid=$(lsof -ti:${FRONTEND_ALT_PORT} 2>/dev/null || true)
    
    if [[ -n "${port_3000_pid}" ]]; then
        echo -e "  端口: ${YELLOW}${FRONTEND_PORT} 被其他进程占用 (PID: ${port_3000_pid})${NC}"
    elif [[ -n "${port_3001_pid}" ]]; then
        echo -e "  端口: ${YELLOW}${FRONTEND_ALT_PORT} 被其他进程占用 (PID: ${port_3001_pid})${NC}"
    else
        echo -e "  端口: ${RED}${FRONTEND_PORT}/${FRONTEND_ALT_PORT} (无进程)${NC}"
    fi
fi

# 检查数据库连接（如果后端运行）
echo -e "\n${BLUE}📋 数据库状态:${NC}"
if curl -s "http://localhost:${BACKEND_PORT}/api/statistics/config" >/dev/null 2>&1; then
    echo -e "  连接: ${GREEN}正常${NC}"
else
    echo -e "  连接: ${RED}无法访问${NC}"
fi

# 显示系统资源使用情况
echo -e "\n${BLUE}📋 系统资源:${NC}"
# macOS内存命令
memory_info=$(vm_stat 2>/dev/null | awk '
BEGIN { 
    free=0; used=0; 
}
/Pages free/ { 
    free=$3*4096/(1024*1024*1024) 
}
/Pages active/ { 
    used+=$3*4096/(1024*1024*1024) 
}
/Pages inactive/ { 
    used+=$3*4096/(1024*1024*1024) 
}
/Pages speculative/ { 
    used+=$3*4096/(1024*1024*1024) 
}
/Pages wired down/ { 
    used+=$4*4096/(1024*1024*1024) 
}
END { 
    printf "%.1fGB/%.1fGB", used, used+free 
}')
echo -e "  内存使用: ${memory_info:-未知}"
echo -e "  磁盘使用: $(df -h "${PROJECT_DIR}" | awk 'NR==2 {print $3"/"$2" ("$5")"}')"

# 检查日志文件
echo -e "\n${BLUE}📋 日志文件:${NC}"
for log_file in restart.log backend.log frontend.log; do
    if [[ -f "${PROJECT_DIR}/${log_file}" ]]; then
        size=$(ls -lh "${PROJECT_DIR}/${log_file}" | awk '{print $5}')
        modified=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M" "${PROJECT_DIR}/${log_file}" 2>/dev/null || date -r "${PROJECT_DIR}/${log_file}" "+%Y-%m-%d %H:%M" 2>/dev/null || echo "未知时间")
        echo -e "  ${log_file}: ${GREEN}${size} (${modified})${NC}"
    else
        echo -e "  ${log_file}: ${RED}不存在${NC}"
    fi
done

# 总结状态
echo -e "\n${CYAN}📊 总结:${NC}"

# 检查后端
backend_ok=false
if [[ -f "${BACKEND_PID_FILE}" ]]; then
    backend_pid=$(cat "${BACKEND_PID_FILE}")
    if kill -0 "${backend_pid}" 2>/dev/null && curl -s "http://localhost:${BACKEND_PORT}" >/dev/null 2>&1; then
        backend_ok=true
    fi
fi

# 检查前端
frontend_ok=false
if [[ -f "${FRONTEND_PID_FILE}" ]]; then
    frontend_pid=$(cat "${FRONTEND_PID_FILE}")
    if kill -0 "${frontend_pid}" 2>/dev/null; then
        if curl -s "http://localhost:${FRONTEND_PORT}" >/dev/null 2>&1 || curl -s "http://localhost:${FRONTEND_ALT_PORT}" >/dev/null 2>&1; then
            frontend_ok=true
        fi
    fi
fi

if $backend_ok && $frontend_ok; then
    echo -e "  状态: ${GREEN}✅ 所有服务正常运行${NC}"
    echo -e "  建议: ${BLUE}服务运行良好${NC}"
elif $backend_ok; then
    echo -e "  状态: ${YELLOW}⚠️  仅后端运行${NC}"
    echo -e "  建议: ${YELLOW}运行 ./restart.sh 重启前端${NC}"
elif $frontend_ok; then
    echo -e "  状态: ${YELLOW}⚠️  仅前端运行${NC}"
    echo -e "  建议: ${YELLOW}运行 ./restart.sh 重启后端${NC}"
else
    echo -e "  状态: ${RED}❌ 所有服务已停止${NC}"
    echo -e "  建议: ${GREEN}运行 ./restart.sh 启动服务${NC}"
fi

echo "" 