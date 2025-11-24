#!/bin/bash

# 啟動監控程序 (背景執行)
echo "Starting System Monitor..."
python backend/cli.py monitor --interval 1 > logs/monitor.log 2>&1 &
MONITOR_PID=$!

# 啟動 API Server (前台執行)
echo "Starting API Server..."
exec python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000
