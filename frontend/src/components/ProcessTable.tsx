import React, { useState, useMemo } from 'react';
import { Search, Filter, RefreshCw, X } from 'lucide-react';
import type { ProcessInfo } from '../types';

interface ProcessTableProps {
  processes: ProcessInfo[];
  isLoading: boolean;
  onRefresh: () => void;
  mode: 'monitor' | 'stats' | 'charts';
  lastUpdated?: Date;
}

type FilterType = 'search' | 'pid' | 'name' | 'cmd' | 'ram_gt' | 'gpu_gt';

interface ActiveFilter {
  id: string;
  type: FilterType;
  value: string | number;
  label: string;
}

export const ProcessTable: React.FC<ProcessTableProps> = ({
  processes,
  isLoading,
  onRefresh,
  mode,
  lastUpdated
}) => {
  const [filters, setFilters] = useState<ActiveFilter[]>([]);
  const [filterType, setFilterType] = useState<FilterType>('search');
  const [filterValue, setFilterValue] = useState('');
  const [selectedPids, setSelectedPids] = useState<Set<number>>(new Set());
  const [isGeneratingChart, setIsGeneratingChart] = useState(false);
  const [chartPath, setChartPath] = useState<string | null>(null);

  const addFilter = () => {
    if (!filterValue.trim()) return;

    const newFilter: ActiveFilter = {
      id: Date.now().toString(),
      type: filterType,
      value: filterType === 'ram_gt' || filterType === 'gpu_gt' ? Number(filterValue) : filterValue,
      label: `${getFilterLabel(filterType)}: ${filterValue}`
    };

    setFilters([...filters, newFilter]);
    setFilterValue('');
  };

  const removeFilter = (id: string) => {
    setFilters(filters.filter(f => f.id !== id));
  };

  const getFilterLabel = (type: FilterType) => {
    switch (type) {
      case 'search': return '搜尋';
      case 'pid': return 'PID';
      case 'name': return '進程名';
      case 'cmd': return '指令';
      case 'ram_gt': return 'RAM > (MB)';
      case 'gpu_gt': return 'GPU > (MB)';
      default: return type;
    }
  };

  const filteredProcesses = useMemo(() => {
    return processes.filter(proc => {
      return filters.every(filter => {
        switch (filter.type) {
          case 'search':
            const term = String(filter.value).toLowerCase();
            return (
              String(proc.pid).includes(term) ||
              proc.name.toLowerCase().includes(term) ||
              proc.command.toLowerCase().includes(term)
            );
          case 'pid':
            return String(proc.pid).includes(String(filter.value));
          case 'name':
            return proc.name.toLowerCase().includes(String(filter.value).toLowerCase());
          case 'cmd':
            return proc.command.toLowerCase().includes(String(filter.value).toLowerCase());
          case 'ram_gt':
            return (proc.ram_mb || 0) > Number(filter.value);
          case 'gpu_gt':
            return proc.gpu_memory_mb > Number(filter.value);
          default:
            return true;
        }
      });
    });
  }, [processes, filters]);

  const togglePidSelection = (pid: number) => {
    const newSelection = new Set(selectedPids);
    if (newSelection.has(pid)) {
      newSelection.delete(pid);
    } else {
      newSelection.add(pid);
    }
    setSelectedPids(newSelection);
  };

  const generateChart = async () => {
    if (selectedPids.size === 0) return;

    setIsGeneratingChart(true);
    try {
      const response = await fetch('/api/processes/plot-comparison', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pids: Array.from(selectedPids),
          timespan: '24h',
          database_file: 'monitoring.db'
        })
      });

      const data = await response.json();
      if (data.success && data.chart) {
        setChartPath(data.chart.path);
      } else {
        alert(data.error || '生成圖表失敗');
      }
    } catch (error) {
      console.error('Failed to generate chart:', error);
      alert('生成圖表時發生錯誤');
    } finally {
      setIsGeneratingChart(false);
    }
  };

  return (
    <div className="bg-gray-800/80 backdrop-blur-md rounded-2xl border border-gray-700 shadow-lg overflow-hidden">
      <div className="p-6 border-b border-gray-700">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
          <div>
            <h3 className="text-xl font-semibold text-gray-100 flex items-center gap-2">
              <Search className="w-5 h-5 text-blue-400" />
              進程分析
              {mode === 'monitor' && (
                <span className="text-xs font-normal text-gray-400 ml-2 bg-gray-700 px-2 py-1 rounded-full">
                  即時更新中
                </span>
              )}
            </h3>
            {lastUpdated && (
              <p className="text-sm text-gray-500 mt-1">
                最後更新: {lastUpdated.toLocaleTimeString()}
              </p>
            )}
          </div>
          
          <div className="flex items-center gap-2">
            {mode === 'stats' && selectedPids.size > 0 && (
              <button
                onClick={generateChart}
                disabled={isGeneratingChart}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white rounded-lg transition-colors flex items-center gap-2"
              >
                {isGeneratingChart ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    生成中...
                  </>
                ) : (
                  <>
                    📊 生成圖表 ({selectedPids.size})
                  </>
                )}
              </button>
            )}
            <button
              onClick={onRefresh}
              disabled={isLoading}
              className="p-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-5 h-5 text-gray-300 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap gap-2">
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value as FilterType)}
              className="bg-gray-700 border border-gray-600 text-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="search">全文搜尋</option>
              <option value="name">進程名</option>
              <option value="pid">PID</option>
              <option value="cmd">指令</option>
              <option value="ram_gt">RAM {'>'} (MB)</option>
              <option value="gpu_gt">GPU {'>'} (MB)</option>
            </select>
            
            <div className="flex-1 flex gap-2">
              <input
                type="text"
                value={filterValue}
                onChange={(e) => setFilterValue(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && addFilter()}
                placeholder="輸入關鍵字..."
                className="flex-1 bg-gray-700 border border-gray-600 text-gray-200 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={addFilter}
                className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
              >
                <Filter className="w-4 h-4" />
                新增
              </button>
            </div>
          </div>

          {filters.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {filters.map(filter => (
                <span 
                  key={filter.id} 
                  className="bg-blue-500/20 text-blue-300 border border-blue-500/30 px-3 py-1 rounded-full text-sm flex items-center gap-2"
                >
                  {filter.label}
                  <button 
                    onClick={() => removeFilter(filter.id)}
                    className="hover:text-white transition-colors"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-700/50 text-gray-400 text-sm uppercase tracking-wider">
              {mode === 'stats' && <th className="p-4 font-medium w-12">選擇</th>}
              <th className="p-4 font-medium">PID</th>
              <th className="p-4 font-medium">process name</th>
              <th className="p-4 font-medium">command</th>
              <th className="p-4 font-medium">vRAM (MB)</th>
              <th className="p-4 font-medium">CPU %</th>
              <th className="p-4 font-medium">RAM (MB)</th>
              <th className="p-4 font-medium">Start time</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700/50">
            {filteredProcesses.length > 0 ? (
              filteredProcesses.map((proc) => (
                <tr key={`${proc.pid}-${proc.start_time}`} className="hover:bg-gray-700/30 transition-colors text-gray-300">
                  {mode === 'stats' && (
                    <td className="p-4">
                      <input
                        type="checkbox"
                        checked={selectedPids.has(proc.pid)}
                        onChange={() => togglePidSelection(proc.pid)}
                        className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-blue-600 focus:ring-2 focus:ring-blue-500 cursor-pointer"
                      />
                    </td>
                  )}
                  <td className="p-4 font-mono text-sm text-gray-400">{proc.pid}</td>
                  <td className="p-4 font-medium text-white">{proc.name}</td>
                  <td className="p-4 text-sm text-gray-400 max-w-xs truncate" title={proc.command}>
                    {proc.command}
                  </td>
                  <td className="p-4 font-mono text-emerald-400">
                    {proc.gpu_memory_mb > 0 ? proc.gpu_memory_mb : '-'}
                  </td>
                  <td className="p-4 font-mono">{proc.cpu_percent}</td>
                  <td className="p-4 font-mono">
                    {proc.ram_mb !== undefined ? proc.ram_mb.toFixed(1) : '-'}
                  </td>
                  <td className="p-4 text-sm text-gray-500 whitespace-nowrap">
                    {new Date(proc.start_time).toLocaleString('zh-TW', {
                      year: 'numeric',
                      month: '2-digit',
                      day: '2-digit',
                      hour: '2-digit',
                      minute: '2-digit',
                      second: '2-digit',
                      hour12: false
                    })}
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={mode === 'stats' ? 8 : 7} className="p-8 text-center text-gray-500">
                  沒有找到符合條件的進程
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* 顯示生成的圖表 */}
      {chartPath && (
        <div className="mt-6 p-4 bg-gray-900 rounded-lg border border-gray-700">
          <div className="flex justify-between items-center mb-4">
            <h4 className="text-lg font-semibold text-gray-100">進程對比圖表</h4>
            <button
              onClick={() => setChartPath(null)}
              className="text-gray-400 hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          <img
            src={`/plots/${chartPath}?t=${Date.now()}`}
            alt="進程對比圖表"
            className="w-full h-auto rounded-lg"
          />
        </div>
      )}
    </div>
  );
};
