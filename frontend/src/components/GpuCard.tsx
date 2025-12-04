import React from 'react';
import { ResponsiveContainer, LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip } from 'recharts';
import type { ChartDataPoint, RealtimeData } from '../types';

interface GpuCardProps {
  gpuId: number;
  color: { main: string; light: string };
  latestGpuData: RealtimeData['gpu_list'];
  data: ChartDataPoint[];
  onSelect: (id: number) => void;
}

export const GpuCard: React.FC<GpuCardProps> = React.memo(({ gpuId, color, latestGpuData, data, onSelect }) => {
  const gpu = latestGpuData.find(g => g.gpu_id === gpuId);
  const usage = gpu?.gpu_usage || 0;
  const vram = gpu?.vram_usage || 0;
  const temp = gpu?.temperature || 0;

  return (
    <div
      className="bg-gray-900/60 rounded-xl p-4 border border-gray-700/50 cursor-pointer hover:border-gray-600 hover:bg-gray-900/80 transition-all"
      onClick={() => onSelect(gpuId)}
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
});
