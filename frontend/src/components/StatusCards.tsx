import React, { useMemo, useState } from 'react';
import { Cpu, Database, HardDrive, Gamepad2, Zap, Thermometer, Activity, Gauge } from 'lucide-react';
import type { SystemStatus, GPUInfo } from '../types';

interface StatusCardsProps {
  status?: SystemStatus;
}

const Card: React.FC<{
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}> = ({ title, icon, children, className = '' }) => (
  <div className={`bg-gray-800/80 backdrop-blur-md p-6 rounded-2xl border border-gray-700 shadow-lg hover:shadow-xl hover:-translate-y-1 transition-all duration-300 ${className}`}>
    <div className="flex items-center gap-3 mb-4">
      {icon}
      <h3 className="text-xl font-semibold text-gray-100">{title}</h3>
    </div>
    <div className="space-y-3">
      {children}
    </div>
  </div>
);

const MetricRow: React.FC<{ label: string; value: string | number; subValue?: string }> = ({ label, value, subValue }) => (
  <div className="flex justify-between items-center py-2 border-b border-gray-700/50 last:border-0">
    <span className="text-gray-400 font-medium">{label}</span>
    <div className="text-right">
      <div className="text-gray-100 font-bold text-lg">{value}</div>
      {subValue && <div className="text-xs text-gray-500">{subValue}</div>}
    </div>
  </div>
);

const CircularProgress: React.FC<{ value: number; size?: number; strokeWidth?: number; color?: string }> = ({ 
  value, 
  size = 120, 
  strokeWidth = 10,
  color = "#3b82f6"
}) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (value / 100) * circumference;

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="#1f2937"
          strokeWidth={strokeWidth}
          fill="transparent"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth={strokeWidth}
          fill="transparent"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-1000 ease-out"
        />
      </svg>
      <div className="absolute flex flex-col items-center justify-center text-gray-100">
        <span className="text-3xl font-bold">{Math.round(value)}%</span>
        <span className="text-xs text-gray-400">Usage</span>
      </div>
    </div>
  );
};

interface AggregatedGPUStats {
  count: number;
  avgUsage: number;
  totalVramUsed: number;
  totalVram: number;
  avgTemp: number | null;
}

const GPUOverviewCard: React.FC<{ stats: AggregatedGPUStats }> = ({ stats }) => {
  const toGB = (mb: number) => (mb / 1024).toFixed(1);
  return (
    <Card 
      title={`GPU Overview (${stats.count} GPUs)`} 
      icon={<Gamepad2 className="w-6 h-6 text-green-400" />}
      className="col-span-full"
    >
      <MetricRow label="平均使用率" value={`${stats.avgUsage.toFixed(1)}%`} />
      <MetricRow 
        label="VRAM 使用" 
        value={`${toGB(stats.totalVramUsed)} GB`} 
        subValue={`/ ${toGB(stats.totalVram)} GB`}
      />
      <MetricRow 
        label="平均溫度" 
        value={stats.avgTemp !== null ? `${stats.avgTemp.toFixed(1)}°C` : 'N/A'} 
      />
    </Card>
  );
};

