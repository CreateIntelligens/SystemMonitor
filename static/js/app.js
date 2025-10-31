// 全域變數
let allGpuProcesses = [];
let activeFilters = [];
let currentMode = 'monitor'; // 'monitor' 或 'stats'
let lastUpdateTime = null;
let statusInterval = null;

// --- **新** 時鐘功能 ---
function updateClock() {
    const clockContainer = document.getElementById('realtime-clock');
    if (clockContainer) {
        const now = new Date();
        const dateString = now.toLocaleDateString('zh-TW', { 
            year: 'numeric', 
            month: '2-digit', 
            day: '2-digit' 
        });
        const timeString = now.toLocaleTimeString('zh-TW', { hour12: false });
        clockContainer.textContent = `${dateString} ${timeString} (UTC+8)`;
    }
}

// --- 初始資料載入與顯示 ---
async function loadStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        updateStatusDisplay(data);
    } catch (error) {
        console.error('載入狀態失敗:', error);
    }
}

// 載入週資料庫列表
async function loadWeeklyDatabases() {
    try {
        const response = await fetch('/api/databases');
        const data = await response.json();
        
        if (data.success && data.databases) {
            updateDatabaseSelectors(data.databases);
        }
    } catch (error) {
        console.error('載入週資料庫列表失敗:', error);
    }
}

// 更新資料庫選擇器
function updateDatabaseSelectors(databases) {
    const selectors = [
        document.getElementById('database-select'),
        document.getElementById('system-database-select')
    ];
    
    selectors.forEach(select => {
        if (!select) return;
        
        // 清除現有選項
        select.innerHTML = '<option value="">週週分檔 (自動合併)</option>';
        
        // 添加週資料庫選項
        databases.forEach(db => {
            const option = document.createElement('option');
            option.value = db.filename;
            option.textContent = `${db.display_name} (${db.size_mb}MB)`;
            if (db.is_current) {
                option.textContent += ' [當前]';
            }
            select.appendChild(option);
        });
        
        // 添加自定義選項
        const customOption = document.createElement('option');
        customOption.value = 'custom';
        customOption.textContent = '其他資料庫...';
        select.appendChild(customOption);
    });
}

function updateStatusDisplay(data) {
    if (data.system_info) {
        const hostInfo = `${data.system_info.hostname || '未知主機'}`;
        const ipInfo = data.system_info.local_ip ? ` (${data.system_info.local_ip})` : '';
        document.getElementById('hostname').textContent = hostInfo + ipInfo;
    }
    const grid = document.getElementById('statusGrid');
    grid.innerHTML = `
        <div class="status-card"><h3>🖥️ CPU (${data.system_info?.cpu_count|| 'N/A'}核心)</h3><div class="metric"><span>使用率</span><span>${data.cpu_usage?.toFixed(1)}%</span></div><div class="metric"><span>來源</span><span>${data.cpu_source}</span></div></div>
        <div class="status-card"><h3>💾 記憶體 (${data.ram_total_gb?.toFixed(1)}GB)</h3><div class="metric"><span>已使用</span><span>${data.ram_used_gb?.toFixed(1)}GB / ${data.ram_total_gb?.toFixed(1)}GB</span></div><div class="metric"><span>使用率</span><span>${data.ram_usage?.toFixed(1)}%</span></div><div class="metric"><span>來源</span><span>${data.ram_source}</span></div></div>
        <div class="status-card"><h3>🎮 ${data.system_info?.gpu_name|| 'GPU'}</h3><div class="metric"><span>使用率</span><span>${data.gpu_usage?data.gpu_usage.toFixed(1)+'%':'N/A'}</span></div><div class="metric"><span>VRAM總用量</span><span title="某些環境下無法顯示單個進程的GPU記憶體使用量">${data.vram_used_mb?Math.round(data.vram_used_mb/1024*10)/10+'GB':'N/A'} / ${data.vram_total_mb?Math.round(data.vram_total_mb/1024*10)/10+'GB':'N/A'}</span></div><div class="metric"><span>溫度</span><span>${data.gpu_temperature?data.gpu_temperature+'°C':'N/A'}</span></div></div>
        <div class="status-card"><h3>📈 資料庫</h3><div class="metric"><span>記錄數</span><span>${data.total_records?.toLocaleString()}</span></div><div class="metric"><span>大小</span><span>${data.database_size_mb?.toFixed(2)} MB</span></div><div class="metric"><span>時間範圍</span><span>${data.earliest_record?new Date(data.earliest_record).toLocaleDateString('zh-TW'):'N/A'} ~ 現在</span></div></div>
    `;
}

