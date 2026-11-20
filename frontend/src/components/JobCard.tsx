import React from 'react';
import { 
  Play, RotateCw, Pause, Trash2, Youtube, Upload, 
  CheckCircle2, AlertTriangle, Clock, RefreshCw, ChevronRight
} from 'lucide-react';
import { Job, JobStatus } from '../types';

interface JobCardProps {
  job: Job;
  onOpenDetails: (job: Job) => void;
  onRetry: (jobId: string) => void;
  onCancel: (jobId: string) => void;
  onPause: (jobId: string) => void;
  onResume: (jobId: string) => void;
  onDelete: (jobId: string) => void;
}

export const JobCard: React.FC<JobCardProps> = ({
  job,
  onOpenDetails,
  onRetry,
  onCancel,
  onPause,
  onResume,
  onDelete
}) => {
  const getStatusBadge = (status: JobStatus) => {
    switch (status) {
      case 'COMPLETED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Ready ({job.clips.length} Clips)</span>
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-red-500/10 text-red-400 border border-red-500/20">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Failed</span>
          </span>
        );
      case 'QUEUED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-500/10 text-slate-400 border border-slate-500/20">
            <Clock className="w-3.5 h-3.5" />
            <span>Queued</span>
          </span>
        );
      case 'PAUSED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Pause className="w-3.5 h-3.5" />
            <span>Paused</span>
          </span>
        );
      case 'CANCELLED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-700/30 text-slate-400 border border-slate-700/50">
            <span>Cancelled</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-sky-500/10 text-sky-400 border border-sky-500/20">
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            <span>{job.current_stage || status}</span>
          </span>
        );
    }
  };

  const isProcessing = ['DOWNLOADING', 'TRANSCRIBING', 'ANALYZING', 'RENDERING'].includes(job.status);

  return (
    <div className="bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-2xl p-5 transition shadow-sm hover:shadow-md flex flex-col justify-between gap-4">
      <div>
        {/* Top Header */}
        <div className="flex items-start justify-between gap-3 mb-2">
          <div className="flex items-center gap-2">
            {job.source_type === 'youtube' ? (
              <span className="p-1.5 rounded-lg bg-red-500/10 text-red-400">
                <Youtube className="w-4 h-4" />
              </span>
            ) : (
              <span className="p-1.5 rounded-lg bg-sky-500/10 text-sky-400">
                <Upload className="w-4 h-4" />
              </span>
            )}
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              {job.source_type}
            </span>
          </div>
          {getStatusBadge(job.status)}
        </div>

        {/* Project Title */}
        <h3 className="font-semibold text-white text-base leading-snug line-clamp-1 mb-1">
          {job.project_name}
        </h3>
        {job.source_url && (
          <p className="text-xs text-slate-500 truncate mb-3">{job.source_url}</p>
        )}

        {/* Progress Bar */}
        <div className="space-y-1.5 mt-3">
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400 font-medium">
              {isProcessing ? job.current_stage : job.status}
            </span>
            <span className="font-semibold text-slate-300">
              {Math.round(job.progress)}%
            </span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
            <div
              className={`h-full transition-all duration-300 ${
                job.status === 'COMPLETED'
                  ? 'bg-emerald-500'
                  : job.status === 'FAILED'
                  ? 'bg-red-500'
                  : isProcessing
                  ? 'bg-sky-500'
                  : 'bg-slate-600'
              }`}
              style={{ width: `${Math.max(3, job.progress)}%` }}
            />
          </div>
        </div>

        {/* Chunk Details & Metadata */}
        <div className="grid grid-cols-2 gap-2 mt-4 pt-3 border-t border-slate-800/80 text-xs text-slate-400">
          <div>
            <span className="block text-[11px] text-slate-500">Chunks Processed</span>
            <span className="font-medium text-slate-300">
              {job.completed_chunks} / {job.total_chunks || '-'}
            </span>
          </div>
          <div>
            <span className="block text-[11px] text-slate-500">Clips Produced</span>
            <span className="font-medium text-emerald-400">
              {job.clips.length} Short(s)
            </span>
          </div>
        </div>

        {job.error_details && (
          <div className="mt-3 p-2.5 bg-red-950/40 border border-red-900/60 rounded-xl text-xs text-red-300 line-clamp-2">
            ⚠️ {job.error_details}
          </div>
        )}
      </div>

      {/* Action Footer */}
      <div className="flex items-center justify-between pt-3 border-t border-slate-800/80 mt-1">
        <div className="flex items-center gap-1">
          {job.status === 'FAILED' && (
            <button
              onClick={() => onRetry(job.id)}
              className="p-1.5 text-slate-400 hover:text-emerald-400 hover:bg-slate-800 rounded-lg transition"
              title="Retry Job"
            >
              <RotateCw className="w-4 h-4" />
            </button>
          )}
          {isProcessing && (
            <>
              <button
                onClick={() => onPause(job.id)}
                className="p-1.5 text-slate-400 hover:text-amber-400 hover:bg-slate-800 rounded-lg transition"
                title="Pause Job"
              >
                <Pause className="w-4 h-4" />
              </button>
              <button
                onClick={() => onCancel(job.id)}
                className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-slate-800 rounded-lg transition"
                title="Cancel Job"
              >
                <AlertTriangle className="w-4 h-4" />
              </button>
            </>
          )}
          {job.status === 'PAUSED' && (
            <button
              onClick={() => onResume(job.id)}
              className="p-1.5 text-slate-400 hover:text-emerald-400 hover:bg-slate-800 rounded-lg transition"
              title="Resume Job"
            >
              <Play className="w-4 h-4" />
            </button>
          )}
          <button
            onClick={() => onDelete(job.id)}
            className="p-1.5 text-slate-500 hover:text-red-400 hover:bg-slate-800 rounded-lg transition"
            title="Delete Job"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>

        <button
          onClick={() => onOpenDetails(job)}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg transition"
        >
          <span>{job.clips.length > 0 ? 'View Clips' : 'Details & Logs'}</span>
          <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
        </button>
      </div>
    </div>
  );
};
