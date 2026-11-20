import React from 'react';
import { X, Download, Flame, Clock } from 'lucide-react';
import { Clip } from '../types';

interface ClipPlayerModalProps {
  clip: Clip | null;
  onClose: () => void;
}

export const ClipPlayerModal: React.FC<ClipPlayerModalProps> = ({ clip, onClose }) => {
  if (!clip) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/85 backdrop-blur-md animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <Flame className="w-3.5 h-3.5 fill-current" />
              <span>Score: {Math.round(clip.score)}</span>
            </span>
            <span className="flex items-center gap-1 text-xs text-slate-400">
              <Clock className="w-3.5 h-3.5" />
              <span>{Math.round(clip.duration)}s</span>
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Video Player (9:16 container) */}
        <div className="relative bg-black flex items-center justify-center aspect-[9/16] max-h-[500px] w-full mx-auto overflow-hidden">
          <video
            src={clip.download_url}
            controls
            autoPlay
            className="w-full h-full object-contain"
          />
        </div>

        {/* Content & Details */}
        <div className="p-4 space-y-3 bg-slate-900 overflow-y-auto">
          <h3 className="font-semibold text-white text-sm">{clip.title}</h3>
          {clip.transcript_snippet && (
            <div className="p-2.5 bg-slate-950/80 rounded-xl border border-slate-800/80">
              <span className="text-[10px] font-semibold uppercase text-slate-500 block mb-1">
                Transcript Hook
              </span>
              <p className="text-xs text-slate-300 italic leading-relaxed">
                "{clip.transcript_snippet}"
              </p>
            </div>
          )}

          <a
            href={clip.download_url}
            download
            className="w-full flex items-center justify-center gap-2 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-semibold text-xs rounded-xl shadow-md shadow-emerald-600/20 transition active:scale-98"
          >
            <Download className="w-4 h-4" />
            <span>Download 1080x1920 MP4</span>
          </a>
        </div>
      </div>
    </div>
  );
};