// 更新設定顯示
function updateSettingsDisplay() {
    const settingsText = document.getElementById('settings-text');
    const databaseSelect = document.getElementById('database-select');
    const customDbInput = document.getElementById('custom-database-input');
    const timespanSelect = document.getElementById('process-timespan-select');
    const customTimespanInput = document.getElementById('custom-timespan-input');
    
    if (!settingsText) return;
    
    // 獲取資料庫資訊
    let databaseInfo = '週週分檔 (自動合併)';
    if (databaseSelect && databaseSelect.value === 'custom') {
        const customDb = customDbInput ? customDbInput.value.trim() : '';
        databaseInfo = customDb ? `其他資料庫 (${customDb})` : '其他資料庫 (未指定)';
    } else if (databaseSelect && databaseSelect.value && databaseSelect.value !== '') {
        // 顯示選定的週資料庫
        const selectedOption = databaseSelect.options[databaseSelect.selectedIndex];
        databaseInfo = selectedOption ? selectedOption.text : databaseSelect.value;
    }
    
    // 獲取時間範圍資訊
    let timeInfo = '即時進程';
    if (currentMode === 'stats') {
        if (timespanSelect) {
            if (timespanSelect.value === 'custom') {
                const customTime = customTimespanInput ? customTimespanInput.value.trim() : '';
                timeInfo = customTime ? `自定義時間 (${customTime})` : '自定義時間 (未指定)';
            } else {
                const selectedOption = timespanSelect.options[timespanSelect.selectedIndex];
                timeInfo = selectedOption ? selectedOption.text : timespanSelect.value;
            }
        }
    }
    
    // 更新顯示
    const modeIcon = currentMode === 'monitor' ? '📊' : '📈';
    settingsText.textContent = `${modeIcon} 目前設定：${databaseInfo} | ${timeInfo}`;
}

// 切換模式
function switchMode(mode) {
    currentMode = mode;
    
    // 更新按鈕樣式
    const monitorBtn = document.getElementById('monitor-mode-btn');
    const statsBtn = document.getElementById('stats-mode-btn');
    const timespanSelect = document.getElementById('process-timespan-select');
    const customInput = document.getElementById('custom-timespan-input');
    const processLiveIndicator = document.getElementById('process-live-indicator');
    const processDatabaseControls = document.getElementById('process-database-controls');
    
    if (mode === 'monitor') {
        monitorBtn.style.background = 'var(--active-tab-bg)';
        monitorBtn.style.color = 'var(--active-tab-text)';
        statsBtn.style.background = 'var(--card-bg)';
        statsBtn.style.color = 'var(--text-primary)';
        
        // 即時進程模式：顯示實時指示器，隱藏DB選擇
        processLiveIndicator.style.display = 'flex';
        processDatabaseControls.style.display = 'none';
        timespanSelect.value = 'current';
        timespanSelect.disabled = true;
        timespanSelect.style.opacity = '0.5';
        customInput.style.display = 'none';
        
    } else {
        monitorBtn.style.background = 'var(--card-bg)';
        monitorBtn.style.color = 'var(--text-primary)';
        statsBtn.style.background = 'var(--active-tab-bg)';
        statsBtn.style.color = 'var(--active-tab-text)';
        
        // 歷史分析模式：隱藏實時指示器，顯示DB選擇
        processLiveIndicator.style.display = 'none';
        processDatabaseControls.style.display = 'flex';
        timespanSelect.disabled = false;
        timespanSelect.style.opacity = '1';
        
        // 預設使用 1h
        if (timespanSelect.value === 'current') {
            timespanSelect.value = '1h';
        }
    }
    
    // 更新設定顯示
    updateSettingsDisplay();
}

