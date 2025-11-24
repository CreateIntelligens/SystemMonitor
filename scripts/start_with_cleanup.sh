#!/bin/bash

# 系統監控啟動腳本（包含圖片自動清理）- 週週分檔版本
# 此腳本會同時啟動Web服務、監控服務和定期圖片清理

echo "🚀 啟動系統監控（包含圖片自動清理）..."

# 載入環境變數（如果 .env 檔案存在）
if [ -f .env ]; then
    echo "📋 載入環境變數 (.env)"
    export $(grep -v '^#' .env | xargs)
fi

# 確保logs目錄存在（使用相對路徑）
mkdir -p logs

# 設置crontab用於定期圖片清理
# 每天凌晨2點執行圖片清理：使用環境變數設定
PLOTS_KEEP_DAYS=${PLOTS_KEEP_DAYS:-1}
echo "⏰ 設置定期圖片清理任務（每天凌晨2點）..."
echo "📅 資料庫使用週週分檔系統，不清理數據"
echo "0 2 * * * cd $(pwd) && /usr/local/bin/python scripts/cleanup.py --plots-days $PLOTS_KEEP_DAYS >> logs/cleanup.log 2>&1" > /tmp/cleanup_cron
crontab /tmp/cleanup_cron

# 啟動cron服務
echo "⚙️ 啟動cron服務..."
service cron start

# 立即執行一次清理（可選）
echo "🧹 執行初始圖片清理（保留 $PLOTS_KEEP_DAYS 天圖片）..."
python scripts/cleanup.py --plots-days $PLOTS_KEEP_DAYS >> logs/cleanup.log 2>&1

# 背景啟動監控服務
echo "📊 啟動監控服務..."
python backend/cli.py monitor --interval 1 > logs/monitor.log 2>&1 &

# 啟動Web服務（前台運行）
WEB_PORT=${WEB_PORT:-5000}
echo "🌐 啟動Web服務 (端口: $WEB_PORT)..."
exec python -m uvicorn backend.api:app --host 0.0.0.0 --port $WEB_PORT
