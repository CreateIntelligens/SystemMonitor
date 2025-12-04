import React, { useEffect, useState, useRef, useCallback } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Activity, Cpu, MemoryStick } from 'lucide-react';
import type { SystemStatus, ChartDataPoint, RealtimeData } from '../types';
import { GPU_COLORS } from '../constants';
import { GpuCard } from './GpuCard';
import { GpuDetailView } from './GpuDetailView';

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

  // Refs for buffering data to throttle renders
  const dataBufferRef = useRef<ChartDataPoint[]>([]);
  const latestStateRef = useRef<{
    cpu: number;
    ram: number;
    gpuList: RealtimeData['gpu_list'];
  } | null>(null);
  
  // Max data points to keep (60 seconds window)
  const maxDataPoints = 120;

  // Memoized selection handler
  const handleGpuSelect = useCallback((id: number) => {
    setSelectedGpu(id);
  }, []);

  // Handle selecting 'all'
  const handleSelectAll = useCallback(() => {
    setSelectedGpu('all');
  }, []);

  useEffect(() => {
    const eventSource = new EventSource('/api/stream/status');
    let dataIndexRef = 0;

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

        // Update latest state ref (cheap)
        latestStateRef.current = {
          cpu: parsedData.cpu_usage || 0,
          ram: parsedData.ram_usage || 0,
          gpuList: parsedData.gpu_list || []
        };

        const newPoint: ChartDataPoint = {
          time: timestamp,
          index: dataIndexRef % maxDataPoints,
          cpu: parsedData.cpu_usage || 0,
          ram: parsedData.ram_usage || 0,
        };

        dataIndexRef++;

        if (parsedData.gpu_list && parsedData.gpu_list.length > 0) {
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

        // Buffer the new point instead of setting state immediately
        dataBufferRef.current.push(newPoint);
        
        // Keep buffer from growing indefinitely if the interval stops working
        if (dataBufferRef.current.length > maxDataPoints * 2) {
             dataBufferRef.current = dataBufferRef.current.slice(-maxDataPoints);
        }

      } catch (error) {
        console.error('Error parsing SSE data:', error);
      }
    };

    eventSource.onerror = () => {
      setIsConnected(false);
      eventSource.close();
      // Simple reconnect logic handled by effect cleanup and re-mount if needed, 
      // or let the user refresh if it's a hard failure. 
      // For now, we just log it.
      console.error('SSE Connection lost');
    };

    return () => {
      eventSource.close();
    };
  }, []);

  // Throttled update effect
  useEffect(() => {
    const intervalId = setInterval(() => {
      // 1. Update Chart Data if we have new points
      if (dataBufferRef.current.length > 0) {
        const newPoints = [...dataBufferRef.current];
        // Clear buffer
        dataBufferRef.current = [];

        setData((prevData) => {
          const newData = [...prevData, ...newPoints];
          return newData.length > maxDataPoints
            ? newData.slice(newData.length - maxDataPoints)
            : newData;
        });
      }

      // 2. Update Latest Stats if available
      if (latestStateRef.current) {
        const state = latestStateRef.current;
        setLatestCpu(state.cpu);
        setLatestRam(state.ram);
        if (state.gpuList && state.gpuList.length > 0) {
          setGpuCount(state.gpuList.length);
          setLatestGpuData(state.gpuList);
        }
        // Clear ref after reading? No, we might want to keep the latest value 
        // until a new one comes, but we only need to trigger a render if it changed.
        // Since we are setting state every 1s anyway if data comes in, 
        // React will handle the diffing.
      }
    }, 1000); // Update UI once per second

    return () => clearInterval(intervalId);
  }, []);

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
              onClick={handleSelectAll}
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
                  onClick={() => handleGpuSelect(i)}
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
                <GpuCard
                  key={i}
                  gpuId={i}
                  color={GPU_COLORS[i % GPU_COLORS.length]}
                  latestGpuData={latestGpuData}
                  data={data}
                  onSelect={handleGpuSelect}
                />
              ))}
            </div>
          ) : (
            <div className="space-y-4">
              <GpuDetailView
                gpuId={selectedGpu as number}
                color={GPU_COLORS[(selectedGpu as number) % GPU_COLORS.length]}
                latestGpuData={latestGpuData}
                data={data}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default RealtimeChart;
