# 系統監控工具

專業級系統資源監控與可視化工具，支援跨機器進程分析、多資料庫管理。

## 快速開始

### 啟動服務
```bash
# 智能啟動（自動選擇本機或Docker）
./monitor.sh start

# 或直接運行Web界面
python app.py --host 0.0.0.0 --port 5000
# 訪問: http://localhost:5000
```

### Docker部署
```bash
./monitor.sh build
./monitor.sh start-web
```

## 核心功能

### 系統監控
- **即時監控**: CPU/RAM/GPU/VRAM使用率、溫度
- **進程監控**: GPU進程詳細資訊，支援歷史分析
- **數據存儲**: SQLite數據庫，自動清理舊數據

### 圖表生成
- **系統圖表**: 系統概覽、資源對比、記憶體使用、分佈圖
- **進程對比**: 多PID四合一圖表（CPU/GPU/RAM/VRAM）
- **跨機器分析**: 支援不同資料庫的進程對比

### 多資料庫支援
- **跨機器分析**: 使用其他機器的資料庫進行分析
- **CLI/腳本支援**: 命令行和Web界面都支援資料庫選擇
- **使用範例**: 分析多台伺服器的進程資源使用

## 使用方法

### monitor.sh 腳本

#### 基本指令
```bash
./monitor.sh start              # 智能啟動監控
./monitor.sh stop               # 停止服務
./monitor.sh status             # 查看狀態
./monitor.sh status service     # 查看詳細服務狀態
```

#### 系統圖表
```bash
./monitor.sh plot 24h                          # 生成24小時系統圖表
./monitor.sh plot 2d --database=server2.db    # 使用其他機器資料庫
```

#### 進程對比圖
```bash
./monitor.sh plot-processes 1234 5678 2h                    # 繪製PID 1234和5678的2小時對比
./monitor.sh plot-processes 999 1h --database=remote.db     # 跨機器進程分析
./monitor.sh plot-processes 1111 2222 3333 3d --output=result.png  # 指定輸出檔案
```

#### 數據管理
```bash
./monitor.sh export report.csv  # 導出數據
./monitor.sh cleanup            # 清理舊數據（30天前）
./monitor.sh logs               # 查看服務日誌
```

### CLI直接使用

#### 監控操作
```bash
python src/system_monitor.py monitor           # 開始監控
python src/system_monitor.py status            # 查看狀態
python src/system_monitor.py gpu-processes     # 查看GPU進程
```

#### 圖表生成
```bash
# 系統圖表
python src/system_monitor.py plot --timespan 24h
python src/system_monitor.py plot --timespan 2d --database server2.db

# 進程對比圖
python src/system_monitor.py plot-processes 1234 5678 2h
python src/system_monitor.py plot-processes 999 1h --database remote.db --output result.png
```

#### 數據操作
```bash
python src/system_monitor.py export data.csv
python src/system_monitor.py cleanup --keep-days 30
python src/system_monitor.py web --host 0.0.0.0 --port 5000
```

### Web界面使用

#### 功能特點
- **即時狀態**: 系統資源使用率、溫度、主機資訊
- **進程分析**: 支援篩選、搜尋、歷史進程查看
- **多資料庫**: 前端選擇不同資料庫進行分析
- **圖表生成**: 一鍵生成系統圖表和進程對比圖

#### 進程分析流程
1. 選擇資料庫（本機或自定義）
2. 選擇時間範圍（目前運行/1h/6h/24h/3d/7d/自定義）
3. 使用篩選器找到目標進程
4. 勾選要對比的進程
5. 點擊「繪製選定進程圖表」

## 時間格式支援

- `30m` - 30分鐘
- `2h` - 2小時  
- `3d` - 3天
- `1w` - 1週

## 跨機器使用案例

### 場景1: 多伺服器負載對比
```bash
# 本機分析
./monitor.sh plot-processes 1001 1002 24h

# Server2分析  
./monitor.sh plot-processes 2001 2002 24h --database=server2_monitoring.db

# Server3分析
./monitor.sh plot-processes 3001 3002 24h --database=server3_monitoring.db
```

### 場景2: 跨機器同一進程對比
```bash
# 假設多台機器都運行相同應用（不同PID）
./monitor.sh plot-processes 1234 1h --database=server1.db --output=server1_app.png
./monitor.sh plot-processes 5678 1h --database=server2.db --output=server2_app.png
./monitor.sh plot-processes 9012 1h --database=server3.db --output=server3_app.png
```

### 場景3: 使用Web界面跨機器分析
1. 將其他機器的 `monitoring.db` 複製到本機
2. 重命名為 `server2.db`, `server3.db` 等
3. 在Web界面選擇對應資料庫
4. 進行進程分析和圖表生成

## 專案結構

```
system-monitor/
├── app.py                    # 主程式入口
├── monitor.sh                # 操作腳本（支援多資料庫）
├── src/
│   ├── system_monitor.py     # CLI工具（支援多資料庫）
│   ├── core/
│   │   ├── collectors.py     # 數據收集器
│   │   ├── storage.py        # 數據存儲
│   │   └── visualizer.py     # 圖表生成（4合1進程對比）
│   └── utils/
├── templates/
│   └── index.html           # Web界面（多資料庫選擇）
├── static/js/
│   └── app.js              # 前端邏輯（多資料庫支援）
├── plots/                  # 圖表輸出目錄
├── monitoring.db           # 主資料庫
└── *.db                   # 其他機器的資料庫檔案
```

## 環境需求

- **Python**: >= 3.8
- **系統**: Linux/Windows/macOS  
- **GPU**: NVIDIA（可選，需nvidia-ml-py）
- **Docker**: >= 20.10（可選）

## 故障排除

### GPU不可用
```bash
nvidia-smi  # 檢查GPU
pip install nvidia-ml-py
```

### 資料庫檔案不存在
```bash
ls *.db  # 檢查資料庫檔案
# 確認檔案路徑正確
```

### 端口佔用
```bash
netstat -tlnp | grep 5000
# 或更換端口
python app.py --port 8080
```

---

**專為技術人員設計，一鍵部署，跨機器分析**