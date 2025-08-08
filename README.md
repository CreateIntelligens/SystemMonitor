# 系統監控工具

🖥️ 專業級系統資源監控與可視化工具，支援 GPU/CPU/RAM 實時監控、數據存儲與圖表生成。

## ✨ 特點

- 🔄 **實時監控** - GPU/CPU/RAM/VRAM 使用率與溫度
- 📊 **數據可視化** - 多種圖表類型，支援時序分析  
- ⚡ **FastAPI Web 介面** - 現代化 API 與 Web 儀表板
- 🐳 **Docker 部署** - 完整容器化，支援 GPU 加速
- 📁 **數據存儲** - SQLite 數據庫，支援數據導出
- 🛠️ **操作腳本** - 一鍵操作，簡化管理

## 🚀 快速開始

### 本機直接運行（推薦）

```bash
# 安裝依賴並運行
python scripts/run_local.py

# 直接啟動 Web 介面
python app.py web
# 🌐 http://localhost:5000
# 📖 API 文檔: http://localhost:5000/docs

# 或使用操作腳本
./monitor.sh status        # 自動偵測本機執行
```

### 使用 Docker

```bash
# 構建並啟動 Web 服務
./monitor.sh build
./monitor.sh start-web
```

### 操作腳本使用

```bash
# 啟動服務
./monitor.sh start-web       # 啟動 Web 介面
./monitor.sh start-monitor   # 啟動後台監控
./monitor.sh start-all       # 啟動所有服務

# 監控操作
./monitor.sh status          # 查看監控狀態
./monitor.sh plot 24h        # 生成 24 小時圖表
./monitor.sh shell           # 進入容器操作
./monitor.sh logs            # 查看服務日誌

# 維護操作
./monitor.sh stop            # 停止服務
./monitor.sh restart         # 重啟服務
./monitor.sh clean           # 清理 Docker 資源
```

## 📂 專案結構

```
system-monitor/
├── app.py                 # 主程式入口 ⭐
├── monitor.sh             # 操作腳本
├── src/                   # 源碼目錄
│   ├── system_monitor.py  # 核心監控邏輯
│   ├── core/              # 核心模塊
│   │   ├── collectors.py  # 數據收集器
│   │   ├── storage.py     # 數據存儲
│   │   └── visualizer.py  # 圖表可視化
│   ├── web/               # Web 介面
│   │   └── app.py         # FastAPI 應用
│   └── utils/             # 工具模塊
│       ├── config.py      # 配置管理
│       └── logger.py      # 日誌管理
├── config/                # 配置文件
├── data/                  # 數據存儲
├── logs/                  # 日誌文件
├── scripts/               # 輔助腳本
├── docker-compose.yml     # Docker 配置
├── Dockerfile            
├── requirements.txt      
└── README.md            
```

## 🖥️ 使用方式

### 1. Web 儀表板（推薦）

```bash
./monitor.sh start-web
# 🌐 Web 介面: http://localhost:5000
# 📖 API 文檔: http://localhost:5000/docs
```

**Web 功能：**
- 📊 實時系統狀態顯示
- 🎛️ 監控開始/停止控制  
- 📈 一鍵生成圖表
- 🔄 自動數據更新
- 📱 響應式設計

### 2. 命令行介面

```bash
# 進入容器
./monitor.sh shell

# 直接命令
python app.py status
python app.py monitor --interval 30
python app.py plot --timespan 24h
python app.py export data.csv
```

### 3. Docker 服務模式

```bash
# Web 服務（端口 5000）
docker-compose up -d monitor

# 後台監控服務
docker-compose --profile monitoring up -d monitor-daemon
```

## 📊 監控功能

### 數據收集
- **CPU**: 使用率、核心數、頻率、每核心使用率
- **RAM**: 使用率、已用/總容量、Swap 使用情況
- **GPU**: 使用率、VRAM 使用率、溫度（NVIDIA）
- **時序**: 時間戳、數據持久化

