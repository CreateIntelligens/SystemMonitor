#!/bin/bash

# 簡單的清理執行腳本
# 用法：
#   ./cleanup.sh            # 使用預設設置（7天資料，1天圖片）
#   ./cleanup.sh 3 1        # 自定義設置（3天資料，1天圖片）

DATA_DAYS=${1:-7}    # 預設保留7天資料
PLOTS_DAYS=${2:-1}   # 預設保留1天圖片

echo "🧹 開始清理..."
echo "📅 資料保留: ${DATA_DAYS} 天"
echo "🖼️ 圖片保留: ${PLOTS_DAYS} 天"

docker-compose exec monitor python scripts/cleanup.py --data-days $DATA_DAYS --plots-days $PLOTS_DAYS

echo "✅ 清理完成!"