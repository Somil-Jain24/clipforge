import React, { useState, useEffect } from 'react';
import { 
  X, Download, Play, Terminal, Layers, Film, RotateCw, 
  AlertTriangle, CheckCircle2, Clock, Flame
} from 'lucide-react';
import { Job, Clip, ProcessingLog } from '../types';
import { fetchJobLogs, retryJob, cancelJob } from '../api';

interface JobDetailModalProps {
  job: Job | null;
  onClose: () => void;
  onPlayClip: (clip: Clip) => void;
  onRefreshJob: () => void;
}

export const JobDetailModal: React.FC<JobDetailModalProps> = ({
  job,
  onClose,
  onPlayClip,
  onRefreshJob
}) => {
  const [activeTab, setActiveTab] = useState<'clips' | 'logs' | 'chunks'>('clips');
  const [logs, setLogs] = useState<ProcessingLog[]>([]);
  const [loadingLogs, setLoadingLogs] = useState(false);

  useEffect(() => {
    if (job && activeTab === 'logs') {
      loadLogs();
      const interval = setInterval(loadLogs, 4000);
      return () => clearInterval(interval);
    }
  }, [job?.id, activeTab]);

  const loadLogs = async () => {
    if (!job) return;
    try {
      setLoadingLogs(true);
      const data = await fetchJobLogs(job.id);
      setLogs(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingLogs(false);
    }
  };

  if (!job) return null;

  const isProcessing = ['DOWNLOADING', 'TRANSCRIBING', 'ANALYZING', 'RENDERING'].includes(job.status);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/85 backdrop-blur-md animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-4xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-bold text-white text-lg">{job.project_name}</h2>
              <span className="text-xs px-2 py-0.5 rounded-full font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                {job.status}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Job ID: <code className="text-slate-300">{job.id}</code>
            </p>
          </div>
          <div className="flex items-center gap-2">
            {job.clips.length > 0 && (
              <a
                href={`/api/jobs/${job.id}/download-all`}
                download
                className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-semibold text-xs rounded-lg shadow-sm transition active:scale-95"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download All ({job.clips.length} Clips ZIP)</span>
              </a>
            )}
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Tab Bar */}
        <div className="flex border-b border-slate-800 bg-slate-950/40 px-6">
          <button
            onClick={() => setActiveTab('clips')}
            className={`py-3 px-4 text-xs font-semibold flex items-center gap-2 border-b-2 transition ${
              activeTab === 'clips'
                ? 'border-emerald-500 text-emerald-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Film className="w-4 h-4" />
            <span>Generated Clips ({job.clips.length})</span>
          </button>
          <button
            onClick={() => setActiveTab('chunks')}
            className={`py-3 px-4 text-xs font-semibold flex items-center gap-2 border-b-2 transition ${
              activeTab === 'chunks'
                ? 'border-emerald-500 text-emerald-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>Resilient Chunks ({job.completed_chunks}/{job.total_chunks || '-'})</span>
          </button>
          <button
            onClick={() => setActiveTab('logs')}
            className={`py-3 px-4 text-xs font-semibold flex items-center gap-2 border-b-2 transition ${
              activeTab === 'logs'
                ? 'border-emerald-500 text-emerald-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Terminal className="w-4 h-4" />
            <span>Processing Logs</span>
          </button>
        </div>

        {/* Tab Contents */}
        <div className="p-6 overflow-y-auto flex-1">
          {activeTab === 'clips' && (
            <div>
              {job.clips.length === 0 ? (
                <div className="text-center py-12">
                  <Film className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                  <h4 className="text-sm font-semibold text-slate-300">No clips ready yet</h4>
                  <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1">
                    {isProcessing
                      ? `Currently in stage: ${job.current_stage}. Clips will appear here as each 120s chunk completes.`
                      : 'Clips will be generated when a Colab GPU worker processes this video.'}
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {job.clips.map((clip, idx) => (
                    <div
                      key={clip.id}
                      className="bg-slate-950 border border-slate-800 rounded-xl overflow-hidden hover:border-slate-700 transition flex flex-col justify-between"
                    >
                      <div className="p-4">
                        <div className="flex items-center justify-between text-xs mb-2">
                          <span className="font-semibold text-slate-400">Clip #{idx + 1}</span>
                          <span className="flex items-center gap-1 font-bold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                            <Flame className="w-3 h-3 fill-current" />
                            <span>{Math.round(clip.score)}</span>
                          </span>
                        </div>
                        <h4 className="font-semibold text-white text-sm line-clamp-2 mb-2">
                          {clip.title}
                        </h4>
                        {clip.transcript_snippet && (
                          <p className="text-xs text-slate-400 line-clamp-3 italic bg-slate-900/60 p-2 rounded-lg border border-slate-800/60">
                            "{clip.transcript_snippet}"
                          </p>
                        )}
                      </div>

                      <div className="p-3 bg-slate-900/80 border-t border-slate-800/80 flex items-center gap-2">
                        <button
                          onClick={() => onPlayClip(clip)}
                          className="flex-1 flex items-center justify-center gap-1.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg transition"
                        >
                          <Play className="w-3.5 h-3.5 fill-current" />
                          <span>Preview</span>
                        </button>
                        <a
                          href={clip.download_url}
                          download
                          className="p-1.5 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 border border-emerald-500/30 rounded-lg transition"
                          title="Download Clip MP4"
                        >
                          <Download className="w-4 h-4" />
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'chunks' && (
            <div className="space-y-4">
              <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl">
                <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                  Resumable Checkpoints Architecture
                </h4>
                <p className="text-xs text-slate-400 leading-relaxed">
                  ClipForge divides your video into 120-second chunks. Each chunk is processed independently and checkpointed. If the free Colab worker drops connection, it automatically resumes right at the first incomplete chunk without duplicating already generated clips.
                </p>
              </div>

              <div className="border border-slate-800 rounded-xl overflow-hidden bg-slate-950">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-900 text-slate-400 border-b border-slate-800">
                    <tr>
                      <th className="p-3">Chunk Index</th>
                      <th className="p-3">Time Range</th>
                      <th className="p-3">Status</th>
                      <th className="p-3">Checkpoint Recovery</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/80 text-slate-300">
                    {Array.from({ length: job.total_chunks || 1 }).map((_, i) => {
                      const isDone = i < job.completed_chunks;
                      return (
                        <tr key={i} className="hover:bg-slate-900/40">
                          <td className="p-3 font-semibold">Chunk #{i + 1}</td>
                          <td className="p-3 text-slate-400">{i * 120}s — {(i + 1) * 120}s</td>
                          <td className="p-3">
                            {isDone ? (
                              <span className="inline-flex items-center gap-1 text-emerald-400 font-medium">
                                <CheckCircle2 className="w-3.5 h-3.5" />
                                <span>Completed</span>
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-slate-500">
                                <Clock className="w-3.5 h-3.5" />
                                <span>Pending</span>
                              </span>
                            )}
                          </td>
                          <td className="p-3 text-slate-400">
                            {isDone ? 'Saved in DB & Storage' : 'Eligible for Worker'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeTab === 'logs' && (
            <div className="bg-slate-950 font-mono text-xs rounded-xl p-4 border border-slate-800 h-96 overflow-y-auto space-y-1.5">
              {logs.length === 0 ? (
                <div className="text-slate-500 italic py-8 text-center">
                  {loadingLogs ? 'Loading logs...' : 'No logs recorded yet. Start your Colab worker to begin.'}
                </div>
              ) : (
                logs.map((log) => (
                  <div key={log.id} className="leading-relaxed flex items-start gap-2">
                    <span className="text-slate-600 shrink-0">
                      [{new Date(log.created_at).toLocaleTimeString()}]
                    </span>
                    <span
                      className={`shrink-0 font-bold ${
                        log.level === 'ERROR'
                          ? 'text-red-400'
                          : log.level === 'WARNING'
                          ? 'text-amber-400'
                          : 'text-emerald-400'
                      }`}
                    >
                      [{log.level}]
                    </span>
                    <span className="text-slate-300">{log.message}</span>
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-800 bg-slate-950 flex items-center justify-between text-xs text-slate-400">
          <div>
            <span>Worker: </span>
            <code className="text-slate-300">{job.worker_id || 'None (Queueing)'}</code>
          </div>
          <div className="flex items-center gap-2">
            {job.status === 'FAILED' && (
              <button
                onClick={async () => { await retryJob(job.id); onRefreshJob(); }}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-emerald-400 font-semibold rounded-lg transition"
              >
                <RotateCw className="w-3.5 h-3.5" />
                <span>Retry Job</span>
              </button>
            )}
            {isProcessing && (
              <button
                onClick={async () => { await cancelJob(job.id); onRefreshJob(); }}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-red-950/60 border border-red-800 hover:bg-red-900/60 text-red-300 font-semibold rounded-lg transition"
              >
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>Cancel Job</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
