
// 全域變數
let allGpuProcesses = [];
let activeFilters = [];

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
        <div class="status-card"><h3>📈 資料庫</h3><div class="metric"><span>記錄數</span><span>${data.total_records?.toLocaleString()}</span></div><div class="metric"><span>大小</span><span>${data.database_size_mb?.toFixed(2)} MB</span></div><div class="metric"><span>時間範圍</span><span>${data.earliest_record?new Date(data.earliest_record).toLocaleDateString():'N/A'}</span></div></div>
    `;
}

// **簡化後**：只獲取數據，由 applyFilters 渲染
async function showGpuProcesses() {
    try {
        const response = await fetch('/api/gpu-processes');
        const data = await response.json();
        allGpuProcesses = data.current || [];
        applyFilters(); // 應用當前篩選並渲染唯一的列表
    } catch (error) {
        console.error('獲取GPU進程失敗:', error);
        document.getElementById('filteredProcessList').innerHTML = '<h3>進程列表</h3><p>獲取GPU進程資訊失敗。</p>';
    }
}

function renderProcessTable(processes, containerId, title) {
    const container = document.getElementById(containerId);
    if (!container) return;
    let html = `<h3>${title}</h3>`;
    if (processes.length > 0) {
        html += '<table class="process-table"><thead><tr><th><input type="checkbox" id="select-all-processes" onclick="toggleSelectAll(this)"></th><th>PID</th><th>容器來源</th><th>進程名</th><th>指令</th><th>GPU記憶體</th><th>CPU %</th><th>RAM (GB)</th><th>啟動時間</th></tr></thead><tbody>';
        processes.forEach(proc => {
            let memoryDisplay = proc.gpu_memory_mb > 0 ? `${proc.gpu_memory_mb} MB` : 'N/A';
            const containerDisplay = proc.container_source || proc.container || '主機';
            html += `<tr>
                <td><input type="checkbox" class="process-checkbox" data-pid="${proc.pid}"></td>
                <td>${proc.pid}</td><td title="${containerDisplay}">${containerDisplay}</td><td>${proc.name}</td>
                <td class="command-cell" title="${proc.command}">${proc.command}</td><td>${memoryDisplay}</td>
                <td>${proc.cpu_percent}%</td><td>${(proc.ram_mb / 1024).toFixed(2)}</td><td>${proc.start_time}</td>
            </tr>`;
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
                             .map(cb => cb.getAttribute('data-pid'));
    if (checkedPIDs.length === 0) {
        alert('請至少選擇一個進程來繪圖。');
        return;
    }
    const chartContainer = document.getElementById('process-chart-container');
    chartContainer.innerHTML = `<div class="loading"><h3>⏳ 正在生成進程圖表...</h3></div>`;
    try {
        const response = await fetch('/api/plot/processes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pids: checkedPIDs, timespan: '1h' })
        });
        const result = await response.json();
        if (result.success) {
            chartContainer.innerHTML = `
                <div class="chart-card">
                    <h4>${result.chart.title}</h4>
                    <img src="/plots/${result.chart.path}" alt="${result.chart.title}" onclick="window.open('/plots/${result.chart.path}', '_blank')">
                </div>`;
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
    loadStatus();
    showGpuProcesses();

    document.getElementById('add-filter-btn').addEventListener('click', createFilterFromUI);
    document.getElementById('filter-value-input').addEventListener('keydown', (event) => {
        if (event.key === 'Enter') createFilterFromUI();
    });
    document.getElementById('plot-selected-btn').addEventListener('click', plotSelectedProcesses);

    setInterval(() => {
        loadStatus();
        showGpuProcesses();
    }, 5000);
    
    document.getElementById('timeRange').value = '30m';
};