### 圖表類型
- **系統概覽**: 2x2 子圖，全面展示系統狀態
- **資源對比**: 多條線圖，對比不同資源使用趨勢
- **記憶體詳情**: RAM/VRAM 絕對使用量圖表
- **使用率分佈**: 直方圖分析資源使用模式

### 時間範圍
- `1h` - 過去 1 小時
- `6h` - 過去 6 小時  
- `24h` - 過去 24 小時
- `7d` - 過去 7 天
- `30d` - 過去 30 天

## 🐳 Docker 配置

### 服務配置
```yaml
# Web 介面服務
monitor:
  ports: ["5000:5000"]
  command: python app.py web --host 0.0.0.0 --port 5000

# 後台監控服務  
monitor-daemon:
  command: python app.py monitor --interval 30
  profiles: ["monitoring"]
```

### GPU 支援
```bash
# GPU 加速支援
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]
```

## 🔧 環境需求

### 系統要求
- **作業系統**: Linux/Windows/macOS
- **Docker**: >= 20.10
- **Docker Compose**: >= 2.0
- **GPU** (可選): NVIDIA GPU + nvidia-docker2

### Python 依賴
```
psutil>=5.9.0          # 系統監控
pandas>=2.0.0          # 數據處理
matplotlib>=3.7.0      # 圖表生成
fastapi>=0.104.0       # Web API 框架
uvicorn>=0.24.0        # ASGI 伺服器
nvidia-ml-py>=12.535.0 # NVIDIA GPU 支援
```

## 📈 使用案例

### 案例 1: 開發環境監控
```bash
# 啟動輕量級監控
./monitor.sh start-web
# Web 介面即時查看系統狀態
```

### 案例 2: 伺服器性能分析
```bash
# 啟動持續監控
./monitor.sh start-all
# 定期生成報告
./monitor.sh plot 7d
./monitor.sh export weekly_report.csv
```

### 案例 3: GPU 工作負載監控
```bash
# 高頻監控（每10秒）
./monitor.sh shell
python3 system_monitor.py monitor --interval 10
# 重點關注 GPU/VRAM 使用情況
```

## 🛠️ 進階配置

### 自定義數據庫位置
```bash
python3 system_monitor.py --db /path/to/monitoring.db monitor
```

### 自定義 Web 服務
```bash
python3 system_monitor.py web --host 0.0.0.0 --port 8080
```

### 數據清理自動化
```bash
# 定期清理 30 天前數據
python3 system_monitor.py cleanup --keep-days 30
```

## 📊 FastAPI 端點

Web 服務提供 RESTful API：

```
GET  /                        # Web 儀表板
GET  /api/status              # 獲取系統狀態
POST /api/monitor/{action}    # 監控控制 (start/stop)
GET  /api/plots               # 獲取圖表列表
POST /api/plots?timespan=24h  # 生成圖表
GET  /plots/{filename}        # 獲取圖片文件
GET  /docs                    # API 文檔 (Swagger UI)
GET  /redoc                   # API 文檔 (ReDoc)
```

## 🔍 故障排除

### 常見問題

**GPU 不可用**
```bash
# 檢查 nvidia-smi
nvidia-smi
# 檢查 Docker GPU 支援
docker run --gpus all nvidia/cuda:11.0-base nvidia-smi
```

**容器權限問題**
```bash
# 確保 Docker 有足夠權限訪問系統信息
docker-compose up --privileged
```

**端口佔用**
```bash
# 檢查端口使用
netstat -tlnp | grep 5000
# 更換端口
./monitor.sh start-web --port 8080
```

## 📝 開發指南

### 本地開發
```bash
# 安裝依賴
pip install -r requirements.txt

# 運行測試
python3 collectors.py
python3 storage.py  
python3 visualizer.py

# 啟動開發服務
python app.py web --debug
# API 文檔: http://localhost:5000/docs
```

### 代碼結構
```
- src/core/        # 核心業務邏輯
- src/web/         # FastAPI Web 服務
- src/utils/       # 配置與工具
- app.py          # 統一入口點
```

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

## 📄 授權

MIT License

---

🎯 **專為技術人員設計的系統監控解決方案**

✨ **一鍵部署，即開即用，專業可視化**