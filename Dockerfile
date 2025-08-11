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

# 只複製 requirements.txt 來安裝依賴
COPY requirements.txt .

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製並設置腳本權限
COPY scripts/start_with_cleanup.sh scripts/
RUN chmod +x scripts/start_with_cleanup.sh

# 暴露 Web 介面端口（可透過環境變數調整）
ARG WEB_PORT=5000
EXPOSE $WEB_PORT

# 預設命令
CMD ["python", "app.py", "status"]