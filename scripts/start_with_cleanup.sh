#!/bin/bash

# 系統監控啟動腳本（包含自動清理）
# 此腳本會同時啟動Web服務、監控服務和定期清理

echo "🚀 啟動系統監控（包含自動清理）..."

# 確保logs目錄存在
mkdir -p /app/logs

# 設置crontab用於定期清理
# 每天凌晨2點執行清理：使用環境變數設定
DATA_KEEP_DAYS=${DATA_KEEP_DAYS:-7}
PLOTS_KEEP_DAYS=${PLOTS_KEEP_DAYS:-1}
echo "⏰ 設置定期清理任務（每天凌晨2點）..."
echo "0 2 * * * cd /app && /usr/local/bin/python scripts/cleanup.py --data-days $DATA_KEEP_DAYS --plots-days $PLOTS_KEEP_DAYS >> /app/logs/cleanup.log 2>&1" > /tmp/cleanup_cron
crontab /tmp/cleanup_cron

# 啟動cron服務
echo "⚙️ 啟動cron服務..."
service cron start

# 立即執行一次清理（可選）
echo "🧹 執行初始清理（保留 $DATA_KEEP_DAYS 天資料，$PLOTS_KEEP_DAYS 天圖片）..."
/usr/local/bin/python scripts/cleanup.py --data-days $DATA_KEEP_DAYS --plots-days $PLOTS_KEEP_DAYS >> /app/logs/cleanup.log 2>&1

# 背景啟動監控服務
echo "📊 啟動監控服務..."
/usr/local/bin/python src/system_monitor.py monitor --interval 1 > /app/logs/monitor.log 2>&1 &

# 啟動Web服務（前台運行）
WEB_PORT=${WEB_PORT:-5000}
echo "🌐 啟動Web服務 (端口: $WEB_PORT)..."
exec python -m uvicorn app:app --host 0.0.0.0 --port $WEB_PORT