const GPUCard: React.FC<{ gpu: GPUInfo }> = ({ gpu }) => {
  const utilColor = (gpu.gpu_usage || 0) > 80 ? "#ef4444" : (gpu.gpu_usage || 0) > 50 ? "#eab308" : "#3b82f6";
  
  return (
    <div className="bg-gray-800/80 backdrop-blur-md p-6 rounded-2xl border border-gray-700 shadow-lg hover:shadow-xl transition-all duration-300 col-span-1 md:col-span-2 lg:col-span-2">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <Gamepad2 className="w-8 h-8 text-green-400" />
          <div>
            <h3 className="text-2xl font-bold text-gray-100">{gpu.gpu_name}</h3>
            <div className="text-sm text-gray-400">GPU #{gpu.gpu_id} • {gpu.performance_state || 'Unknown State'}</div>
          </div>
        </div>
        <div className="text-right">
          <div className="text-gray-100 font-semibold text-lg">{(gpu.gpu_usage ?? 0).toFixed(1)}%</div>
          <div className="text-xs text-gray-500">
            VRAM {(gpu.vram_usage ?? 0).toFixed(1)}%
          </div>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Utilization Circle */}
        <div className="flex flex-col items-center justify-center p-4 bg-gray-900/50 rounded-xl border border-gray-700/50">
          <CircularProgress value={gpu.gpu_usage || 0} color={utilColor} />
          <div className="mt-4 text-center">
            <div className="text-gray-400 text-sm">Memory Usage</div>
            <div className="text-gray-200 font-semibold">
              {gpu.vram_usage?.toFixed(1)}%
            </div>
            <div className="text-xs text-gray-500">
              {(gpu.vram_used_mb || 0) / 1024 < 1 
                ? `${gpu.vram_used_mb} MB` 
                : `${((gpu.vram_used_mb || 0) / 1024).toFixed(1)} GB`} 
              / 
              {((gpu.vram_total_mb || 0) / 1024).toFixed(1)} GB
            </div>
          </div>
        </div>

        {/* Detailed Metrics Grid */}
        <div className="col-span-2 grid grid-cols-2 gap-4">
          {/* Temperature */}
          <div className="bg-gray-900/30 p-4 rounded-xl border border-gray-700/30">
            <div className="flex items-center gap-2 text-gray-400 mb-2">
              <Thermometer className="w-4 h-4" />
              <span className="text-sm">Temperature</span>
            </div>
            <div className="text-2xl font-bold text-gray-100">{gpu.temperature}°C</div>
            <div className="text-xs text-gray-500">
              {gpu.temperature && gpu.temperature < 60 ? 'Cool' : gpu.temperature && gpu.temperature < 80 ? 'Normal' : 'Hot'}
            </div>
          </div>

          {/* Power */}
          <div className="bg-gray-900/30 p-4 rounded-xl border border-gray-700/30">
            <div className="flex items-center gap-2 text-gray-400 mb-2">
              <Zap className="w-4 h-4" />
              <span className="text-sm">Power Draw</span>
            </div>
            <div className="text-2xl font-bold text-gray-100">{gpu.power_draw?.toFixed(0) || 'N/A'} W</div>
            <div className="text-xs text-gray-500">
              Limit: {gpu.power_limit?.toFixed(0) || 'N/A'} W
            </div>
          </div>

          {/* Clocks */}
          <div className="bg-gray-900/30 p-4 rounded-xl border border-gray-700/30">
            <div className="flex items-center gap-2 text-gray-400 mb-2">
              <Activity className="w-4 h-4" />
              <span className="text-sm">Clocks</span>
            </div>
            <div className="flex justify-between items-end">
              <div>
                <div className="text-lg font-bold text-gray-100">{gpu.clock_graphics || 0}</div>
                <div className="text-xs text-gray-500">Graphics MHz</div>
              </div>
              <div className="text-right">
                <div className="text-lg font-bold text-gray-100">{gpu.clock_memory || 0}</div>
                <div className="text-xs text-gray-500">Memory MHz</div>
              </div>
            </div>
          </div>

          {/* PCIe */}
          <div className="bg-gray-900/30 p-4 rounded-xl border border-gray-700/30 flex justify-between items-center">
            <div>
              <div className="flex items-center gap-2 text-gray-400 mb-1">
                <Gauge className="w-4 h-4" />
                <span className="text-sm">PCIe Link</span>
              </div>
              <div className="text-gray-100 font-semibold">
                Gen {gpu.pcie_gen || 'N/A'} x{gpu.pcie_width || 'N/A'}
              </div>
            </div>
            <div className="text-right">
              <div className="text-xs text-gray-400">Throughput</div>
              <div className="text-gray-200 text-sm">
                <span className="mr-2">↓ {gpu.pcie_rx?.toFixed(0) || 0} KB/s</span>
                <span>↑ {gpu.pcie_tx?.toFixed(0) || 0} KB/s</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export const StatusCards: React.FC<StatusCardsProps> = ({ status }) => {
  if (!status) return <div className="text-center py-10">Loading status...</div>;
  const aggregatedGpuStats = useMemo<AggregatedGPUStats | null>(() => {
    if (!status?.gpu_list || status.gpu_list.length === 0) return null;
    const count = status.gpu_list.length;
    const usageValues = status.gpu_list
      .map(g => g.gpu_usage)
      .filter((v): v is number => typeof v === 'number' && !Number.isNaN(v));
    const avgUsage = usageValues.length
      ? usageValues.reduce((sum, val) => sum + val, 0) / usageValues.length
      : 0;
    const totalVramUsed = status.gpu_list.reduce(
      (sum, gpu) => sum + (gpu.vram_used_mb || 0),
      0
    );
    const totalVram = status.gpu_list.reduce(
      (sum, gpu) => sum + (gpu.vram_total_mb || 0),
      0
    );
    const tempValues = status.gpu_list
      .map(g => g.temperature)
      .filter((v): v is number => typeof v === 'number' && !Number.isNaN(v));
    const avgTemp = tempValues.length
      ? tempValues.reduce((sum, val) => sum + val, 0) / tempValues.length
      : null;
    return { count, avgUsage, totalVramUsed, totalVram, avgTemp };
  }, [status?.gpu_list]);
  const [gpuViewMode, setGpuViewMode] = useState<'individual' | 'summary'>('individual');

  const switchGpuViewMode = () => {
    setGpuViewMode(prev => (prev === 'summary' ? 'individual' : 'summary'));
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      {/* CPU Card */}
      <Card 
        title={`CPU (${status.system_info.cpu_count} Cores)`} 
        icon={<Cpu className="w-6 h-6 text-blue-400" />}
      >
        <MetricRow label="Usage" value={`${status.cpu_usage.toFixed(1)}%`} />
        <MetricRow label="Source" value={status.cpu_source} />
        <div className="w-full bg-gray-700 h-2 rounded-full mt-2">
          <div 
            className="bg-blue-500 h-2 rounded-full transition-all duration-500" 
            style={{ width: `${Math.min(status.cpu_usage, 100)}%` }}
          />
        </div>
      </Card>

      {/* RAM Card */}
      <Card 
        title={`Memory (${status.ram_total_gb.toFixed(1)}GB)`} 
        icon={<HardDrive className="w-6 h-6 text-purple-400" />}
      >
        <MetricRow 
          label="Used" 
          value={`${status.ram_used_gb.toFixed(1)}GB`} 
          subValue={`/ ${status.ram_total_gb.toFixed(1)}GB`}
        />
        <MetricRow label="Usage" value={`${status.ram_usage.toFixed(1)}%`} />
        <div className="w-full bg-gray-700 h-2 rounded-full mt-2">
          <div 
            className="bg-purple-500 h-2 rounded-full transition-all duration-500" 
            style={{ width: `${Math.min(status.ram_usage, 100)}%` }}
          />
        </div>
      </Card>

      {/* Database Card */}
      <Card 
        title="Database" 
        icon={<Database className="w-6 h-6 text-yellow-400" />}
      >
        <MetricRow label="Records" value={status.total_records.toLocaleString()} />
        <MetricRow label="Size" value={`${status.database_size_mb.toFixed(2)} MB`} />
        <MetricRow
          label="Range"
          value={status.earliest_record ? new Date(status.earliest_record).toLocaleDateString('zh-TW', { year: 'numeric', month: '2-digit', day: '2-digit' }) : 'N/A'}
          subValue="~ Now"
        />
      </Card>

      {/* Spacer or Summary */}
      <div className="hidden lg:block bg-gray-800/50 rounded-2xl border border-gray-700/50 p-6 flex flex-col justify-center items-center text-center">
        <div className="text-gray-400 text-sm mb-2">System Status</div>
        <div className="text-green-400 font-bold text-xl flex items-center gap-2">
          <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
          Operational
        </div>
        <div className="text-xs text-gray-500 mt-2">
          Monitoring Active
        </div>
      </div>

      {/* GPU Cards (Full Width) */}
      <div className="col-span-1 md:col-span-2 lg:col-span-4 grid grid-cols-1 lg:grid-cols-2 gap-6">
        {status.gpu_list && status.gpu_list.length > 0 ? (
          <>
            {status.gpu_list.length > 1 && (
              <div className="col-span-full flex">
                <button
                  type="button"
                  onClick={switchGpuViewMode}
                  className="px-4 py-2 text-sm font-medium text-gray-200 bg-gray-700/70 rounded-full border border-gray-600/60 hover:text-white transition"
                >
                  {gpuViewMode === 'summary' ? '顯示個別' : '整合顯示'}
                </button>
              </div>
            )}
            {gpuViewMode === 'summary' && aggregatedGpuStats ? (
              <GPUOverviewCard stats={aggregatedGpuStats} />
            ) : (
              status.gpu_list.map((gpu: GPUInfo) => (
                <GPUCard key={gpu.gpu_id} gpu={gpu} />
              ))
            )}
          </>
        ) : (
          <div className="col-span-full bg-gray-800/80 backdrop-blur-md p-6 rounded-2xl border border-gray-700 text-center text-gray-500">
            No GPU Detected
          </div>
        )}
      </div>
    </div>
  );
};
