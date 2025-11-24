import React, { useEffect, useState } from 'react';
import { Monitor, Clock } from 'lucide-react';
import type { SystemInfo } from '../types';

interface HeaderProps {
  systemInfo?: SystemInfo;
}

export const Header: React.FC<HeaderProps> = ({ systemInfo }) => {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <header className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
      <div>
        <div className="flex items-center gap-3 mb-2">
          <Monitor className="w-8 h-8 text-emerald-400" />
          <h1 className="text-3xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
            系統監控
          </h1>
        </div>
        <div className="flex items-center gap-2 text-gray-400 text-sm">
          <span className="bg-gray-800 px-3 py-1 rounded-full border border-gray-700">
            {systemInfo?.hostname || 'Loading...'} 
            {systemInfo?.local_ip && ` (${systemInfo.local_ip})`}
          </span>
          <span>實時系統狀態監控與分析</span>
        </div>
      </div>

      <div className="flex items-center gap-2 bg-gray-800/50 px-4 py-2 rounded-xl border border-gray-700/50 backdrop-blur-sm">
        <Clock className="w-5 h-5 text-cyan-400" />
        <span className="font-mono text-lg text-gray-200">
          {time.toLocaleDateString('zh-TW', { year: 'numeric', month: '2-digit', day: '2-digit' })} {time.toLocaleTimeString('zh-TW', { hour12: false })} (UTC+8)
        </span>
      </div>
    </header>
  );
};
