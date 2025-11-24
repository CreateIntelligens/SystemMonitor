import { useEffect, useState } from 'react';
import axios from 'axios';
import { Header } from './components/Header';
import { StatusCards } from './components/StatusCards';
import { ProcessTable } from './components/ProcessTable';
import { ChartPanel } from './components/ChartPanel';
import type { SystemStatus, ProcessInfo, ProcessResponse } from './types';

function App() {
  const [status, setStatus] = useState<SystemStatus | undefined>(undefined);
  const [processes, setProcesses] = useState<ProcessInfo[]>([]);
  const [isLoadingProcesses, setIsLoadingProcesses] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const [mode, setMode] = useState<'monitor' | 'stats' | 'charts'>('monitor');

  const fetchStatus = async () => {
    try {
      const response = await axios.get<SystemStatus>('/api/status');
      setStatus(response.data);
    } catch (error) {
      console.error('Failed to fetch status:', error);
    }
  };

  const fetchProcesses = async () => {
    setIsLoadingProcesses(true);
    try {
      if (mode === 'monitor') {
        const response = await axios.get<ProcessResponse>('/api/gpu-processes');
        // Map current processes to ProcessInfo format if needed
        const currentProcs = response.data.current.map((p: any) => ({
          ...p,
          start_time: p.start_time || new Date().toISOString(), // Fallback if missing
          ram_mb: p.ram_mb || 0,
          gpu_memory_mb: p.gpu_memory_mb || 0,
          cpu_percent: p.cpu_percent || 0
        }));
        setProcesses(currentProcs);
      } else {
        // For stats mode, we might want to fetch historical data
        // This is a placeholder as the API requires a timespan
        const response = await axios.post('/api/all-processes/1h');
        if (response.data.success) {
          setProcesses(response.data.processes);
        }
      }
      setLastUpdated(new Date());
    } catch (error) {
      console.error('Failed to fetch processes:', error);
    } finally {
      setIsLoadingProcesses(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    fetchProcesses();

    const statusInterval = setInterval(fetchStatus, 2000);
    const processInterval = setInterval(() => {
      if (mode === 'monitor') {
        fetchProcesses();
      }
    }, 5000);

    return () => {
      clearInterval(statusInterval);
      clearInterval(processInterval);
    };
  }, [mode]);

  return (
    <div className="min-h-screen bg-[#1a1b1e] text-gray-100 p-4 md:p-8 font-sans">
      <div className="max-w-[1600px] mx-auto">
        <Header systemInfo={status?.system_info} />
        
        <StatusCards status={status} />

        <div className="mb-8">
          <div className="flex gap-4 mb-6">
            <button
              onClick={() => setMode('monitor')}
              className={`px-6 py-2 rounded-full font-medium transition-all ${
                mode === 'monitor'
                  ? 'bg-gray-100 text-gray-900 shadow-lg shadow-gray-100/20'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              📊 即時監控
            </button>
            <button
              onClick={() => setMode('stats')}
              className={`px-6 py-2 rounded-full font-medium transition-all ${
                mode === 'stats'
                  ? 'bg-gray-100 text-gray-900 shadow-lg shadow-gray-100/20'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              📈 歷史分析
            </button>
            <button
              onClick={() => setMode('charts')}
              className={`px-6 py-2 rounded-full font-medium transition-all ${
                mode === 'charts'
                  ? 'bg-gray-100 text-gray-900 shadow-lg shadow-gray-100/20'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              📊 圖表分析
            </button>
          </div>

          {mode === 'charts' ? (
            <ChartPanel />
          ) : (
            <ProcessTable
              processes={processes}
              isLoading={isLoadingProcesses}
              onRefresh={fetchProcesses}
              mode={mode}
              lastUpdated={lastUpdated}
            />
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
