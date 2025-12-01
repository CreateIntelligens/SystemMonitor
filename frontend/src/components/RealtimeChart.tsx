import React, { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Activity, Cpu, MemoryStick } from 'lucide-react';
import type { SystemStatus } from '../types';

interface RealtimeData {
  timestamp: string;
  cpu_usage: number;
  ram_usage: number;
  ram_used_gb?: number;
  ram_total_gb?: number;
  gpu_list: Array<{
    gpu_id: number;
    gpu_name?: string;
    gpu_usage: number;
    vram_usage: number;
    vram_used_mb?: number;
    vram_total_mb?: number;
    temperature: number;
    power_draw?: number;
    power_limit?: number;
    fan_speed?: number;
    clock_graphics?: number;
    clock_memory?: number;
    clock_sm?: number;
    pcie_gen?: number;
    pcie_width?: number;
    performance_state?: string;
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

interface RealtimeChartProps {
  status?: SystemStatus;
}

const RealtimeChart: React.FC<RealtimeChartProps> = ({ status }) => {
  const [data, setData] = useState<ChartDataPoint[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [gpuCount, setGpuCount] = useState(0);
  const [selectedGpu, setSelectedGpu] = useState<number | 'all'>('all');
  const [latestGpuData, setLatestGpuData] = useState<RealtimeData['gpu_list']>([]);
  const [latestCpu, setLatestCpu] = useState(0);
  const [latestRam, setLatestRam] = useState(0);

  // 保留最近 120 個資料點（60 秒，0.5s 間隔，模仿 GPU HOT）
  const maxDataPoints = 120;

  useEffect(() => {
    const eventSource = new EventSource('/api/stream/status');
    let dataIndexRef = 0; // 使用區域變數來避免無限重建

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

        const newPoint: ChartDataPoint = {
          time: timestamp,
          index: dataIndexRef % maxDataPoints, // 循環使用索引,防止無限增長
          cpu: parsedData.cpu_usage || 0,
          ram: parsedData.ram_usage || 0,
        };

        dataIndexRef++;

        if (parsedData.gpu_list && parsedData.gpu_list.length > 0) {
          setGpuCount(parsedData.gpu_list.length);
          setLatestGpuData(parsedData.gpu_list);

          parsedData.gpu_list.forEach((gpu) => {
            newPoint[`gpu${gpu.gpu_id}`] = gpu.gpu_usage || 0;
            newPoint[`vram${gpu.gpu_id}`] = gpu.vram_usage || 0;
            newPoint[`temp${gpu.gpu_id}`] = gpu.temperature || 0;
            newPoint[`power${gpu.gpu_id}`] = gpu.power_draw || 0;
            newPoint[`fan${gpu.gpu_id}`] = gpu.fan_speed || 0;
            newPoint[`clock_graphics${gpu.gpu_id}`] = gpu.clock_graphics || 0;
            newPoint[`clock_memory${gpu.gpu_id}`] = gpu.clock_memory || 0;
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
  }, []); // 移除依賴,只在 mount 時建立連線

  // GPU 詳細視圖組件
  const GpuDetailView = ({ gpuId, color }: { gpuId: number; color: typeof GPU_COLORS[0] }) => {
    const gpu = latestGpuData.find(g => g.gpu_id === gpuId);
    const usage = gpu?.gpu_usage || 0;
    const vram = gpu?.vram_usage || 0;
    const temp = gpu?.temperature || 0;
    const power = gpu?.power_draw || 0;
    const powerLimit = gpu?.power_limit || 0;
    const fan = gpu?.fan_speed || 0;

    const chartConfig = {
      height: 200,
      cartesianGrid: { stroke: "#374151", strokeDasharray: "3 3", vertical: false },
      xAxis: { dataKey: "time", tick: { fill: 'rgba(255, 255, 255, 0.55)', fontSize: 10 }, interval: "preserveStartEnd" as const },
      yAxis: { tick: { fill: 'rgba(255, 255, 255, 0.55)', fontSize: 10 } },
      tooltip: {
        contentStyle: { backgroundColor: 'rgba(0, 0, 0, 0.9)', borderRadius: '12px', border: '2px solid #4facfe', fontSize: '11px', padding: '12px' },
        labelStyle: { color: '#ffffff', fontWeight: 'bold' as const },
        wrapperStyle: { pointerEvents: 'none' as const },
        isAnimationActive: false,
      },
    };

    return (
      <div className="space-y-6">
        {/* GPU Info Panel */}
        <div className="bg-gray-900/60 rounded-xl p-4 border border-gray-700/50">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-2xl font-bold text-gray-100 mb-1">GPU {gpuId}</h3>
              <p className="text-gray-400 text-sm">{gpu?.gpu_name || 'Unknown GPU'}</p>
            </div>
            <div className="flex gap-3 text-xs text-gray-400">
              {gpu?.fan_speed !== undefined && gpu.fan_speed > 0 && (
                <span>{gpu.fan_speed.toFixed(0)}% Fan</span>
              )}
              {gpu?.performance_state && (
                <span>{gpu.performance_state}</span>
              )}
              {gpu?.pcie_gen && (
                <span>PCIe Gen {gpu.pcie_gen}</span>
              )}
            </div>
          </div>
        </div>
        {/* Header Stats */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <div className="text-center p-4 bg-gray-900/40 rounded-lg border border-gray-700/50">
            <div className="text-xs text-gray-400 mb-1">GPU Usage</div>
            <div className="text-2xl font-bold" style={{ color: color.main }}>{usage.toFixed(1)}%</div>
          </div>
          <div className="text-center p-4 bg-gray-900/40 rounded-lg border border-gray-700/50">
            <div className="text-xs text-gray-400 mb-1">VRAM</div>
            {gpu?.vram_used_mb !== undefined && gpu?.vram_total_mb !== undefined ? (
              <>
                <div className="text-lg font-bold" style={{ color: color.light }}>
                  {(gpu.vram_used_mb / 1024).toFixed(1)} / {(gpu.vram_total_mb / 1024).toFixed(1)} GB
                </div>
                <div className="text-xs text-gray-500 mt-1">{vram.toFixed(1)}%</div>
              </>
            ) : (
              <div className="text-2xl font-bold" style={{ color: color.light }}>{vram.toFixed(1)}%</div>
            )}
          </div>
          <div className="text-center p-4 bg-gray-900/40 rounded-lg border border-gray-700/50">
            <div className="text-xs text-gray-400 mb-1">Temperature</div>
            <div className={`text-2xl font-bold ${temp > 80 ? 'text-red-400' : temp > 60 ? 'text-yellow-400' : 'text-green-400'}`}>
              {temp}°C
            </div>
          </div>
          {power > 0 && (
            <div className="text-center p-4 bg-gray-900/40 rounded-lg border border-gray-700/50">
              <div className="text-xs text-gray-400 mb-1">Power Draw</div>
              <div className="text-2xl font-bold text-green-400">{power.toFixed(1)}W</div>
              {powerLimit > 0 && (
                <div className="text-xs text-gray-500 mt-1">/ {powerLimit.toFixed(0)}W</div>
              )}
            </div>
          )}
          {fan > 0 && (
            <div className="text-center p-4 bg-gray-900/40 rounded-lg border border-gray-700/50">
              <div className="text-xs text-gray-400 mb-1">Fan Speed</div>
              <div className="text-2xl font-bold text-blue-400">{fan.toFixed(0)}%</div>
            </div>
          )}
          {gpu?.clock_graphics && gpu.clock_graphics > 0 && (
            <div className="text-center p-4 bg-gray-900/40 rounded-lg border border-gray-700/50">
              <div className="text-xs text-gray-400 mb-1">GPU Clock</div>
              <div className="text-2xl font-bold text-purple-400">{gpu.clock_graphics} MHz</div>
            </div>
          )}
        </div>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* GPU Usage */}
          <div className="bg-gray-900/40 rounded-xl p-4 border border-gray-700/50">
            <h4 className="text-sm font-medium text-gray-300 mb-3">GPU Usage (%)</h4>
            <div style={{ width: '100%', height: chartConfig.height }}>
              <ResponsiveContainer width="100%" height={chartConfig.height}>
                <LineChart data={data}>
                  <CartesianGrid {...chartConfig.cartesianGrid} />
                  <XAxis {...chartConfig.xAxis} />
                  <YAxis domain={[0, 100]} width={35} {...chartConfig.yAxis} />
                  <Tooltip {...chartConfig.tooltip} />
                  <defs>
                    <linearGradient id={`colorGpu${gpuId}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={color.main} stopOpacity={0.3}/>
                      <stop offset="95%" stopColor={color.main} stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <Line type="monotone" dataKey={`gpu${gpuId}`} stroke={color.main} strokeWidth={3} dot={false} isAnimationActive={false} animationDuration={0} fill={`url(#colorGpu${gpuId})`} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Temperature */}
          <div className="bg-gray-900/40 rounded-xl p-4 border border-gray-700/50">
            <h4 className="text-sm font-medium text-gray-300 mb-3">Temperature (°C)</h4>
            <div style={{ width: '100%', height: chartConfig.height }}>
              <ResponsiveContainer width="100%" height={chartConfig.height}>
                <LineChart data={data}>
                  <CartesianGrid {...chartConfig.cartesianGrid} />
                  <XAxis {...chartConfig.xAxis} />
                  <YAxis domain={[0, 100]} width={35} {...chartConfig.yAxis} />
                  <Tooltip {...chartConfig.tooltip} />
                  <defs>
                    <linearGradient id={`colorTemp${gpuId}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#F59E0B" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#F59E0B" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <Line type="monotone" dataKey={`temp${gpuId}`} stroke="#F59E0B" strokeWidth={3} dot={false} isAnimationActive={false} animationDuration={0} fill={`url(#colorTemp${gpuId})`} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* VRAM Usage */}
          <div className="bg-gray-900/40 rounded-xl p-4 border border-gray-700/50">
            <h4 className="text-sm font-medium text-gray-300 mb-3">VRAM Usage (%)</h4>
            <div style={{ width: '100%', height: chartConfig.height }}>
              <ResponsiveContainer width="100%" height={chartConfig.height}>
                <LineChart data={data}>
                  <CartesianGrid {...chartConfig.cartesianGrid} />
                  <XAxis {...chartConfig.xAxis} />
                  <YAxis domain={[0, 100]} width={35} {...chartConfig.yAxis} />
                  <Tooltip {...chartConfig.tooltip} />
                  <defs>
                    <linearGradient id={`colorVram${gpuId}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={color.light} stopOpacity={0.3}/>
                      <stop offset="95%" stopColor={color.light} stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <Line type="monotone" dataKey={`vram${gpuId}`} stroke={color.light} strokeWidth={3} dot={false} isAnimationActive={false} animationDuration={0} fill={`url(#colorVram${gpuId})`} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Power Draw */}
          {power > 0 && (
            <div className="bg-gray-900/40 rounded-xl p-4 border border-gray-700/50">
              <h4 className="text-sm font-medium text-gray-300 mb-3">Power Draw (W)</h4>
              <div style={{ width: '100%', height: chartConfig.height }}>
                <ResponsiveContainer width="100%" height={chartConfig.height}>
                  <LineChart data={data}>
                    <CartesianGrid {...chartConfig.cartesianGrid} />
                    <XAxis {...chartConfig.xAxis} />
                    <YAxis domain={[0, powerLimit > 0 ? powerLimit * 1.1 : 300]} width={35} {...chartConfig.yAxis} />
                    <Tooltip {...chartConfig.tooltip} />
                    <defs>
                      <linearGradient id={`colorPower${gpuId}`} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10B981" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#10B981" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <Line type="monotone" dataKey={`power${gpuId}`} stroke="#10B981" strokeWidth={3} dot={false} isAnimationActive={false} animationDuration={0} fill={`url(#colorPower${gpuId})`} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Fan Speed */}
          {fan > 0 && (
            <div className="bg-gray-900/40 rounded-xl p-4 border border-gray-700/50">
              <h4 className="text-sm font-medium text-gray-300 mb-3">Fan Speed (%)</h4>
              <div style={{ width: '100%', height: chartConfig.height }}>
                <ResponsiveContainer width="100%" height={chartConfig.height}>
                  <LineChart data={data}>
                    <CartesianGrid {...chartConfig.cartesianGrid} />
                    <XAxis {...chartConfig.xAxis} />
                    <YAxis domain={[0, 100]} width={35} {...chartConfig.yAxis} />
                    <Tooltip {...chartConfig.tooltip} />
                    <defs>
                      <linearGradient id={`colorFan${gpuId}`} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#3B82F6" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <Line type="monotone" dataKey={`fan${gpuId}`} stroke="#3B82F6" strokeWidth={3} dot={false} isAnimationActive={false} animationDuration={0} fill={`url(#colorFan${gpuId})`} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Clock Speeds */}
          {gpu?.clock_graphics && gpu.clock_graphics > 0 && (
            <div className="bg-gray-900/40 rounded-xl p-4 border border-gray-700/50">
              <h4 className="text-sm font-medium text-gray-300 mb-3">Clock Speeds (MHz)</h4>
              <div style={{ width: '100%', height: chartConfig.height }}>
                <ResponsiveContainer width="100%" height={chartConfig.height}>
                  <LineChart data={data}>
                    <CartesianGrid {...chartConfig.cartesianGrid} />
                    <XAxis {...chartConfig.xAxis} />
                    <YAxis width={40} {...chartConfig.yAxis} />
                    <Tooltip {...chartConfig.tooltip} />
                    <defs>
                      <linearGradient id={`colorClockGr${gpuId}`} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#A78BFA" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#A78BFA" stopOpacity={0}/>
                      </linearGradient>
                      <linearGradient id={`colorClockMem${gpuId}`} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#34D399" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#34D399" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <Line type="monotone" dataKey={`clock_graphics${gpuId}`} stroke="#A78BFA" strokeWidth={3} dot={false} isAnimationActive={false} animationDuration={0} fill={`url(#colorClockGr${gpuId})`} name="Graphics" />
                    <Line type="monotone" dataKey={`clock_memory${gpuId}`} stroke="#34D399" strokeWidth={3} dot={false} isAnimationActive={false} animationDuration={0} fill={`url(#colorClockMem${gpuId})`} name="Memory" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  // GPU 卡片組件
  const GpuCard = ({ gpuId, color }: { gpuId: number; color: typeof GPU_COLORS[0] }) => {
    const gpu = latestGpuData.find(g => g.gpu_id === gpuId);
    const usage = gpu?.gpu_usage || 0;
    const vram = gpu?.vram_usage || 0;
    const temp = gpu?.temperature || 0;

    return (
      <div
        className="bg-gray-900/60 rounded-xl p-4 border border-gray-700/50 cursor-pointer hover:border-gray-600 hover:bg-gray-900/80 transition-all"
        onClick={() => setSelectedGpu(gpuId)}
      >
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color.main }} />
            <span className="text-sm text-gray-400">GPU {gpuId}</span>
          </div>
          <span className="text-xs text-gray-500">{temp}°C</span>
        </div>

        <div className="grid grid-cols-2 gap-3 mb-3">
          <div>
            <div className="text-xs text-gray-500 mb-1">Usage</div>
            <div className="text-xl font-bold" style={{ color: color.main }}>{usage.toFixed(1)}%</div>
          </div>
          <div>
            <div className="text-xs text-gray-500 mb-1">VRAM</div>
            {gpu?.vram_used_mb !== undefined && gpu?.vram_total_mb !== undefined ? (
              <div className="text-lg font-bold" style={{ color: color.light }}>
                {(gpu.vram_used_mb / 1024).toFixed(1)} / {(gpu.vram_total_mb / 1024).toFixed(1)} GB
              </div>
            ) : (
              <div className="text-xl font-bold" style={{ color: color.light }}>{vram.toFixed(1)}%</div>
            )}
          </div>
        </div>

        <div style={{ width: '100%', height: 80, minWidth: 0 }}>
          <ResponsiveContainer width="100%" height={80}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
              <XAxis dataKey="time" hide />
              <YAxis
                domain={[0, 100]}
                tick={{ fill: 'rgba(255, 255, 255, 0.55)', fontSize: 9 }}
                width={25}
              />
              <Tooltip
                contentStyle={{ backgroundColor: '#1F2937', borderRadius: '8px', border: '1px solid #374151', fontSize: '11px' }}
                labelStyle={{ color: '#9CA3AF' }}
                wrapperStyle={{ pointerEvents: 'none' }}
                isAnimationActive={false}
              />
              <Line type="monotone" dataKey={`gpu${gpuId}`} stroke={color.main} strokeWidth={2} dot={false} isAnimationActive={false} animationDuration={0} connectNulls={false} name="GPU" />
              <Line type="monotone" dataKey={`vram${gpuId}`} stroke={color.light} strokeWidth={2} strokeDasharray="3 3" dot={false} isAnimationActive={false} animationDuration={0} connectNulls={false} name="VRAM" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* System Monitor Panel - Left: Info, Right: Chart */}
      <div className="bg-gray-800/80 backdrop-blur-md p-6 rounded-2xl border border-gray-700 shadow-lg">
        <div className="flex items-center gap-2 mb-4">
          <Activity className="w-6 h-6 text-green-400" />
          <h2 className="text-xl font-bold text-gray-100">即時系統監控</h2>
          <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: System Info */}
          <div className="space-y-4">
            {/* CPU */}
            <div className="bg-gray-900/60 rounded-xl p-4 border border-gray-700/50">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-red-400" />
                  <span className="text-sm text-gray-400">CPU</span>
                </div>
                <span className="text-2xl font-bold text-red-400">{latestCpu.toFixed(1)}%</span>
              </div>
              <div className="text-xs text-gray-500 mb-2">
                {status?.system_info?.cpu_count || '?'} cores • {status?.cpu_source || 'N/A'}
              </div>
              <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-300 bg-red-500"
                  style={{ width: `${Math.min(latestCpu, 100)}%` }}
                />
              </div>
            </div>

            {/* RAM */}
            <div className="bg-gray-900/60 rounded-xl p-4 border border-gray-700/50">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <MemoryStick className="w-4 h-4 text-cyan-400" />
                  <span className="text-sm text-gray-400">RAM</span>
                </div>
                <span className="text-2xl font-bold text-cyan-400">{latestRam.toFixed(1)}%</span>
              </div>
              <div className="text-xs text-gray-500 mb-2">
                {status?.ram_used_gb ? `${status.ram_used_gb.toFixed(1)} / ${status.ram_total_gb.toFixed(1)} GB` : 'N/A'}
              </div>
              <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-300 bg-cyan-500"
                  style={{ width: `${Math.min(latestRam, 100)}%` }}
                />
              </div>
            </div>
          </div>

          {/* Right: Chart */}
          <div className="lg:col-span-2 bg-gray-900/40 rounded-xl border border-gray-700/50 p-4">
            <div className="flex items-center justify-between text-xs text-gray-400 mb-2">
              <span>CPU {latestCpu.toFixed(1)}%</span>
              <span>RAM {latestRam.toFixed(1)}%</span>
            </div>
            <div style={{ width: '100%', height: 180, minWidth: 0 }}>
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={data}>
                  <CartesianGrid stroke="#374151" strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="time"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: 'rgba(255, 255, 255, 0.55)', fontSize: 11 }}
                    interval="preserveStartEnd"
                    minTickGap={50}
                  />
                  <YAxis
                    domain={[0, 100]}
                    width={35}
                    tick={{ fill: 'rgba(255, 255, 255, 0.55)', fontSize: 10 }}
                  />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1F2937', borderRadius: '8px', border: '1px solid #374151', fontSize: '11px' }}
                    labelStyle={{ color: '#9CA3AF' }}
                    wrapperStyle={{ pointerEvents: 'none' }}
                    isAnimationActive={false}
                  />
                  <Line type="monotone" dataKey="cpu" stroke="#EF4444" strokeWidth={2} dot={false} isAnimationActive={false} animationDuration={0} connectNulls={false} name="CPU" />
                  <Line type="monotone" dataKey="ram" stroke="#06B6D4" strokeWidth={2} dot={false} isAnimationActive={false} animationDuration={0} connectNulls={false} name="RAM" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      {/* GPU Section */}
      {gpuCount > 0 && (
        <div className="bg-gray-800/80 backdrop-blur-md p-6 rounded-2xl border border-gray-700 shadow-lg">
          {/* GPU Tabs */}
          <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
            <button
              onClick={() => setSelectedGpu('all')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors whitespace-nowrap ${
                selectedGpu === 'all'
                  ? 'bg-gray-100 text-gray-900'
                  : 'bg-gray-700/50 text-gray-300 hover:bg-gray-700'
              }`}
            >
              All GPUs
            </button>
            {Array.from({ length: gpuCount }).map((_, i) => {
              const gpu = latestGpuData.find(g => g.gpu_id === i);
              const usage = gpu?.gpu_usage || 0;
              const color = GPU_COLORS[i % GPU_COLORS.length];
              return (
                <button
                  key={i}
                  onClick={() => setSelectedGpu(i)}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors whitespace-nowrap flex items-center gap-2 ${
                    selectedGpu === i
                      ? 'bg-gray-100 text-gray-900'
                      : 'bg-gray-700/50 text-gray-300 hover:bg-gray-700'
                  }`}
                >
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: color.main }} />
                  GPU {i}
                  <span className="text-xs opacity-70">{usage.toFixed(0)}%</span>
                </button>
              );
            })}
          </div>

          {/* Content based on selected tab */}
          {selectedGpu === 'all' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
              {Array.from({ length: gpuCount }).map((_, i) => (
                <GpuCard key={i} gpuId={i} color={GPU_COLORS[i % GPU_COLORS.length]} />
              ))}
            </div>
          ) : (
            <div className="space-y-4">
              <GpuDetailView gpuId={selectedGpu} color={GPU_COLORS[selectedGpu % GPU_COLORS.length]} />
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default RealtimeChart;
