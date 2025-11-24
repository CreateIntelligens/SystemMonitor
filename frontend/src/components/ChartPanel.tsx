import { useState, useEffect } from 'react';
import axios from 'axios';
import { Database, Clock, BarChart3, RefreshCw, X, ChevronDown, Cpu } from 'lucide-react';
import type { DatabaseInfo, DatabasesResponse, PlotResponse, ChartInfo } from '../types';

const TIMESPANS = [
  { value: '1h', label: '1 小時' },
  { value: '6h', label: '6 小時' },
  { value: '24h', label: '24 小時' },
  { value: '7d', label: '7 天' },
  { value: '30d', label: '30 天' },
];

interface GPUItem {
  gpu_id: number;
  gpu_name: string;
}

export function ChartPanel() {
  const [databases, setDatabases] = useState<DatabaseInfo[]>([]);
  const [selectedDb, setSelectedDb] = useState<string>('');
  const [timespan, setTimespan] = useState<string>('1h');
  const [charts, setCharts] = useState<ChartInfo[]>([]);
  const [gpuChart, setGpuChart] = useState<ChartInfo | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dbDropdownOpen, setDbDropdownOpen] = useState(false);
  const [expandedChart, setExpandedChart] = useState<ChartInfo | null>(null);

  // GPU selection
  const [gpuList, setGpuList] = useState<GPUItem[]>([]);
  const [selectedGpus, setSelectedGpus] = useState<number[]>([]);
  const [gpuDropdownOpen, setGpuDropdownOpen] = useState(false);
  const [chartMode, setChartMode] = useState<'system' | 'gpu'>('system');

  // Fetch database list
  useEffect(() => {
    const fetchDatabases = async () => {
      try {
        const response = await axios.get<DatabasesResponse>('/api/databases');
        if (response.data.success) {
          setDatabases(response.data.databases);
        }
      } catch (err) {
        console.error('Failed to fetch databases:', err);
      }
    };
    fetchDatabases();
  }, []);

  // Fetch GPU list
  useEffect(() => {
    const fetchGpuList = async () => {
      try {
        const response = await axios.get<{ success: boolean; gpus: GPUItem[] }>('/api/gpu-list');
        if (response.data.success) {
          setGpuList(response.data.gpus);
          // Default: select all GPUs
          setSelectedGpus(response.data.gpus.map(g => g.gpu_id));
        }
      } catch (err) {
        console.error('Failed to fetch GPU list:', err);
      }
    };
    fetchGpuList();
  }, []);

  const generateCharts = async () => {
    setIsLoading(true);
    setError(null);
    setCharts([]);
    setGpuChart(null);

    try {
      if (chartMode === 'system') {
        const response = await axios.post<PlotResponse>(`/api/plot/${timespan}`, {
          database_file: selectedDb || undefined,
          return_base64: true,
        });

        if (response.data.success && response.data.charts) {
          setCharts(response.data.charts);
        } else {
          setError(response.data.error || '生成圖表失敗');
        }
      } else {
        // GPU mode
        const response = await axios.post<{
          success: boolean;
          chart?: ChartInfo;
          error?: string;
          gpu_count?: number;
        }>(`/api/plot/gpu/${timespan}`, {
          gpu_ids: selectedGpus.length === gpuList.length ? undefined : selectedGpus,
          database_file: selectedDb || undefined,
          return_base64: true,
        });

        if (response.data.success && response.data.chart) {
          setGpuChart(response.data.chart);
        } else {
          setError(response.data.error || '生成 GPU 圖表失敗');
        }
      }
    } catch (err: any) {
      setError(err.message || '生成圖表時發生錯誤');
    } finally {
      setIsLoading(false);
    }
  };

  const getSelectedDbDisplay = () => {
    if (!selectedDb) return '自動合併 (週週分檔)';
    const db = databases.find((d) => d.filename === selectedDb);
    return db ? db.display_name : selectedDb;
  };

  const getSelectedGpuDisplay = () => {
    if (selectedGpus.length === 0) return '未選擇';
    if (selectedGpus.length === gpuList.length) return `全部 (${gpuList.length} GPUs)`;
    return `${selectedGpus.length} / ${gpuList.length} GPUs`;
  };

  const toggleGpu = (gpuId: number) => {
    setSelectedGpus(prev =>
      prev.includes(gpuId)
        ? prev.filter(id => id !== gpuId)
        : [...prev, gpuId].sort((a, b) => a - b)
    );
  };

  const selectAllGpus = () => {
    setSelectedGpus(gpuList.map(g => g.gpu_id));
  };

  const deselectAllGpus = () => {
    setSelectedGpus([]);
  };

  return (
    <div className="bg-[#25262b] rounded-xl p-6 border border-gray-800">
      <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
        <BarChart3 className="w-5 h-5 text-blue-400" />
        歷史圖表
      </h2>

      {/* Chart Mode Toggle */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setChartMode('system')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            chartMode === 'system'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
          }`}
        >
          系統總覽
        </button>
        <button
          onClick={() => setChartMode('gpu')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 ${
            chartMode === 'gpu'
              ? 'bg-green-600 text-white'
              : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
          }`}
        >
          <Cpu className="w-4 h-4" />
          多 GPU 監控
        </button>
      </div>

      {/* Controls */}
      <div className="flex flex-wrap gap-4 mb-6">
        {/* Database Selector */}
        <div className="relative">
          <button
            onClick={() => setDbDropdownOpen(!dbDropdownOpen)}
            className="flex items-center gap-2 px-4 py-2 bg-gray-800 rounded-lg border border-gray-700 hover:border-gray-600 transition-colors min-w-[240px]"
          >
            <Database className="w-4 h-4 text-gray-400" />
            <span className="flex-1 text-left truncate">{getSelectedDbDisplay()}</span>
            <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${dbDropdownOpen ? 'rotate-180' : ''}`} />
          </button>

          {dbDropdownOpen && (
            <div className="absolute z-50 top-full left-0 mt-1 w-full bg-gray-800 border border-gray-700 rounded-lg shadow-xl max-h-64 overflow-y-auto">
              <button
                onClick={() => {
                  setSelectedDb('');
                  setDbDropdownOpen(false);
                }}
                className={`w-full px-4 py-2 text-left hover:bg-gray-700 transition-colors ${
                  selectedDb === '' ? 'bg-blue-600/20 text-blue-400' : ''
                }`}
              >
                自動合併 (週週分檔)
              </button>
              {databases.map((db) => (
                <button
                  key={db.filename}
                  onClick={() => {
                    setSelectedDb(db.filename);
                    setDbDropdownOpen(false);
                  }}
                  className={`w-full px-4 py-2 text-left hover:bg-gray-700 transition-colors flex justify-between items-center ${
                    selectedDb === db.filename ? 'bg-blue-600/20 text-blue-400' : ''
                  }`}
                >
                  <span className="flex items-center gap-2">
                    {db.display_name}
                    {db.is_current && (
                      <span className="text-xs bg-green-600/30 text-green-400 px-1.5 py-0.5 rounded">
                        目前
                      </span>
                    )}
                  </span>
                  <span className="text-xs text-gray-500">{db.size_mb} MB</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* GPU Selector (only in GPU mode) */}
        {chartMode === 'gpu' && gpuList.length > 0 && (
          <div className="relative">
            <button
              onClick={() => setGpuDropdownOpen(!gpuDropdownOpen)}
              className="flex items-center gap-2 px-4 py-2 bg-gray-800 rounded-lg border border-gray-700 hover:border-gray-600 transition-colors min-w-[180px]"
            >
              <Cpu className="w-4 h-4 text-green-400" />
              <span className="flex-1 text-left">{getSelectedGpuDisplay()}</span>
              <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${gpuDropdownOpen ? 'rotate-180' : ''}`} />
            </button>

            {gpuDropdownOpen && (
              <div className="absolute z-50 top-full left-0 mt-1 w-72 bg-gray-800 border border-gray-700 rounded-lg shadow-xl max-h-80 overflow-y-auto">
                <div className="flex gap-2 p-2 border-b border-gray-700">
                  <button
                    onClick={selectAllGpus}
                    className="flex-1 px-2 py-1 text-xs bg-green-600/20 text-green-400 rounded hover:bg-green-600/30"
                  >
                    全選
                  </button>
                  <button
                    onClick={deselectAllGpus}
                    className="flex-1 px-2 py-1 text-xs bg-gray-700 text-gray-400 rounded hover:bg-gray-600"
                  >
                    取消全選
                  </button>
                </div>
                {gpuList.map((gpu) => (
                  <button
                    key={gpu.gpu_id}
                    onClick={() => toggleGpu(gpu.gpu_id)}
                    className={`w-full px-4 py-2 text-left hover:bg-gray-700 transition-colors flex items-center gap-3 ${
                      selectedGpus.includes(gpu.gpu_id) ? 'bg-green-600/20' : ''
                    }`}
                  >
                    <div className={`w-4 h-4 rounded border ${
                      selectedGpus.includes(gpu.gpu_id)
                        ? 'bg-green-500 border-green-500'
                        : 'border-gray-500'
                    } flex items-center justify-center`}>
                      {selectedGpus.includes(gpu.gpu_id) && (
                        <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      )}
                    </div>
                    <span className="text-sm">
                      <span className="text-green-400">GPU {gpu.gpu_id}</span>
                      <span className="text-gray-500 ml-2 text-xs">{gpu.gpu_name}</span>
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Timespan Selector */}
        <div className="flex items-center gap-2 bg-gray-800 rounded-lg border border-gray-700 p-1">
          <Clock className="w-4 h-4 text-gray-400 ml-2" />
          {TIMESPANS.map((ts) => (
            <button
              key={ts.value}
              onClick={() => setTimespan(ts.value)}
              className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                timespan === ts.value
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-700'
              }`}
            >
              {ts.label}
            </button>
          ))}
        </div>

        {/* Generate Button */}
        <button
          onClick={generateCharts}
          disabled={isLoading || (chartMode === 'gpu' && selectedGpus.length === 0)}
          className="flex items-center gap-2 px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-lg font-medium transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          {isLoading ? '生成中...' : '生成圖表'}
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mb-4 p-3 bg-red-900/30 border border-red-800 rounded-lg text-red-400">
          {error}
        </div>
      )}

      {/* Charts Grid (System mode) */}
      {chartMode === 'system' && charts.length > 0 && (
        <div className="flex flex-col gap-8 items-center">
          {charts.map((chart, index) => (
            <div
              key={index}
              className="w-full max-w-4xl bg-gray-900 rounded-xl border border-gray-800 overflow-hidden cursor-pointer hover:border-blue-500/50 hover:shadow-lg hover:shadow-blue-500/10 transition-all duration-300 group"
              onClick={() => setExpandedChart(chart)}
            >
              <div className="p-4 border-b border-gray-800 flex justify-between items-center bg-gray-800/50">
                <span className="font-medium text-gray-200 flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-blue-400" />
                  {chart.title}
                </span>
                <span className="text-xs text-gray-500 group-hover:text-blue-400 transition-colors">
                  點擊放大
                </span>
              </div>
              <div className="p-4 bg-gray-900/50 flex justify-center">
                <img
                  src={chart.base64 ? `data:image/png;base64,${chart.base64}` : `/plots/${chart.path}?t=${Date.now()}`}
                  alt={chart.title}
                  className="w-full h-auto max-h-[600px] object-contain rounded-lg"
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* GPU Chart (GPU mode) */}
      {chartMode === 'gpu' && gpuChart && (
        <div className="flex justify-center">
          <div
            className="w-full max-w-5xl bg-gray-900 rounded-xl border border-gray-800 overflow-hidden cursor-pointer hover:border-green-500/50 hover:shadow-lg hover:shadow-green-500/10 transition-all duration-300 group"
            onClick={() => setExpandedChart(gpuChart)}
          >
            <div className="p-4 border-b border-gray-800 flex justify-between items-center bg-gray-800/50">
              <span className="font-medium text-gray-200 flex items-center gap-2">
                <Cpu className="w-4 h-4 text-green-400" />
                {gpuChart.title}
              </span>
              <span className="text-xs text-gray-500 group-hover:text-green-400 transition-colors">
                點擊放大
              </span>
            </div>
            <div className="p-4 bg-gray-900/50 flex justify-center">
              <img
                src={gpuChart.base64 ? `data:image/png;base64,${gpuChart.base64}` : `/plots/${gpuChart.path}?t=${Date.now()}`}
                alt={gpuChart.title}
                className="w-full h-auto max-h-[700px] object-contain rounded-lg"
              />
            </div>
          </div>
        </div>
      )}

      {/* Empty State */}
      {((chartMode === 'system' && charts.length === 0) || (chartMode === 'gpu' && !gpuChart)) && !isLoading && !error && (
        <div className="text-center py-12 text-gray-500">
          <BarChart3 className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p>
            {chartMode === 'gpu'
              ? '選擇 GPU 和時間範圍，然後點擊「生成圖表」'
              : '選擇資料庫和時間範圍，然後點擊「生成圖表」'
            }
          </p>
        </div>
      )}

      {/* Expanded Chart Modal */}
      {expandedChart && (
        <div
          className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4"
          onClick={() => setExpandedChart(null)}
        >
          <div
            className="bg-gray-900 rounded-xl max-w-6xl max-h-[90vh] overflow-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between p-4 border-b border-gray-800">
              <h3 className="text-lg font-semibold">{expandedChart.title}</h3>
              <button
                onClick={() => setExpandedChart(null)}
                className="p-1 hover:bg-gray-700 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <img
              src={expandedChart.base64 ? `data:image/png;base64,${expandedChart.base64}` : `/plots/${expandedChart.path}?t=${Date.now()}`}
              alt={expandedChart.title}
              className="w-full h-auto"
            />
          </div>
        </div>
      )}
    </div>
  );
}
