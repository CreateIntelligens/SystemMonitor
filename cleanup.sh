#!/bin/bash

# 圖片清理執行腳本 - 週週分檔版本
# 用法：
#   ./cleanup.sh            # 使用預設設置（1天圖片）
#   ./cleanup.sh 2          # 自定義設置（2天圖片）

PLOTS_DAYS=${1:-1}   # 預設保留1天圖片

echo "🧹 開始清理圖片..."
echo "📅 資料庫: 使用週週分檔，不清理數據"
echo "🖼️ 圖片保留: ${PLOTS_DAYS} 天"

docker-compose exec monitor python scripts/cleanup.py --plots-days $PLOTS_DAYS

echo "✅ 圖片清理完成!"