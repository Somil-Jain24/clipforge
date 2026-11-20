import React, { useState } from 'react';
import { X, Youtube, Upload, Video, AlertCircle, Loader2 } from 'lucide-react';
import { createYoutubeProject, uploadVideoFile } from '../api';

interface NewProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onProjectCreated: () => void;
}

export const NewProjectModal: React.FC<NewProjectModalProps> = ({
  isOpen,
  onClose,
  onProjectCreated
}) => {
  const [tab, setTab] = useState<'youtube' | 'upload'>('youtube');
  const [name, setName] = useState('');
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (tab === 'youtube') {
        if (!youtubeUrl.trim()) throw new Error('Please enter a YouTube video URL.');
        const projectName = name.trim() || 'YouTube Video Project';
        await createYoutubeProject(projectName, youtubeUrl.trim());
      } else {
        if (!selectedFile) throw new Error('Please select a video file to upload.');
        const projectName = name.trim() || selectedFile.name;
        await uploadVideoFile(selectedFile, projectName);
      }
      onProjectCreated();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to submit project');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
              <Video className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-semibold text-white">Create Clipping Project</h3>
              <p className="text-xs text-slate-400">Transform long video into 9:16 vertical shorts</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-800 bg-slate-950/40">
          <button
            type="button"
            onClick={() => { setTab('youtube'); setError(null); }}
            className={`flex-1 py-3 px-4 text-xs font-semibold flex items-center justify-center gap-2 border-b-2 transition ${
              tab === 'youtube'
                ? 'border-emerald-500 text-emerald-400 bg-slate-900/60'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Youtube className="w-4 h-4 text-red-500" />
            <span>YouTube URL</span>
          </button>
          <button
            type="button"
            onClick={() => { setTab('upload'); setError(null); }}
            className={`flex-1 py-3 px-4 text-xs font-semibold flex items-center justify-center gap-2 border-b-2 transition ${
              tab === 'upload'
                ? 'border-emerald-500 text-emerald-400 bg-slate-900/60'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Upload className="w-4 h-4 text-sky-400" />
            <span>Direct Video Upload</span>
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-950/40 border border-red-800 text-red-300 text-xs rounded-lg flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-red-400" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Project Title (Optional)
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Alex Hormozi Business Breakdown"
              className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition"
            />
          </div>

          {tab === 'youtube' ? (
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                YouTube URL <span className="text-red-400">*</span>
              </label>
              <input
                type="url"
                value={youtubeUrl}
                onChange={(e) => setYoutubeUrl(e.target.value)}
                placeholder="https://www.youtube.com/watch?v=..."
                required
                className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition"
              />
              <p className="text-[11px] text-slate-400 mt-1">
                Standard YouTube videos, podcasts, interviews, or livestreams.
              </p>
            </div>
          ) : (
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Video File <span className="text-red-400">*</span>
              </label>
              <div className="border-2 border-dashed border-slate-800 hover:border-slate-700 rounded-xl p-6 text-center bg-slate-950/50 cursor-pointer relative">
                <input
                  type="file"
                  accept="video/mp4,video/quicktime,video/x-matroska,video/webm"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  className="absolute inset-0 opacity-0 cursor-pointer"
                  required
                />
                <div className="flex flex-col items-center gap-2">
                  <div className="p-3 bg-slate-800/60 rounded-full text-slate-400">
                    <Upload className="w-6 h-6" />
                  </div>
                  <p className="text-xs text-slate-300 font-medium">
                    {selectedFile ? selectedFile.name : 'Click or drag video file here'}
                  </p>
                  <p className="text-[11px] text-slate-500">
                    MP4, MOV, MKV, or WEBM (Max 500 MB)
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Footer actions */}
          <div className="pt-2 flex items-center justify-end gap-3 border-t border-slate-800/80">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-2 px-5 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-slate-950 font-semibold text-xs rounded-lg shadow-md shadow-emerald-600/20 transition"
            >
              {loading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              <span>{loading ? 'Submitting...' : 'Queue Processing'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
