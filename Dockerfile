FROM python:3.11-slim

# 設置環境變數
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Taipei

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    curl \
    htop \
    procps \
    cron \
    && rm -rf /var/lib/apt/lists/*

# 創建工作目錄
WORKDIR /app

# 只複製後端 requirements.txt 來安裝依賴
COPY backend/requirements.txt ./requirements.txt

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製後端程式碼與腳本
COPY backend ./backend
COPY entrypoint.sh monitor.sh ./ 
COPY scripts ./scripts

# 確保腳本可執行
RUN chmod +x entrypoint.sh monitor.sh && mkdir -p logs data plots

# 暴露 API 端口
EXPOSE 8000

# 使用 entrypoint 啟動
CMD ["./entrypoint.sh"]
