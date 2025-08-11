// 載入狀態
async function loadStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        updateStatusDisplay(data);
    } catch (error) {
        document.getElementById('statusGrid').innerHTML = '<div class="status-card"><h3>❌ 載入失敗</h3><p>無法獲取系統狀態</p></div>';
    }
}

// 更新狀態顯示
function updateStatusDisplay(data) {
    // 更新主機資訊
    if (data.system_info) {
        const hostInfo = `${data.system_info.hostname || '未知主機'}`;
        const ipInfo = data.system_info.local_ip ? ` (${data.system_info.local_ip})` : '';
        document.getElementById('hostname').textContent = hostInfo + ipInfo;
    }
    
    // 更新狀態卡片
    const grid = document.getElementById('statusGrid');
    grid.innerHTML = `
        <div class="status-card">
            <h3>🖥️ CPU (${data.system_info?.cpu_count || 'N/A'}核心)</h3>
            <div class="metric"><span>使用率</span><span>${data.cpu_usage?.toFixed(1)}%</span></div>
            <div class="metric"><span>來源</span><span>${data.cpu_source}</span></div>
        </div>
        <div class="status-card">
            <h3>💾 記憶體 (${data.ram_total_gb?.toFixed(1)}GB)</h3>
            <div class="metric"><span>已使用</span><span>${data.ram_used_gb?.toFixed(1)}GB / ${data.ram_total_gb?.toFixed(1)}GB</span></div>
            <div class="metric"><span>使用率</span><span>${data.ram_usage?.toFixed(1)}%</span></div>
            <div class="metric"><span>來源</span><span>${data.ram_source}</span></div>
        </div>
        <div class="status-card">
            <h3>🎮 ${data.system_info?.gpu_name || 'GPU'}</h3>
            <div class="metric"><span>使用率</span><span>${data.gpu_usage ? data.gpu_usage.toFixed(1) + '%' : 'N/A'}</span></div>
            <div class="metric"><span>VRAM總用量</span><span title="Windows WDDM模式下無法顯示單個進程的GPU記憶體使用量">${data.vram_used_mb ? Math.round(data.vram_used_mb/1024*10)/10 + 'GB' : 'N/A'} / ${data.vram_total_mb ? Math.round(data.vram_total_mb/1024*10)/10 + 'GB' : 'N/A'}</span></div>
            <div class="metric"><span>溫度</span><span>${data.gpu_temperature ? data.gpu_temperature + '°C' : 'N/A'}</span></div>
        </div>
        <div class="status-card">
            <h3>📈 資料庫</h3>
            <div class="metric"><span>記錄數</span><span>${data.total_records?.toLocaleString()}</span></div>
            <div class="metric"><span>大小</span><span>${data.database_size_mb?.toFixed(2)} MB</span></div>
            <div class="metric"><span>時間範圍</span><span>${data.earliest_record ? new Date(data.earliest_record).toLocaleDateString() : 'N/A'}</span></div>
        </div>
    `;
}

// 下拉選單功能
function showDropdown() {
    document.getElementById('timeDropdown').style.display = 'block';
}

function hideDropdown() {
    setTimeout(() => {
        document.getElementById('timeDropdown').style.display = 'none';
    }, 150);
}

function selectTime(value) {
    document.getElementById('timeRange').value = value;
    document.getElementById('timeDropdown').style.display = 'none';
}

function filterDropdown() {
    const input = document.getElementById('timeRange').value.toLowerCase();
    const dropdown = document.getElementById('timeDropdown');
    const items = dropdown.getElementsByClassName('dropdown-item');
    
    for (let item of items) {
        const text = item.textContent.toLowerCase();
        item.style.display = text.includes(input) ? 'block' : 'none';
    }
}

// 生成選定時間範圍的圖表
function generateSelectedChart() {
    const timeRange = document.getElementById('timeRange').value.trim();
    if (!timeRange) {
        alert('請選擇時間範圍');
        return;
    }
    generateChart(timeRange);
}