// 確認設定並載入數據
function confirmSettings() {
    // 更新設定顯示
    updateSettingsDisplay();
    
    // 載入數據
    showGpuProcesses();
}

async function showGpuProcesses() {
    const timespanSelect = document.getElementById('process-timespan-select');
    let timespan = timespanSelect ? timespanSelect.value : 'current';
    
    // 即時進程模式強制使用 current
    if (currentMode === 'monitor') {
        timespan = 'current';
    }
    
    // 處理自定義時間輸入
    if (timespan === 'custom') {
        const customInput = document.getElementById('custom-timespan-input');
        const customValue = customInput ? customInput.value.trim() : '';
        
        if (!customValue) {
            document.getElementById('filteredProcessList').innerHTML = '<h3>進程列表</h3><p>請輸入自定義時間範圍（例：2d, 12h, 30m）</p>';
            return;
        }
        
        // 驗證自定義時間格式
        if (!/^\d+[mhd]$/.test(customValue)) {
            document.getElementById('filteredProcessList').innerHTML = '<h3>進程列表</h3><p>時間格式錯誤！請使用格式：數字+單位（m=分鐘, h=小時, d=天）<br>例：30m, 2h, 5d</p>';
            return;
        }
        
        timespan = customValue;
    }
    
    try {
        let response, data;
        
        if (timespan === 'current') {
            // 載入目前運行的進程
            response = await fetch('/api/gpu-processes');
            data = await response.json();
            allGpuProcesses = (data.current || []).map(proc => ({
                ...proc,
                status: 'running',
                name: proc.name,
                gpu_memory_mb: proc.gpu_memory_mb || 0,
                cpu_percent: proc.cpu_percent || 0,
                ram_mb: proc.ram_mb || 0,
                start_time: proc.start_time || 'Unknown'
            }));
        } else {
            // 載入歷史進程，傳遞資料庫參數
            const databaseSelect = document.getElementById('database-select');
            const customDatabaseInput = document.getElementById('custom-database-input');
            let selectedDatabase = 'monitoring.db';
            
            if (databaseSelect && databaseSelect.value === 'custom') {
                selectedDatabase = customDatabaseInput ? customDatabaseInput.value.trim() : 'monitoring.db';
            } else if (databaseSelect && databaseSelect.value !== 'monitoring.db') {
                selectedDatabase = databaseSelect.value;
            }
            
            const requestBody = selectedDatabase !== 'monitoring.db' ? 
                { database_file: selectedDatabase } : {};
            
            response = await fetch(`/api/all-processes/${timespan}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });
            data = await response.json();
            
            if (data.success) {
                allGpuProcesses = data.processes.map(proc => ({
                    pid: proc.pid,
                    name: proc.process_name,
                    command: proc.command,
                    gpu_memory_mb: proc.avg_gpu_memory_mb,
                    cpu_percent: proc.avg_cpu_percent,
                    ram_mb: proc.avg_ram_mb,
                    start_time: proc.first_seen,
                    last_seen: proc.last_seen,
                    record_count: proc.record_count,
                    status: proc.status,
                    container_source: '歷史記錄'
                }));
            } else {
                throw new Error(data.error || '載入歷史進程失敗');
            }
        }
        
        // 更新最後更新時間
        lastUpdateTime = new Date();
        
        applyFilters();
    } catch (error) {
        console.error('獲取進程失敗:', error);
        const isHistorical = timespan !== 'current';
        const errorMessage = isHistorical ? '此時間範圍內沒有找到進程記錄，請嘗試更長的時間範圍。' : '無法獲取當前運行的進程。';
        document.getElementById('filteredProcessList').innerHTML = `<h3>進程列表</h3><p>${errorMessage}</p>`;
    }
}

function renderProcessTable(processes, containerId, title) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    // 保存滾輪位置
    let scrollTop = 0;
    const existingScrollContainer = container.querySelector('.process-table-container');
    if (existingScrollContainer) {
        scrollTop = existingScrollContainer.scrollTop;
    }
    
    let html = '';
    
    if (currentMode === 'monitor') {
        // 📊 即時進程模式
        const updateTimeStr = lastUpdateTime ? 
            `最後更新: ${lastUpdateTime.toLocaleTimeString('zh-TW', { hour12: false })}` : 
            '載入中...';
        html = `<h3>📊 即時進程 (自動更新) <span style="font-size: 0.8rem; font-weight: normal; color: var(--text-secondary);">${updateTimeStr}</span></h3>`;
        if (processes.length > 0) {
            const headers = '<th><input type="checkbox" id="select-all-processes" onclick="toggleSelectAll(this)"></th><th>PID</th><th>容器來源</th><th>進程名</th><th>指令</th><th>GPU記憶體</th><th>GPU使用率</th><th>CPU %</th><th>RAM (GB)</th><th>啟動時間</th>';
            html += `<div class="process-table-container"><table class="process-table"><thead><tr>${headers}</tr></thead><tbody>`;
            
            processes.forEach(proc => {
                    let memoryDisplay = proc.gpu_memory_mb > 0 ? `${proc.gpu_memory_mb} MB` : 'N/A';
                    const containerDisplay = proc.container_source || proc.container || '主機';
                    const gpuUtilDisplay = proc.gpu_utilization > 0 ? `${proc.gpu_utilization}%` : 'N/A';
                    html += `<tr>
                    <td><input type="checkbox" class="process-checkbox" data-pid="${proc.pid}"></td>
                    <td>${proc.pid}</td>
                    <td title="${containerDisplay}">${containerDisplay}</td>
                    <td>${proc.name}</td>
                    <td class="command-cell" title="${proc.command}">${proc.command}</td>
                    <td>${memoryDisplay}</td>
                    <td>${gpuUtilDisplay}</td>
                    <td>${proc.cpu_percent}%</td>
                    <td>${(proc.ram_mb / 1024).toFixed(2)}</td>
                    <td>${proc.start_time}</td>
                </tr>`;
                });
            html += '</tbody></table></div>';
        } else {
            html += '<p>目前沒有運行中的GPU進程。</p>';
        }
    } else {
        // 📈 歷史分析模式
        const timespanSelect = document.getElementById('process-timespan-select');
        const timespan = timespanSelect ? timespanSelect.value : '1h';
        
        // 獲取當前使用的資料庫名稱
        const databaseSelect = document.getElementById('database-select');
        const customDatabaseInput = document.getElementById('custom-database-input');
        let databaseName = 'monitoring.db';
        if (databaseSelect && databaseSelect.value === 'custom' && customDatabaseInput && customDatabaseInput.value.trim()) {
            databaseName = customDatabaseInput.value.trim();
        } else if (databaseSelect) {
            databaseName = databaseSelect.value;
        }
        
        html = `<h3>📈 歷史分析 (${timespan} 內的進程統計) 
                <span style="font-size: 1.1rem; color: var(--accent-grad-start); margin-left: 15px;">📊 ${databaseName}</span>
                <button onclick="refreshHistoryData()" style="margin-left: 10px; padding: 4px 8px; font-size: 0.8rem; background: var(--accent-grad-start); color: white; border: none; border-radius: 4px; cursor: pointer;">🔄 重新整理</button></h3>`;
        
        if (processes.length > 0) {
            const headers = '<th><input type="checkbox" id="select-all-processes" onclick="toggleSelectAll(this)"></th><th>狀態</th><th>PID</th><th>進程名</th><th>指令</th><th>平均GPU記憶體</th><th>平均CPU %</th><th>平均RAM (GB)</th><th>首次記錄</th><th>最後記錄</th><th>記錄數</th>';
            html += `<div class="process-table-container"><table class="process-table"><thead><tr>${headers}</tr></thead><tbody>`;
            
            processes.forEach(proc => {
                let memoryDisplay = proc.gpu_memory_mb > 0 ? `${proc.gpu_memory_mb} MB` : 'N/A';
                const statusIcon = proc.status === 'running' ? '🟢' : '🔴';
                const statusText = proc.status === 'running' ? '運行中' : '已結束';
                html += `<tr>
                    <td><input type="checkbox" class="process-checkbox" data-pid="${proc.pid}"></td>
                    <td>${statusIcon} ${statusText}</td>
                    <td>${proc.pid}</td>
                    <td>${proc.name}</td>
                    <td class="command-cell" title="${proc.command}">${proc.command}</td>
                    <td>${memoryDisplay}</td>
                    <td>${proc.cpu_percent}%</td>
                    <td>${(proc.ram_mb / 1024).toFixed(2)}</td>
                    <td>${proc.start_time}</td>
                    <td>${proc.last_seen || 'N/A'}</td>
                    <td>${proc.record_count || 0}</td>
                </tr>`;
            });
            html += '</tbody></table></div>';
        } else {
            html += '<p>該時間範圍內沒有找到進程記錄。</p>';
        }
    }
    
    container.innerHTML = html;
    
    // 恢復滾輪位置
    if (scrollTop > 0) {
        setTimeout(() => {
            const newScrollContainer = container.querySelector('.process-table-container');
            if (newScrollContainer) {
                newScrollContainer.scrollTop = scrollTop;
            }
        }, 50); // 稍微延遲以確保DOM更新完成
    }
}

// --- 篩選標籤 (Pill) 系統 ---

function renderFilterPills() {
    const container = document.getElementById('filter-pills-container');
    container.innerHTML = activeFilters.map(filter => `
        <div class="filter-pill" data-filter-id="${filter.id}">
            <span>${filter.label}</span>
            <button class="close-btn" onclick="removeFilter('${filter.id}')">&times;</button>
        </div>
    `).join('');
}

function addFilter(filter) {
    if (!activeFilters.some(f => f.id === filter.id)) {
        activeFilters.push(filter);
        applyFilters();
    }
}

function removeFilter(filterId) {
    activeFilters = activeFilters.filter(f => f.id !== filterId);
    applyFilters();
}

function applyFilters() {
    let filtered = [...allGpuProcesses];
    activeFilters.forEach(filter => {
        switch (filter.type) {
            case 'search':
                // 全文搜尋：搜尋 PID、進程名、指令
                const searchTerm = filter.value.toLowerCase();
                filtered = filtered.filter(p => 
                    String(p.pid).includes(searchTerm) ||
                    p.name.toLowerCase().includes(searchTerm) ||
                    p.command.toLowerCase().includes(searchTerm)
                );
                break;
            case 'pid': filtered = filtered.filter(p => String(p.pid).includes(filter.value)); break;
            case 'name': filtered = filtered.filter(p => p.name.toLowerCase().includes(filter.value.toLowerCase())); break;
            case 'cmd': filtered = filtered.filter(p => p.command.toLowerCase().includes(filter.value.toLowerCase())); break;
            case 'ram_gt': filtered = filtered.filter(p => p.ram_mb > filter.value); break;
            case 'gpu_gt': filtered = filtered.filter(p => p.gpu_memory_mb > filter.value); break;
        }
    });
    renderProcessTable(filtered, 'filteredProcessList', '進程列表');
    renderFilterPills();
}

function createFilterFromUI() {
    const typeSelect = document.getElementById('filter-type-select');
    const valueInput = document.getElementById('filter-value-input');
    const type = typeSelect.value;
    const value = valueInput.value.trim();
    if (!value) return;
    let filter = {};
    const typeText = typeSelect.options[typeSelect.selectedIndex].text;
    
    if (type === 'ram_gt' || type === 'gpu_gt') {
        const numValue = parseInt(value);
        if (isNaN(numValue)) { alert('請輸入有效的數字'); return; }
        filter = { id: `${type}:${value}`, type: type, value: numValue, label: `${typeText}: ${value}MB` };
    } else if (type === 'search') {
        filter = { id: `${type}:${value}`, type: type, value: value, label: `搜尋: ${value}` };
    } else {
        filter = { id: `${type}:${value}`, type: type, value: value, label: `${typeText}: ${value}` };
    }
    addFilter(filter);
    valueInput.value = '';
    valueInput.focus();
}

// --- 歷史數據重新整理 ---
async function refreshHistoryData() {
    const btn = event.target;
    const originalText = btn.innerHTML;
    
    // 顯示載入狀態
    btn.innerHTML = '⏳ 載入中...';
    btn.disabled = true;
    btn.style.opacity = '0.6';
    
    try {
        await showGpuProcesses();
        
        // 顯示成功狀態
        btn.innerHTML = '✅ 已更新';
        btn.style.background = '#28a745';
        
        // 1秒後恢復原狀
        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.style.background = 'var(--accent-grad-start)';
            btn.disabled = false;
            btn.style.opacity = '1';
        }, 1000);
        
    } catch (error) {
        // 顯示錯誤狀態
        btn.innerHTML = '❌ 失敗';
        btn.style.background = '#dc3545';
        
        // 2秒後恢復原狀
        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.style.background = 'var(--accent-grad-start)';
            btn.disabled = false;
            btn.style.opacity = '1';
        }, 2000);
    }
}

// --- 進程繪圖功能 ---

function toggleSelectAll(source) {
    const checkboxes = document.querySelectorAll('#filteredProcessList .process-checkbox');
    checkboxes.forEach(checkbox => { checkbox.checked = source.checked; });
}

async function plotSelectedProcesses() {
    const checkedPIDs = Array.from(document.querySelectorAll('#filteredProcessList .process-checkbox:checked'))
                             .map(cb => parseInt(cb.getAttribute('data-pid'), 10))
                             .filter(pid => !isNaN(pid));
    if (checkedPIDs.length === 0) {
        alert('請至少選擇一個進程來繪圖。');
        return;
    }
    
    // 使用當前選擇的時間範圍，如果是 "current" 則預設為 1h
    const timespanSelect = document.getElementById('process-timespan-select');
    let timespan = timespanSelect ? timespanSelect.value : '1h';
    
    if (timespan === 'current') {
        timespan = '1h'; // 目前運行的進程用1小時數據
    } else if (timespan === 'custom') {
        const customInput = document.getElementById('custom-timespan-input');
        const customValue = customInput ? customInput.value.trim() : '';
        
        if (!customValue || !/^\d+[mhd]$/.test(customValue)) {
            alert('請輸入有效的自定義時間範圍（例：2d, 12h, 30m）');
            return;
        }
        
        timespan = customValue;
    }
    
    const chartContainer = document.getElementById('process-chart-container');
    chartContainer.innerHTML = `<div class="loading"><h3>⏳ 正在生成進程圖表...</h3></div>`;
    try {
        console.log('🔍 發送進程繪圖請求:', { pids: checkedPIDs, timespan: timespan });
        // 獲取當前選中的資料庫
        const databaseSelect = document.getElementById('database-select');
        const customDatabaseInput = document.getElementById('custom-database-input');
        let selectedDatabase = 'monitoring.db';
        
        if (databaseSelect && databaseSelect.value === 'custom') {
            selectedDatabase = customDatabaseInput ? customDatabaseInput.value.trim() : 'monitoring.db';
        } else if (databaseSelect && databaseSelect.value !== 'monitoring.db') {
            selectedDatabase = databaseSelect.value;
        }
        
        console.log('🔍 畫圖請求參數:', { pids: checkedPIDs, timespan: timespan, database_file: selectedDatabase });
        
        const response = await fetch('/api/processes/plot-comparison', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pids: checkedPIDs, timespan: timespan, database_file: selectedDatabase })
        });
        const result = await response.json();
        console.log('🔍 API 返回結果:', result);
        if (result.success) {
            // 處理進程對比圖表結果
            if (result.chart) {
                // 新格式：單個圖表
                chartContainer.innerHTML = `
                    <div class="chart-card">
                        <h4>${result.chart.title}</h4>
                        <img src="/plots/${result.chart.path}" alt="${result.chart.title}" onclick="window.open('/plots/${result.chart.path}', '_blank')">
                    </div>`;
            } else if (result.charts) {
                // 舊格式：多個圖表（臨時兼容）
                const chartsHtml = result.charts.map(chart => `
                    <div class="chart-card">
                        <h4>${chart.title}</h4>
                        <img src="/plots/${chart.path}" alt="${chart.title}" onclick="window.open('/plots/${chart.path}', '_blank')">
                    </div>`).join('');
                chartContainer.innerHTML = chartsHtml;
            } else {
                chartContainer.innerHTML = `<p style="color: red;">API 返回了意外的數據格式</p>`;
            }
        } else {
            chartContainer.innerHTML = `<p style="color: red;">圖表生成失敗: ${result.error}</p>`;
        }
    } catch (error) {
        console.error('進程繪圖失敗:', error);
        chartContainer.innerHTML = `<p style="color: red;">圖表生成時發生客戶端錯誤。</p>`;
    }
}

// --- 時間選擇器下拉功能 ---
function showDropdown() {
    const dropdown = document.getElementById('timeDropdown');
    if (dropdown) {
        dropdown.style.display = 'block';
    }
}

function hideDropdown() {
    setTimeout(() => {
        const dropdown = document.getElementById('timeDropdown');
        if (dropdown) {
            dropdown.style.display = 'none';
        }
    }, 200); // 延遲隱藏，讓點擊事件能觸發
}

function selectTime(value) {
    const input = document.getElementById('timeRange');
    if (input) {
        input.value = value;
    }
    hideDropdown();
}

function filterDropdown() {
    // 可以在這裡實作篩選功能
}

// --- 系統圖表功能 ---

async function generateSelectedChart() {
    const timeRange = document.getElementById('timeRange').value.trim();
    if (!timeRange) { alert('請選擇時間範圍'); return; }
    generateChart(timeRange);
}

async function generateChart(timespan) {
    const loading = document.getElementById('loading');
    const chartsGrid = document.getElementById('chartsGrid');
    loading.style.display = 'block';
    chartsGrid.innerHTML = '';
    
    try {
        // 獲取選定的資料庫（使用系統圖表的選擇器）
        const systemDatabaseSelect = document.getElementById('system-database-select');
        const systemCustomDbInput = document.getElementById('system-custom-database-input');
        let selectedDatabase = null; // 預設為 null，表示使用週週分檔系統
        
        if (systemDatabaseSelect) {
            if (systemDatabaseSelect.value === 'custom') {
                selectedDatabase = systemCustomDbInput ? systemCustomDbInput.value.trim() : null;
                if (!selectedDatabase) {
                    alert('請輸入自定義資料庫檔案名稱');
                    return;
                }
            } else if (systemDatabaseSelect.value && systemDatabaseSelect.value !== '') {
                selectedDatabase = systemDatabaseSelect.value;
            }
        }
        
        // 構建請求體
        const requestBody = selectedDatabase ? 
            { database_file: selectedDatabase } : {};
        
        const response = await fetch(`/api/plot/${timespan}`, { 
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });
        
        const result = await response.json();
        if (result.success) {
            chartsGrid.innerHTML = result.charts.map(chart => `
                <div class="chart-card">
                    <h4>${chart.title}</h4>
                    <img src="/plots/${chart.path}" alt="${chart.title}" onclick="window.open('/plots/${chart.path}', '_blank')">
                </div>
            `).join('');
        } else {
            alert('圖表生成失敗: ' + result.error);
        }
    } catch (error) {
        alert('生成圖表時發生錯誤');
    } finally {
        loading.style.display = 'none';
    }
}

// --- 頁面初始化 ---
window.onload = function() {
    // 啟動時鐘
    updateClock();
    setInterval(updateClock, 1000);

    // 載入初始數據
    loadStatus();
    loadWeeklyDatabases(); // 載入週資料庫列表
    
    // 初始化模式狀態（確保UI與currentMode同步）
    switchMode(currentMode);
    
    // 初始載入（即時模式才自動載入）
    if (currentMode === 'monitor') {
        showGpuProcesses();
        // 啟動自動更新狀態
        if (!statusInterval) {
            statusInterval = setInterval(loadStatus, 2000);
        }
    }

    // 綁定事件監聽器
    document.getElementById('add-filter-btn').addEventListener('click', createFilterFromUI);
    document.getElementById('filter-value-input').addEventListener('keydown', (event) => {
        if (event.key === 'Enter') createFilterFromUI();
    });
    document.getElementById('plot-selected-btn').addEventListener('click', plotSelectedProcesses);
    document.getElementById('database-select').addEventListener('change', function() {
        const select = this;
        const customInput = document.getElementById('custom-database-input');
        
        if (select.value === 'custom') {
            customInput.style.display = 'inline-block';
            customInput.focus();
        } else {
            customInput.style.display = 'none';
            updateSettingsDisplay();
        }
    });
    
    document.getElementById('custom-database-input').addEventListener('keydown', function(event) {
        if (event.key === 'Enter') {
            updateSettingsDisplay();
        }
    });
    
    document.getElementById('process-timespan-select').addEventListener('change', function() {
        const select = this;
        const customInput = document.getElementById('custom-timespan-input');
        
        if (select.value === 'custom') {
            customInput.style.display = 'inline-block';
            customInput.focus();
        } else {
            customInput.style.display = 'none';
            updateSettingsDisplay();
        }
    });
    
    document.getElementById('custom-timespan-input').addEventListener('keydown', function(event) {
        if (event.key === 'Enter') {
            updateSettingsDisplay();
        }
    });

    // 綁定模式切換按鈕
    document.getElementById('monitor-mode-btn').addEventListener('click', () => switchMode('monitor'));
    document.getElementById('stats-mode-btn').addEventListener('click', () => switchMode('stats'));

    // 綁定確認按鈕
    document.getElementById('confirm-settings-btn').addEventListener('click', confirmSettings);

    // 綁定系統圖表資料庫選擇器
    document.getElementById('system-database-select').addEventListener('change', function() {
        const select = this;
        const customInput = document.getElementById('system-custom-database-input');
        
        if (select.value === 'custom') {
            customInput.style.display = 'inline-block';
            customInput.focus();
        } else {
            customInput.style.display = 'none';
        }
    });

    // 系統監控模式切換
    let currentSystemMode = 'live'; // 'live' 或 'history'
    
    function switchSystemMode(mode) {
        currentSystemMode = mode;
        const liveModeBtn = document.getElementById('live-mode-btn');
        const historyModeBtn = document.getElementById('history-mode-btn');
        const liveIndicator = document.getElementById('live-indicator');
        const databaseControls = document.getElementById('database-controls');
        
        if (mode === 'live') {
            // 實時模式
            liveModeBtn.classList.add('active');
            historyModeBtn.classList.remove('active');
            liveIndicator.style.display = 'flex';
            databaseControls.style.display = 'none';
            
            // 恢復自動更新
            if (statusInterval) clearInterval(statusInterval);
            statusInterval = setInterval(loadStatus, 2000);
            
        } else {
            // 歷史模式
            historyModeBtn.classList.add('active');
            liveModeBtn.classList.remove('active');
            liveIndicator.style.display = 'none';
            databaseControls.style.display = 'flex';
            
            // 停止自動更新
            if (statusInterval) {
                clearInterval(statusInterval);
                statusInterval = null;
            }
        }
    }
    
    // 綁定模式切換按鈕
    document.getElementById('live-mode-btn').addEventListener('click', () => switchSystemMode('live'));
    document.getElementById('history-mode-btn').addEventListener('click', () => switchSystemMode('history'));

    // 設定5秒自動更新
    setInterval(() => {
        loadStatus();
        // 只有在即時進程模式才自動更新進程列表
        if (currentMode === 'monitor') {
            console.log('🔄 即時模式自動更新進程列表');
            showGpuProcesses();
        }
    }, 5000);
    
    document.getElementById('timeRange').value = '30m';
};