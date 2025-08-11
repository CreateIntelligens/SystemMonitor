// 全域變數
let allGpuProcesses = [];
let activeFilters = [];

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
        <div class="status-card"><h3>🎮 ${data.system_info?.gpu_name|| 'GPU'}</h3><div class="metric"><span>使用率</span><span>${data.gpu_usage?data.gpu_usage.toFixed(1)+'%':'N/A'}</span></div><div class="metric"><span>VRAM總用量</span><span title="Windows WDDM模式下無法顯示單個進程的GPU記憶體使用量">${data.vram_used_mb?Math.round(data.vram_used_mb/1024*10)/10+'GB':'N/A'} / ${data.vram_total_mb?Math.round(data.vram_total_mb/1024*10)/10+'GB':'N/A'}</span></div><div class="metric"><span>溫度</span><span>${data.gpu_temperature?data.gpu_temperature+'°C':'N/A'}</span></div></div>
        <div class="status-card"><h3>📈 資料庫</h3><div class="metric"><span>記錄數</span><span>${data.total_records?.toLocaleString()}</span></div><div class="metric"><span>大小</span><span>${data.database_size_mb?.toFixed(2)} MB</span></div><div class="metric"><span>時間範圍</span><span>${data.earliest_record?new Date(data.earliest_record).toLocaleDateString('zh-TW'):'N/A'} ~ 現在</span></div></div>
    `;
}

async function showGpuProcesses() {
    const timespanSelect = document.getElementById('process-timespan-select');
    let timespan = timespanSelect ? timespanSelect.value : 'current';
    
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
            // 載入歷史進程
            response = await fetch(`/api/all-processes/${timespan}`);
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
    const timespanSelect = document.getElementById('process-timespan-select');
    const isHistorical = timespanSelect && timespanSelect.value !== 'current';
    
    let html = `<h3>${title}${isHistorical ? ' (包含歷史進程)' : ''}</h3>`;
    if (processes.length > 0) {
        const headers = isHistorical ? 
            '<th><input type="checkbox" id="select-all-processes" onclick="toggleSelectAll(this)"></th><th>狀態</th><th>PID</th><th>進程名</th><th>指令</th><th>平均GPU記憶體</th><th>平均CPU %</th><th>平均RAM (GB)</th><th>首次記錄</th><th>最後記錄</th><th>記錄數</th>' :
            '<th><input type="checkbox" id="select-all-processes" onclick="toggleSelectAll(this)"></th><th>PID</th><th>容器來源</th><th>進程名</th><th>指令</th><th>GPU記憶體</th><th>CPU %</th><th>RAM (GB)</th><th>啟動時間</th>';
            
        html += `<table class="process-table"><thead><tr>${headers}</tr></thead><tbody>`;
        
        processes.forEach(proc => {
            let memoryDisplay = proc.gpu_memory_mb > 0 ? `${proc.gpu_memory_mb} MB` : 'N/A';
            
            if (isHistorical) {
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
            } else {
                const containerDisplay = proc.container_source || proc.container || '主機';
                html += `<tr>
                    <td><input type="checkbox" class="process-checkbox" data-pid="${proc.pid}"></td>
                    <td>${proc.pid}</td><td title="${containerDisplay}">${containerDisplay}</td><td>${proc.name}</td>
                    <td class="command-cell" title="${proc.command}">${proc.command}</td><td>${memoryDisplay}</td>
                    <td>${proc.cpu_percent}%</td><td>${(proc.ram_mb / 1024).toFixed(2)}</td><td>${proc.start_time}</td>
                </tr>`;
            }
        });
        html += '</tbody></table>';
    } else {
        html += '<p>沒有符合條件的進程。</p>';
    }
    container.innerHTML = html;
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
    } else {
        filter = { id: `${type}:${value}`, type: type, value: value, label: `${typeText}: ${value}` };
    }
    addFilter(filter);
    valueInput.value = '';
    valueInput.focus();
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
        const response = await fetch('/api/processes/plot-comparison', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pids: checkedPIDs, timespan: timespan })
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
        const response = await fetch(`/api/plot/${timespan}`, { method: 'POST' });
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
    showGpuProcesses();

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
            showGpuProcesses();
        }
    });
    
    document.getElementById('custom-database-input').addEventListener('keydown', function(event) {
        if (event.key === 'Enter') {
            showGpuProcesses();
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
            showGpuProcesses();
        }
    });
    
    document.getElementById('custom-timespan-input').addEventListener('keydown', function(event) {
        if (event.key === 'Enter') {
            showGpuProcesses();
        }
    });

    // 設定5秒自動更新
    setInterval(() => {
        loadStatus();
        // 只有在顯示當前進程時才自動更新進程列表
        const timespanSelect = document.getElementById('process-timespan-select');
        if (timespanSelect && timespanSelect.value === 'current') {
            showGpuProcesses();
        }
    }, 5000);
    
    document.getElementById('timeRange').value = '30m';
};