// 生成圖表
async function generateChart(timespan) {
    const loading = document.getElementById('loading');
    const chartsGrid = document.getElementById('chartsGrid');
    
    loading.style.display = 'block';
    chartsGrid.innerHTML = '';
    
    try {
        const response = await fetch(`/api/plot/${timespan}`, { method: 'POST' });
        const result = await response.json();
        
        if (result.success) {
            displayCharts(result.charts);
        } else {
            alert('圖表生成失敗: ' + result.error);
        }
    } catch (error) {
        alert('生成圖表時發生錯誤');
    } finally {
        loading.style.display = 'none';
    }
}

// 顯示圖表
function displayCharts(charts) {
    const grid = document.getElementById('chartsGrid');
    grid.innerHTML = charts.map(chart => `
        <div class="chart-card">
            <h4>${chart.title}</h4>
            <img src="/plots/${chart.path}" alt="${chart.title}" onclick="window.open('/plots/${chart.path}', '_blank')">
        </div>
    `).join('');
}

// 顯示GPU進程
async function showGpuProcesses() {
    try {
        const response = await fetch('/api/gpu-processes');
        const data = await response.json();
        const container = document.getElementById('gpuProcessesContainer');

        if (data.current && data.current.length > 0) {
            // Windows WDDM 模式說明
            const isWindowsWDDM = data.current.some(proc => proc.gpu_memory_mb === 0 && (proc.type?.includes('NVIDIA') || proc.type?.includes('GPU')));
            const wddmInfo = isWindowsWDDM ? 
                `<div style="background: rgba(255, 193, 7, 0.1); border-left: 4px solid #ffc107; padding: 10px; margin-bottom: 15px; border-radius: 4px;">
                    <strong>📝 注意：</strong> Windows WDDM 模式下無法顯示單個進程的 GPU 記憶體使用量，只能顯示總使用量。
                </div>` : '';
            
            let html = '<h3>🎮 當前GPU進程</h3>' + wddmInfo + '<table class="process-table"><thead><tr><th>PID</th><th>容器來源</th><th>進程名</th><th>指令</th><th>GPU記憶體</th><th>CPU %</th><th>RAM (MB)</th><th>啟動時間</th></tr></thead><tbody>';
            
            data.current.forEach(proc => {
                // GPU記憶體顯示邏輯
                let memoryDisplay;
                if (proc.gpu_memory_mb > 0) {
                    memoryDisplay = `${proc.gpu_memory_mb} MB`;
                } else if (proc.type && (proc.type.includes('NVIDIA') || proc.type.includes('GPU'))) {
                    // NVIDIA GPU進程，但Windows WDDM無法顯示個別進程記憶體
                    memoryDisplay = '<span title="Windows WDDM模式無法顯示個別進程 GPU 記憶體">共享GPU</span>';
                } else if (proc.type && proc.type.includes('Keyword')) {
                    // 關鍵字識別的潛在GPU進程
                    memoryDisplay = '<span title="通過關鍵字識別的潛在GPU進程">潛在GPU</span>';
                } else {
                    memoryDisplay = 'N/A';
                }
                
                // 容器來源顯示
                const containerSource = proc.container_source || proc.container || '主機';
                const containerDisplay = containerSource === '主機' ? '主機' : containerSource;
                
                html += `<tr>
                    <td>${proc.pid}</td>
                    <td style="max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${containerDisplay}">${containerDisplay}</td>
                    <td>${proc.name}</td>
                    <td class="command-cell">${proc.command}</td>
                    <td>${memoryDisplay}</td>
                    <td>${proc.cpu_percent}%</td>
                    <td>${proc.ram_mb}</td>
                    <td>${proc.start_time}</td>
                </tr>`;
            });
            html += '</tbody></table>';
            container.innerHTML = html;
        } else {
            container.innerHTML = '<h3>當前GPU進程</h3><p>目前沒有GPU進程在運行。</p>';
        }
    } catch (error) {
        const container = document.getElementById('gpuProcessesContainer');
        container.innerHTML = '<h3>當前GPU進程</h3><p>獲取GPU進程資訊失敗。</p>';
    }
}

// 頁面載入時自動載入狀態
window.onload = function() {
    loadStatus();
    showGpuProcesses(); // 初始載入 GPU 進程
    // 每5秒自動更新一次狀態，實現實時監控
    setInterval(() => {
        loadStatus();
        showGpuProcesses();
    }, 5000);
    
    // 預設選擇 30 分鐘
    document.getElementById('timeRange').value = '30m';
};