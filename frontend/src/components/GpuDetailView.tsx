import React from 'react';
import { ResponsiveContainer, LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip } from 'recharts';
import type { ChartDataPoint, RealtimeData } from '../types';

interface GpuDetailViewProps {
  gpuId: number;
  color: { main: string; light: string };
  latestGpuData: RealtimeData['gpu_list'];
  data: ChartDataPoint[];
}

export const GpuDetailView: React.FC<GpuDetailViewProps> = React.memo(({ gpuId, color, latestGpuData, data }) => {
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
});
