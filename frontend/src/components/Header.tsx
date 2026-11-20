import React from 'react';
import { Scissors, PlusCircle, RefreshCw, Cpu } from 'lucide-react';
import { SystemStatus } from '../types';

interface HeaderProps {
  systemStatus: SystemStatus | null;
  onNewProject: () => void;
  onRefresh: () => void;
  isRefreshing: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  systemStatus,
  onNewProject,
  onRefresh,
  isRefreshing
}) => {
  const onlineCount = systemStatus?.workers_online || 0;
  const isWorkerOnline = onlineCount > 0;

  return (
    <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-400 flex items-center justify-center shadow-lg shadow-emerald-500/20">
            <Scissors className="w-5 h-5 text-slate-950 font-bold" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg tracking-tight text-white">ClipForge</span>
              <span className="px-1.5 py-0.5 text-xs font-semibold rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                AI 2.0
              </span>
            </div>
            <p className="text-xs text-slate-400">Zero-Cost Distributed Video Clipping</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Worker Status Pill */}
          <div className={`hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border ${
            isWorkerOnline 
              ? 'bg-emerald-950/60 border-emerald-800 text-emerald-300' 
              : 'bg-amber-950/60 border-amber-800 text-amber-300'
          }`}>
            <span className={`w-2 h-2 rounded-full ${isWorkerOnline ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
            <Cpu className="w-3.5 h-3.5" />
            <span>
              {isWorkerOnline 
                ? `${onlineCount} GPU Worker${onlineCount > 1 ? 's' : ''} Online` 
                : 'Worker Offline (Waiting for Colab)'}
            </span>
          </div>

          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition"
            title="Refresh queue"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-emerald-400' : ''}`} />
          </button>

          <button
            onClick={onNewProject}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-semibold text-sm rounded-lg shadow-md shadow-emerald-600/20 transition active:scale-95"
          >
            <PlusCircle className="w-4 h-4" />
            <span>New Video</span>
          </button>
        </div>
      </div>
    </header>
  );
};
