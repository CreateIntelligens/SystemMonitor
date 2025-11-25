import React from 'react';
import { Database } from 'lucide-react';
import type { SystemStatus } from '../types';

interface StatusCardsProps {
  status?: SystemStatus;
}

export const StatusCards: React.FC<StatusCardsProps> = ({ status }) => {
  if (!status) return null;

  return (
    <div className="mt-8">
      <div className="bg-gray-800/50 backdrop-blur-sm px-6 py-3 rounded-xl border border-gray-700/50 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Database className="w-4 h-4 text-gray-400" />
          <span className="text-sm text-gray-400">Database</span>
        </div>
        <div className="flex items-center gap-6 text-sm">
          <span className="text-gray-300">
            {status.total_records.toLocaleString()} records
          </span>
          <span className="text-gray-500">•</span>
          <span className="text-gray-300">
            {status.database_size_mb.toFixed(1)} MB
          </span>
        </div>
      </div>
    </div>
  );
};
