#!/bin/bash

# 系統監控工具操作腳本
# 用於 Docker 容器內外的操作管理

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置變數
CONTAINER_NAME="system_monitor"
DAEMON_CONTAINER_NAME="system_monitor_daemon"
WEB_PORT=5000

# 函數定義
print_header() {
    echo -e "${BLUE}🖥️  系統監控工具 v1.0${NC}"
    echo -e "${BLUE}=========================${NC}"
}

print_usage() {
    echo "使用方法: $0 <命令> [選項]"
    echo
    echo "🚀 快速命令:"
    echo "  start           智能啟動監控（自動選擇最佳方式）"
    echo "  stop            停止監控"
    echo "  status          查看監控狀態"
    echo "  plot [範圍]     生成圖表 (1h/6h/24h/7d/30d)"
    echo
    echo "🐳 Docker 命令:"
    echo "  start-web       啟動 Web 服務"
    echo "  start-monitor   啟動監控服務（會詢問執行方式）"
    echo "  logs            查看服務日誌"
    echo "  shell           進入容器 shell"
    echo
    echo "📊 數據管理:"
    echo "  export <文件>   導出數據到 CSV"
    echo "  cleanup         清理舊數據"
    echo
    echo "🛠️  維護命令:"
    echo "  build           構建 Docker 鏡像"
    echo "  clean           清理 Docker 資源"
    echo "  update          更新並重啟服務"
    echo
    echo "🎯 智能執行邏輯:"
    echo "  - 容器內：直接本機執行"
    echo "  - 本機完整環境：優先本機執行"
    echo "  - 本機環境不完整：自動使用 Docker"
    echo "  - Docker 啟動即自動監控（Web + 監控同時運行）"
    echo
    echo "範例:"
    echo "  $0 start               # 智能啟動監控"
    echo "  $0 plot 24h            # 生成 24 小時圖表"
    echo "  $0 status service      # 查看服務詳細狀態"
}

check_docker() {
    # 如果在容器內，跳過 Docker 檢查
    if [[ -f /.dockerenv ]]; then
        return 0
    fi
    
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker 未安裝${NC}"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}❌ Docker Compose 未安裝${NC}"
        exit 1
    fi
}

build_image() {
    echo -e "${BLUE}🔨 構建 Docker 鏡像...${NC}"
    docker-compose build --no-cache
    echo -e "${GREEN}✅ 鏡像構建完成${NC}"
}

start_web() {
    echo -e "${BLUE}🌐 啟動 Web 服務...${NC}"
    
    # 優先本機執行
    if command -v python &> /dev/null && [[ -f "app.py" ]]; then
        echo -e "${GREEN}✅ 使用本機 Python 環境${NC}"
        
        # 檢查端口是否被占用
        if lsof -i:${WEB_PORT} > /dev/null 2>&1; then
            echo -e "${YELLOW}⚠️  端口 ${WEB_PORT} 已被使用${NC}"
            return
        fi
        
        echo -e "${BLUE}🚀 啟動 Web 介面...${NC}"
        python app.py web --host 0.0.0.0 --port ${WEB_PORT}
    else
        echo -e "${YELLOW}🐳 使用 Docker 環境${NC}"
        docker-compose up -d monitor
        echo -e "${GREEN}✅ Web 服務已啟動${NC}"
        echo -e "${YELLOW}📍 訪問地址: http://localhost:${WEB_PORT}${NC}"
    fi
}

start_monitor() {
    echo -e "${BLUE}🔄 開始系統監控...${NC}"
    
    # 自動判斷並選擇最佳執行方式
    if [[ -f /.dockerenv ]]; then
        # 在容器內：直接本機執行
        echo -e "${YELLOW}🐳 檢測到容器環境，使用本機執行${NC}"
        start_monitor_local
    elif command -v python &> /dev/null && [[ -f "app.py" ]] && python -c "import psutil, fastapi" 2>/dev/null; then
        # 本機環境完整：優先本機執行
        echo -e "${GREEN}✅ 本機環境完整，使用本機執行${NC}"
        start_monitor_local
    elif command -v docker &> /dev/null; then
        # 本機環境不完整但有Docker：使用Docker
        echo -e "${YELLOW}🐳 本機環境不完整，使用 Docker 執行${NC}"
        start_monitor_docker_auto
    else
        # 都不可用
        echo -e "${RED}❌ 無法執行：缺少 Python 環境和 Docker${NC}"
        return 1
    fi
}

