import React from 'react';
import { AlertCircle, ExternalLink, Play, CheckCircle2 } from 'lucide-react';
import { SystemStatus } from '../types';

interface WorkerStatusBannerProps {
  status: SystemStatus | null;
}

export const WorkerStatusBanner: React.FC<WorkerStatusBannerProps> = ({ status }) => {
  const isOnline = (status?.workers_online || 0) > 0;
  const activeJobs = status?.active_jobs || 0;

  if (isOnline) {
    return (
      <div className="bg-emerald-950/40 border border-emerald-800/60 rounded-xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-inner">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-emerald-500/20 text-emerald-400">
            <CheckCircle2 className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-emerald-200">Worker Active & Ready</h4>
            <p className="text-xs text-emerald-400/80">
              {status?.workers_online} worker(s) connected. Currently executing {activeJobs} active task(s).
            </p>
          </div>
        </div>
        <div className="text-xs text-slate-400">
          Heartbeats active • Resilient auto-lease enabled
        </div>
      </div>
    );
  }

  return (
    <div className="bg-amber-950/40 border border-amber-800/80 rounded-xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-lg shadow-amber-950/20">
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-amber-500/20 text-amber-400 mt-0.5">
          <AlertCircle className="w-5 h-5" />
        </div>
        <div>
          <h4 className="text-sm font-semibold text-amber-200">Worker Offline — Jobs Are Safely Queued</h4>
          <p className="text-xs text-amber-400/90 mt-0.5">
            You can submit jobs, close your browser, and start the free Google Colab GPU worker whenever convenient.
            No work is lost.
          </p>
        </div>
      </div>
      <a
        href="https://colab.research.google.com"
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold text-xs rounded-lg transition shrink-0"
      >
        <Play className="w-3.5 h-3.5 fill-current" />
        <span>Open Colab Worker</span>
        <ExternalLink className="w-3.5 h-3.5 ml-0.5" />
      </a>
    </div>
  );
};
