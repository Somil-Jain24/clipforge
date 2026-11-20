import { useState, useEffect } from 'react';
import { 
  Film, Scissors, Clock, Search, Plus, Cpu
} from 'lucide-react';
import { Header } from './components/Header';
import { WorkerStatusBanner } from './components/WorkerStatusBanner';
import { JobCard } from './components/JobCard';
import { NewProjectModal } from './components/NewProjectModal';
import { JobDetailModal } from './components/JobDetailModal';
import { ClipPlayerModal } from './components/ClipPlayerModal';
import { Job, Clip, SystemStatus } from './types';
import { 
  fetchJobs, fetchSystemStatus, retryJob, cancelJob, 
  pauseJob, resumeJob, deleteJob
} from './api';

export function App() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [selectedFilter, setSelectedFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Modals state
  const [isNewModalOpen, setIsNewModalOpen] = useState(false);
  const [detailJob, setDetailJob] = useState<Job | null>(null);
  const [previewClip, setPreviewClip] = useState<Clip | null>(null);

  const loadData = async () => {
    try {
      setIsRefreshing(true);
      const [jobsData, statusData] = await Promise.all([
        fetchJobs(),
        fetchSystemStatus()
      ]);
      setJobs(jobsData);
      setSystemStatus(statusData);

      // If detail modal is open, refresh its data too
      if (detailJob) {
        const updated = jobsData.find((j) => j.id === detailJob.id);
        if (updated) setDetailJob(updated);
      }
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleRetry = async (jobId: string) => {
    await retryJob(jobId);
    loadData();
  };

  const handleCancel = async (jobId: string) => {
    await cancelJob(jobId);
    loadData();
  };

  const handlePause = async (jobId: string) => {
    await pauseJob(jobId);
    loadData();
  };

  const handleResume = async (jobId: string) => {
    await resumeJob(jobId);
    loadData();
  };

  const handleDelete = async (jobId: string) => {
    if (confirm('Are you sure you want to delete this job and all its clips?')) {
      await deleteJob(jobId);
      if (detailJob?.id === jobId) setDetailJob(null);
      loadData();
    }
  };

  const filteredJobs = jobs.filter((job) => {
    if (selectedFilter === 'ACTIVE') {
      if (!['DOWNLOADING', 'TRANSCRIBING', 'ANALYZING', 'RENDERING', 'QUEUED'].includes(job.status)) {
        return false;
      }
    } else if (selectedFilter === 'COMPLETED') {
      if (job.status !== 'COMPLETED') return false;
    } else if (selectedFilter === 'FAILED') {
      if (job.status !== 'FAILED') return false;
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return (
        job.project_name.toLowerCase().includes(q) ||
        (job.source_url && job.source_url.toLowerCase().includes(q))
      );
    }
    return true;
  });

  const totalClips = jobs.reduce((acc, j) => acc + (j.clips?.length || 0), 0);

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col font-sans">
      <Header
        systemStatus={systemStatus}
        onNewProject={() => setIsNewModalOpen(true)}
        onRefresh={loadData}
        isRefreshing={isRefreshing}
      />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 w-full space-y-6">
        {/* Worker Status Warning / Active Info */}
        <WorkerStatusBanner status={systemStatus} />

        {/* Stats Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400 font-medium">Total Projects</p>
              <h3 className="text-2xl font-bold text-white mt-1">{systemStatus?.total_jobs ?? jobs.length}</h3>
            </div>
            <div className="p-3 rounded-xl bg-slate-800 text-slate-300">
              <Scissors className="w-5 h-5" />
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400 font-medium">In Queue / Active</p>
              <h3 className="text-2xl font-bold text-sky-400 mt-1">{systemStatus?.active_jobs ?? 0}</h3>
            </div>
            <div className="p-3 rounded-xl bg-sky-500/10 text-sky-400">
              <Clock className="w-5 h-5" />
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400 font-medium">Finished Shorts</p>
              <h3 className="text-2xl font-bold text-emerald-400 mt-1">{totalClips}</h3>
            </div>
            <div className="p-3 rounded-xl bg-emerald-500/10 text-emerald-400">
              <Film className="w-5 h-5" />
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400 font-medium">GPU Workers</p>
              <h3 className="text-2xl font-bold text-emerald-400 mt-1">
                {systemStatus?.workers_online || 0}
              </h3>
            </div>
            <div className="p-3 rounded-xl bg-emerald-500/10 text-emerald-400">
              <Cpu className="w-5 h-5" />
            </div>
          </div>
        </div>

        {/* Controls: Search & Tabs */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-2">
          {/* Filter Pills */}
          <div className="flex items-center gap-1 bg-slate-900 border border-slate-800 p-1 rounded-xl">
            {['ALL', 'ACTIVE', 'COMPLETED', 'FAILED'].map((tab) => (
              <button
                key={tab}
                onClick={() => setSelectedFilter(tab)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  selectedFilter === tab
                    ? 'bg-slate-800 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {tab.charAt(0) + tab.slice(1).toLowerCase()}
              </button>
            ))}
          </div>

          {/* Search Bar */}
          <div className="relative w-full sm:w-72">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search projects..."
              className="w-full pl-9 pr-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
            />
          </div>
        </div>

        {/* Jobs List Grid */}
        {filteredJobs.length === 0 ? (
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-12 text-center">
            <Film className="w-12 h-12 text-slate-600 mx-auto mb-3" />
            <h3 className="text-sm font-semibold text-slate-300">No clipping jobs found</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 mb-5">
              Submit your first YouTube video or direct video upload to start generating viral vertical clips.
            </p>
            <button
              onClick={() => setIsNewModalOpen(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-semibold text-xs rounded-lg transition"
            >
              <Plus className="w-4 h-4" />
              <span>Create First Project</span>
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filteredJobs.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                onOpenDetails={(j) => setDetailJob(j)}
                onRetry={handleRetry}
                onCancel={handleCancel}
                onPause={handlePause}
                onResume={handleResume}
                onDelete={handleDelete}
              />
            ))}
          </div>
        )}
      </main>

      {/* Modals */}
      <NewProjectModal
        isOpen={isNewModalOpen}
        onClose={() => setIsNewModalOpen(false)}
        onProjectCreated={loadData}
      />

      <JobDetailModal
        job={detailJob}
        onClose={() => setDetailJob(null)}
        onPlayClip={(clip) => setPreviewClip(clip)}
        onRefreshJob={loadData}
      />

      <ClipPlayerModal
        clip={previewClip}
        onClose={() => setPreviewClip(null)}
      />
    </div>
  );
}

export default App;