start_monitor_local() {
    # 檢查是否已經在運行
    if command -v pgrep &> /dev/null && pgrep -f "python src/system_monitor.py monitor" > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  監控服務已在運行${NC}"
        return
    elif [[ -f ".monitor_pid" ]]; then
        local existing_pid=$(cat .monitor_pid)
        if kill -0 "$existing_pid" 2>/dev/null; then
            echo -e "${YELLOW}⚠️  監控服務已在運行 (PID: $existing_pid)${NC}"
            return
        else
            rm -f .monitor_pid
        fi
    fi
    
    # 確保日誌目錄存在
    mkdir -p logs
    
    # 在背景啟動監控（1秒間隔）
    nohup python src/system_monitor.py monitor --interval 1 > logs/monitor_daemon.log 2>&1 &
    monitor_pid=$!
    echo $monitor_pid > .monitor_pid
    
    sleep 2
    if kill -0 $monitor_pid 2>/dev/null; then
        echo -e "${GREEN}✅ 監控服務已啟動 (PID: $monitor_pid)${NC}"
        echo -e "${YELLOW}📋 日誌: tail -f logs/monitor_daemon.log${NC}"
        echo -e "${YELLOW}🛑 停止: ./monitor.sh stop-monitor${NC}"
    else
        echo -e "${RED}❌ 監控服務啟動失敗${NC}"
        rm -f .monitor_pid
    fi
}

