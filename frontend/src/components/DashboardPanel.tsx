import React, { useEffect, useState, useMemo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Activity, ChevronDown, ChevronUp, Cpu, HardDrive, Thermometer, MemoryStick, Server, Database, Globe } from 'lucide-react';
import type { SystemStatus } from '../types';

interface RealtimeData {
  timestamp: string;
  cpu_usage: number;
  ram_usage: number;
  gpu_list: Array<{
    gpu_id: number;
    gpu_usage: number;
    vram_usage: number;
    temperature: number;
  }>;
}

interface ChartDataPoint {
  time: string;
  index: number;
  [key: string]: number | string;
}

const GPU_COLORS = [
  { main: '#8B5CF6', light: '#A78BFA' },
  { main: '#10B981', light: '#34D399' },
  { main: '#F59E0B', light: '#FBBF24' },
  { main: '#EF4444', light: '#F87171' },
  { main: '#3B82F6', light: '#60A5FA' },
  { main: '#EC4899', light: '#F472B6' },
  { main: '#14B8A6', light: '#2DD4BF' },
  { main: '#F97316', light: '#FB923C' },
];

interface DashboardPanelProps {
  status?: SystemStatus;
}

const DashboardPanel: React.FC<DashboardPanelProps> = ({ status }) => {
  const [data, setData] = useState<ChartDataPoint[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [gpuCount, setGpuCount] = useState(0);
  const [isGpuExpanded, setIsGpuExpanded] = useState(false);
  const [latestGpuData, setLatestGpuData] = useState<RealtimeData['gpu_list']>([]);
  const [latestCpu, setLatestCpu] = useState(0);
  const [latestRam, setLatestRam] = useState(0);
  const [dataIndex, setDataIndex] = useState(0);

  // 10 分鐘 = 600 秒
  const maxDataPoints = 600;

  // 為圖表準備固定長度的數據（補空值）
  const chartData = useMemo(() => {
    if (data.length === 0) {
      return Array.from({ length: maxDataPoints }, (_, i) => ({
        time: '',
        index: i,
      }));
    }

    const paddedData: ChartDataPoint[] = [];
    const emptyCount = maxDataPoints - data.length;

    for (let i = 0; i < emptyCount; i++) {
      paddedData.push({ time: '', index: i });
    }

    data.forEach((point, i) => {
      paddedData.push({ ...point, index: emptyCount + i });
    });

    return paddedData;
  }, [data, maxDataPoints]);

  useEffect(() => {
    const eventSource = new EventSource('/api/stream/status');

    eventSource.onopen = () => {
      setIsConnected(true);
    };

    eventSource.onmessage = (event) => {
      try {
        const parsedData: RealtimeData = JSON.parse(event.data);
        const timestamp = new Date(parsedData.timestamp).toLocaleTimeString('zh-TW', {
          hour12: false,
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit'
        });

        setLatestCpu(parsedData.cpu_usage || 0);
        setLatestRam(parsedData.ram_usage || 0);

        setDataIndex(prev => prev + 1);

        const newPoint: ChartDataPoint = {
          time: timestamp,
          index: dataIndex,
          cpu: parsedData.cpu_usage || 0,
          ram: parsedData.ram_usage || 0,
        };

        if (parsedData.gpu_list && parsedData.gpu_list.length > 0) {
          setGpuCount(parsedData.gpu_list.length);
          setLatestGpuData(parsedData.gpu_list);

          parsedData.gpu_list.forEach((gpu) => {
            newPoint[`gpu${gpu.gpu_id}`] = gpu.gpu_usage || 0;
            newPoint[`vram${gpu.gpu_id}`] = gpu.vram_usage || 0;
          });
        }

        setData((prevData) => {
          const newData = [...prevData, newPoint];
          return newData.length > maxDataPoints
            ? newData.slice(newData.length - maxDataPoints)
            : newData;
        });
      } catch (error) {
        console.error('Error parsing SSE data:', error);
      }
    };

    eventSource.onerror = () => {
      setIsConnected(false);
      eventSource.close();
      setTimeout(() => {
        window.location.reload();
      }, 5000);
    };

    return () => {
      eventSource.close();
    };
  }, []);

  // 格式化時間軸標籤
  const timeTicks = useMemo(() => {
    const validPoints = chartData.filter((point) => point.time);
    if (validPoints.length === 0) {
      return [];
    }

    const maxTicks = 6;
    const step = Math.max(1, Math.floor(validPoints.length / Math.max(1, maxTicks - 1)));
    const ticks: number[] = [];

    for (let i = 0; i < validPoints.length; i += step) {
      ticks.push(validPoints[i].index);
    }

    const lastIndex = validPoints[validPoints.length - 1].index;
    if (!ticks.includes(lastIndex)) {
      ticks.push(lastIndex);
    }

    return ticks;
  }, [chartData]);

  const formatXAxis = (value: number) => {
    const point = chartData.find((p) => p.index === value);
    return point?.time || '';
  };

  const cpuSource = status?.cpu_source || 'N/A';
  const cpuPercent = status?.cpu_usage ?? latestCpu;
  const ramTotalGb = status?.ram_total_gb ?? 0;
  const ramUsedGb = status?.ram_used_gb ?? 0;
  const ramPercent = status?.ram_usage ?? latestRam;

  // GPU 卡片組件
  const GpuCard = ({ gpuId, color }: { gpuId: number; color: typeof GPU_COLORS[0] }) => {
    const gpu = latestGpuData.find(g => g.gpu_id === gpuId);
    const usage = gpu?.gpu_usage || 0;
    const vram = gpu?.vram_usage || 0;
    const temp = gpu?.temperature || 0;

    return (
      <div className="bg-gray-900/60 rounded-xl p-4 border border-gray-700/50">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color.main }} />
            <span className="font-medium text-gray-200">GPU {gpuId}</span>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <div className="flex items-center gap-1">
              <Cpu className="w-3 h-3 text-gray-500" />
              <span style={{ color: color.main }}>{usage.toFixed(1)}%</span>
            </div>
            <div className="flex items-center gap-1">
              <HardDrive className="w-3 h-3 text-gray-500" />
              <span style={{ color: color.light }}>{vram.toFixed(1)}%</span>
            </div>
            <div className="flex items-center gap-1">
              <Thermometer className="w-3 h-3 text-gray-500" />
              <span className={temp > 80 ? 'text-red-400' : temp > 60 ? 'text-yellow-400' : 'text-green-400'}>
                {temp}°C
              </span>
            </div>
          </div>
        </div>

        <div className="space-y-2 mb-3">
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500 w-12">Usage</span>
            <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-300"
                style={{ width: `${usage}%`, backgroundColor: color.main }}
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500 w-12">VRAM</span>
            <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-300"
                style={{ width: `${vram}%`, backgroundColor: color.light }}
              />
            </div>
          </div>
        </div>

        <div style={{ width: '100%', height: 80, minWidth: 0 }}>
          <ResponsiveContainer width="100%" height={80}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
              <XAxis dataKey="index" type="number" domain={[0, maxDataPoints - 1]} hide />
              <YAxis domain={[0, 100]} hide />
              <Tooltip
                contentStyle={{ backgroundColor: '#1F2937', borderRadius: '8px', border: '1px solid #374151', fontSize: '11px' }}
                labelStyle={{ color: '#9CA3AF' }}
                labelFormatter={(value) => {
                  const point = chartData.find(p => p.index === value);
                  return point?.time || '';
                }}
              />
              <Line type="monotone" dataKey={`gpu${gpuId}`} stroke={color.main} strokeWidth={1.5} dot={false} isAnimationActive={false} connectNulls={false} />
              <Line type="monotone" dataKey={`vram${gpuId}`} stroke={color.light} strokeWidth={1.5} strokeDasharray="3 3" dot={false} isAnimationActive={false} connectNulls={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    );
  };

  // 進度條組件
  const ProgressBar = ({ value, color, label }: { value: number; color: string; label?: string }) => (
    <div className="space-y-1">
      {label && <div className="text-xs text-gray-500">{label}</div>}
      <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-300"
          style={{ width: `${Math.min(value, 100)}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );

  // 資訊行組件
  const InfoRow = ({ icon: Icon, label, value, subValue, iconColor = 'text-gray-400' }: {
    icon: React.ElementType;
    label: string;
    value: string | number;
    subValue?: string;
    iconColor?: string;
  }) => (
    <div className="flex items-start gap-3 py-3 border-b border-gray-700/50 last:border-0">
      <Icon className={`w-4 h-4 mt-0.5 ${iconColor}`} />
      <div className="flex-1 min-w-0">
        <div className="text-xs text-gray-500 mb-0.5">{label}</div>
        <div className="text-sm font-medium text-gray-200 truncate">{value}</div>
        {subValue && <div className="text-xs text-gray-500">{subValue}</div>}
      </div>
    </div>
  );

  if (!status) {
    return (
      <div className="bg-gray-800/80 backdrop-blur-md p-6 rounded-2xl border border-gray-700 shadow-lg">
        <div className="flex items-center justify-center py-10">
          <div className="animate-pulse text-gray-400">Loading system status...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-800/80 backdrop-blur-md p-6 rounded-2xl border border-gray-700 shadow-lg mb-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="w-6 h-6 text-green-400" />
          <h2 className="text-xl font-bold text-gray-100">系統儀表板</h2>
          <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
        </div>
        <span className="text-xs text-gray-500">
          {Math.floor(data.length / 60)}:{(data.length % 60).toString().padStart(2, '0')} / 10:00
        </span>
      </div>

      {/* Main Layout: 左側系統資訊 + 右側即時圖表 */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* 左側：系統資訊面板 */}
        <div className="lg:col-span-4 xl:col-span-3 space-y-4">
          {/* 系統概覽卡片 */}
          <div className="bg-gray-900/60 rounded-xl p-4 border border-gray-700/50">
            <div className="flex items-center gap-2 mb-3">
              <Server className="w-4 h-4 text-blue-400" />
              <span className="text-sm font-medium text-gray-300">系統資訊</span>
            </div>
            
            <InfoRow
              icon={Globe}
              label="Hostname"
              value={status.system_info.hostname || 'N/A'}
              subValue={status.system_info.local_ip || '--'}
              iconColor="text-emerald-400"
            />
            
            <InfoRow
              icon={Server}
              label="Platform"
              value={status.system_info.platform || 'Unknown'}
              subValue={`${status.system_info.cpu_count} cores`}
              iconColor="text-purple-400"
            />
          </div>

          {/* CPU 卡片 */}
          <div className="bg-gray-900/60 rounded-xl p-4 border border-gray-700/50">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Cpu className="w-4 h-4 text-red-400" />
                <span className="text-sm font-medium text-gray-300">CPU</span>
              </div>
              <span className="text-lg font-bold text-red-400">{cpuPercent.toFixed(1)}%</span>
            </div>
            <div className="text-xs text-gray-500 mb-2">來源: {cpuSource}</div>
            <ProgressBar value={cpuPercent} color="#EF4444" />
          </div>

          {/* Memory 卡片 */}
          <div className="bg-gray-900/60 rounded-xl p-4 border border-gray-700/50">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <MemoryStick className="w-4 h-4 text-cyan-400" />
                <span className="text-sm font-medium text-gray-300">Memory</span>
              </div>
              <span className="text-lg font-bold text-cyan-400">{ramPercent.toFixed(1)}%</span>
            </div>
            <div className="text-xs text-gray-500 mb-2">
              {ramUsedGb.toFixed(1)} / {ramTotalGb.toFixed(1)} GB
            </div>
            <ProgressBar value={ramPercent} color="#06B6D4" />
          </div>

          {/* Database 卡片 */}
          <div className="bg-gray-900/60 rounded-xl p-4 border border-gray-700/50">
            <div className="flex items-center gap-2 mb-3">
              <Database className="w-4 h-4 text-yellow-400" />
              <span className="text-sm font-medium text-gray-300">資料庫</span>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">Records</span>
                <span className="text-gray-200 font-medium">{status.total_records.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Size</span>
                <span className="text-gray-200 font-medium">{status.database_size_mb.toFixed(2)} MB</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Range</span>
                <span className="text-gray-200 font-medium">
                  {status.earliest_record 
                    ? new Date(status.earliest_record).toLocaleDateString('zh-TW', { month: '2-digit', day: '2-digit' }) + ' ~ Now'
                    : 'N/A'
                  }
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* 右側：即時圖表區域 */}
        <div className="lg:col-span-8 xl:col-span-9 space-y-4">
          {/* CPU/RAM 趨勢圖 */}
          <div className="bg-gray-900/60 rounded-xl p-4 border border-gray-700/50">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-4 text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-red-500" />
                  <span className="text-gray-400">CPU</span>
                  <span className="font-medium text-red-400">{cpuPercent.toFixed(1)}%</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-cyan-500" />
                  <span className="text-gray-400">RAM</span>
                  <span className="font-medium text-cyan-400">{ramPercent.toFixed(1)}%</span>
                </div>
              </div>
              <span className="text-xs text-gray-500">
                {ramUsedGb.toFixed(1)} / {ramTotalGb.toFixed(1)} GB
              </span>
            </div>
            
            <div style={{ width: '100%', height: 200, minWidth: 0 }}>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={chartData}>
                  <CartesianGrid stroke="#374151" strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="index"
                    type="number"
                    domain={[0, maxDataPoints - 1]}
                    ticks={timeTicks}
                    tickFormatter={formatXAxis}
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: 'rgba(255, 255, 255, 0.55)', fontSize: 11 }}
                    interval={0}
                  />
                  <YAxis 
                    domain={[0, 100]} 
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: 'rgba(255, 255, 255, 0.55)', fontSize: 11 }}
                    tickFormatter={(v) => `${v}%`}
                    width={40}
                  />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1F2937', borderRadius: '8px', border: '1px solid #374151', fontSize: '12px' }}
                    labelStyle={{ color: '#9CA3AF' }}
                    labelFormatter={(value) => {
                      const point = chartData.find(p => p.index === value);
                      return point?.time || '';
                    }}
                    formatter={(value: number, name: string) => [
                      `${value.toFixed(1)}%`,
                      name === 'cpu' ? 'CPU' : 'RAM'
                    ]}
                  />
                  <Line type="monotone" dataKey="cpu" stroke="#EF4444" strokeWidth={2} dot={false} isAnimationActive={false} connectNulls={false} name="cpu" />
                  <Line type="monotone" dataKey="ram" stroke="#06B6D4" strokeWidth={2} dot={false} isAnimationActive={false} connectNulls={false} name="ram" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* GPU 區塊 */}
          {gpuCount > 0 && (
            <>
              <button
                onClick={() => setIsGpuExpanded(!isGpuExpanded)}
                className="w-full flex items-center justify-between py-3 px-4 bg-gray-900/60 rounded-xl border border-gray-700/50 hover:bg-gray-900/80 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2">
                    <HardDrive className="w-4 h-4 text-purple-400" />
                    <span className="text-sm font-medium text-gray-300">{gpuCount} GPUs</span>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-gray-500">
                    <span>
                      Avg Usage: {(latestGpuData.reduce((a, g) => a + (g.gpu_usage || 0), 0) / gpuCount).toFixed(1)}%
                    </span>
                    <span>
                      Avg VRAM: {(latestGpuData.reduce((a, g) => a + (g.vram_usage || 0), 0) / gpuCount).toFixed(1)}%
                    </span>
                    <span>
                      Avg Temp: {(latestGpuData.reduce((a, g) => a + (g.temperature || 0), 0) / gpuCount).toFixed(0)}°C
                    </span>
                  </div>
                </div>
                {isGpuExpanded ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
              </button>

              {isGpuExpanded && (
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
                  {Array.from({ length: gpuCount }).map((_, i) => (
                    <GpuCard key={i} gpuId={i} color={GPU_COLORS[i % GPU_COLORS.length]} />
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default DashboardPanel;