start_monitor_with_choice() {
    echo -e "${BLUE}🔄 啟動監控服務...${NC}"
    
    # 檢查可用的執行方式
    local can_run_local=false
    local can_run_docker=false
    
    if command -v python &> /dev/null && [[ -f "app.py" ]]; then
        can_run_local=true
    fi
    
    if command -v docker &> /dev/null; then
        can_run_docker=true
    fi
    
    # 如果都不可用
    if [[ "$can_run_local" == false && "$can_run_docker" == false ]]; then
        echo -e "${RED}❌ 無法執行：缺少 Python 或 Docker 環境${NC}"
        return 1
    fi
    
    # 顯示選項
    echo "請選擇執行方式："
    local options=()
    local choice_map=()
    
    if [[ "$can_run_local" == true ]]; then
        options+=("本機背景執行")
        choice_map+=("local")
    fi
    
    if [[ "$can_run_docker" == true ]]; then
        options+=("Docker 容器執行")
        choice_map+=("docker")
    fi
    
    # 顯示選項供用戶選擇
    for i in "${!options[@]}"; do
        echo "  $((i+1)). ${options[$i]}"
    done
    
    echo -n "請輸入選擇 [1]: "
    read -r user_choice
    user_choice=${user_choice:-1}
    
    if [[ "$user_choice" =~ ^[0-9]+$ ]] && [[ "$user_choice" -ge 1 ]] && [[ "$user_choice" -le ${#options[@]} ]]; then
        local selected_method="${choice_map[$((user_choice-1))]}"
        echo -e "${GREEN}已選擇: ${options[$((user_choice-1))]}${NC}"
    else
        echo -e "${RED}❌ 無效選擇${NC}"
        return 1
    fi
    
    # 執行選擇的方法
    if [[ "$selected_method" == "local" ]]; then
        start_monitor_local
    elif [[ "$selected_method" == "docker" ]]; then
        start_monitor_docker
    fi
}

start_monitor_docker() {
    # 檢查容器是否已在運行
    if docker ps --format "table {{.Names}}" | grep -q "^system_monitor_only$"; then
        echo -e "${YELLOW}⚠️  Docker 監控服務已在運行${NC}"
        return
    fi
    
    docker-compose --profile monitoring-only up -d monitor-only
    echo -e "${GREEN}✅ Docker 監控服務已啟動${NC}"
}

start_monitor_docker_auto() {
    # 檢查主容器是否已在運行（Web + 監控）
    if docker ps --format "table {{.Names}}" | grep -q "^system_monitor$"; then
        echo -e "${GREEN}✅ Docker 主服務已運行（包含監控）${NC}"
        echo -e "${YELLOW}📍 訪問地址: http://localhost:${WEB_PORT}${NC}"
        return
    fi
    
    # 啟動主服務（自動包含監控）
    docker-compose up -d monitor
    sleep 3
    
    if docker ps --format "table {{.Names}}" | grep -q "^system_monitor$"; then
        echo -e "${GREEN}✅ Docker 主服務已啟動（Web + 監控）${NC}"
        echo -e "${YELLOW}📍 Web 介面: http://localhost:${WEB_PORT}${NC}"
        echo -e "${YELLOW}📊 自動監控: 已啟動（1秒間隔）${NC}"
    else
        echo -e "${RED}❌ Docker 服務啟動失敗${NC}"
    fi
}

stop_services() {
    echo -e "${BLUE}🛑 停止所有服務...${NC}"
    
    # 停止本機監控服務
    stop_monitor_local
    
    # 停止 Docker 服務
    docker-compose --profile monitoring-only down 2>/dev/null || true
    docker-compose down
    
    echo -e "${GREEN}✅ 所有服務已停止${NC}"
}

stop_monitor() {
    echo -e "${BLUE}🛑 停止監控服務...${NC}"
    
    # 停止本機服務
    if stop_monitor_local; then
        return 0
    fi
    
    # 停止 Docker 監控服務
    if docker ps --format "table {{.Names}}" | grep -q "^system_monitor_only$"; then
        docker-compose --profile monitoring-only stop monitor-only
        echo -e "${GREEN}✅ Docker 純監控服務已停止${NC}"
        return 0
    elif docker ps --format "table {{.Names}}" | grep -q "^system_monitor$"; then
        echo -e "${YELLOW}⚠️  主服務正在運行（Web + 監控），只能停止整個服務${NC}"
        echo -e "${YELLOW}💡 使用 '$0 stop' 停止所有服務${NC}"
        return 0
    else
        echo -e "${YELLOW}ℹ️  沒有找到運行中的監控服務${NC}"
    fi
}

stop_monitor_local() {
    local stopped=false
    
    # 通過 PID 文件停止
    if [[ -f ".monitor_pid" ]]; then
        local pid=$(cat .monitor_pid)
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid"
            echo -e "${GREEN}✅ 監控服務已停止 (PID: $pid)${NC}"
            stopped=true
        fi
        rm -f .monitor_pid
    fi
    
    # 通過進程名停止（如果pgrep可用）
    if command -v pgrep &> /dev/null && pgrep -f "python src/system_monitor.py monitor" > /dev/null 2>&1; then
        if command -v pkill &> /dev/null; then
            pkill -f "python src/system_monitor.py monitor"
            echo -e "${GREEN}✅ 監控背景程序已停止${NC}"
            stopped=true
        fi
    fi
    
    if [[ "$stopped" == false ]]; then
        return 1
    fi
    
    return 0
}

restart_services() {
    echo -e "${BLUE}🔄 重啟服務...${NC}"
    stop_services
    sleep 2
    start_web
    echo -e "${GREEN}✅ 服務重啟完成${NC}"
}

show_logs() {
    container=${1:-monitor}
    echo -e "${BLUE}📋 顯示容器日誌: ${container}${NC}"
    if [[ "$container" == "daemon" ]]; then
        docker-compose logs -f monitor-daemon
    else
        docker-compose logs -f monitor
    fi
}

enter_shell() {
    echo -e "${BLUE}🐚 進入容器 shell...${NC}"
    if docker ps --format "table {{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        docker exec -it $CONTAINER_NAME bash
    else
        echo -e "${YELLOW}⚠️  Web 容器未運行，啟動臨時容器...${NC}"
        docker-compose run --rm monitor bash
    fi
}

monitor_status() {
    echo -e "${BLUE}📊 監控狀態檢查...${NC}"
    python src/system_monitor.py status
}

generate_plots() {
    timespan=${1:-24h}
    echo -e "${BLUE}📈 生成圖表 (${timespan})...${NC}"
    python src/system_monitor.py plot --timespan $timespan
}

export_data() {
    output_file=${1:-"monitor_data_$(date +%Y%m%d_%H%M%S).csv"}
    echo -e "${BLUE}💾 導出數據到: ${output_file}${NC}"
    python src/system_monitor.py export $output_file
    echo -e "${GREEN}✅ 數據已導出到 ${output_file}${NC}"
}

cleanup_data() {
    keep_days=${1:-30}
    echo -e "${BLUE}🧹 清理 ${keep_days} 天前的數據...${NC}"
    python src/system_monitor.py cleanup --keep-days $keep_days
}

clean_docker() {
    echo -e "${BLUE}🧹 清理 Docker 資源...${NC}"
    docker-compose --profile monitoring down --rmi all --volumes --remove-orphans
    echo -e "${GREEN}✅ Docker 資源已清理${NC}"
}

update_services() {
    echo -e "${BLUE}🔄 更新服務...${NC}"
    stop_services
    build_image
    start_web
    echo -e "${GREEN}✅ 服務更新完成${NC}"
}

show_service_status() {
    echo -e "${BLUE}📊 服務狀態:${NC}"
    echo
    
    # 檢查主服務容器狀態（Web + 監控）
    if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "^system_monitor"; then
        echo -e "${GREEN}🌐 主服務: 運行中（Web + 監控）${NC}"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep "^system_monitor"
    else
        echo -e "${RED}🌐 主服務: 停止${NC}"
    fi
    
    echo
    
    # 檢查純監控服務容器狀態
    if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "^system_monitor_only"; then
        echo -e "${GREEN}🔄 純監控服務: 運行中${NC}"
        docker ps --format "table {{.Names}}\t{{.Status}}" | grep "^system_monitor_only"
    else
        echo -e "${RED}🔄 純監控服務: 停止${NC}"
    fi
    
    # 檢查本機監控進程
    echo
    if command -v pgrep &> /dev/null && pgrep -f "python src/system_monitor.py monitor" > /dev/null 2>&1; then
        echo -e "${GREEN}🔄 本機監控: 運行中${NC}"
        pgrep -f "python src/system_monitor.py monitor" 2>/dev/null | head -3 | while read pid; do
            echo -e "  PID: $pid"
        done
    elif [[ -f ".monitor_pid" ]]; then
        local pid=$(cat .monitor_pid)
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${GREEN}🔄 本機監控: 運行中${NC}"
            echo -e "  PID: $pid"
        else
            echo -e "${RED}🔄 本機監控: 停止${NC}"
            rm -f .monitor_pid
        fi
    else
        echo -e "${RED}🔄 本機監控: 停止${NC}"
    fi
    
    echo
    echo -e "${YELLOW}💡 使用 '$0 logs' 查看詳細日誌${NC}"
    echo -e "${YELLOW}💡 使用 '$0 shell' 進入容器操作${NC}"
}

# 主邏輯
main() {
    print_header
    
    # 檢查 Docker
    check_docker
    
    # 處理命令
    case "${1:-help}" in
        # Docker 命令
        "start-web")
            start_web
            ;;
        "start-monitor")
            start_monitor_with_choice
            ;;
        "start-all")
            start_web
            start_monitor
            ;;
        "stop")
            stop_services
            ;;
        "restart")
            restart_services
            ;;
        "logs")
            show_logs $2
            ;;
        "shell")
            enter_shell
            ;;
        
        # 監控命令
        "start")
            start_monitor
            ;;
        "stop")
            stop_monitor
            ;;
        "status")
            if [[ "$2" == "service" ]]; then
                show_service_status
            else
                monitor_status
            fi
            ;;
        "plot")
            generate_plots $2
            ;;
        "export")
            export_data $2
            ;;
        "cleanup")
            cleanup_data $2
            ;;
        
        # 維護命令
        "build")
            build_image
            ;;
        "clean")
            clean_docker
            ;;
        "update")
            update_services
            ;;
        
        # 幫助
        "help"|"-h"|"--help"|*)
            print_usage
            ;;
    esac
}

# 執行主函數
main "$@"