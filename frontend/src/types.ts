export type JobStatus = 
  | 'QUEUED' 
  | 'DOWNLOADING' 
  | 'TRANSCRIBING' 
  | 'ANALYZING' 
  | 'RENDERING' 
  | 'COMPLETED' 
  | 'FAILED' 
  | 'CANCELLED' 
  | 'PAUSED';

export interface Clip {
  id: string;
  job_id: string;
  chunk_id?: string;
  title: string;
  start_time: number;
  end_time: number;
  duration: number;
  score: number;
  transcript_snippet?: string;
  file_path: string;
  file_size: number;
  aspect_ratio: string;
  download_url: string;
  created_at: string;
}

export interface JobChunk {
  id: string;
  job_id: string;
  chunk_index: number;
  start_time: number;
  end_time: number;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  checkpoint_data?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface ProcessingLog {
  id: string;
  job_id: string;
  worker_id?: string;
  level: 'INFO' | 'WARNING' | 'ERROR';
  message: string;
  created_at: string;
}

export interface Job {
  id: string;
  project_id: string;
  project_name: string;
  source_type: 'youtube' | 'upload';
  source_url?: string;
  status: JobStatus;
  current_stage: string;
  progress: number;
  total_chunks: number;
  completed_chunks: number;
  worker_id?: string;
  lease_expires_at?: string;
  retry_count: number;
  max_retries: number;
  error_details?: string;
  created_at: string;
  updated_at: string;
  clips: Clip[];
}

export interface WorkerStatus {
  worker_id: string;
  hostname?: string;
  device_type: 'cuda' | 'cpu';
  last_heartbeat: string;
  current_job_id?: string;
  status: 'ONLINE' | 'BUSY' | 'OFFLINE';
  is_active: boolean;
}

export interface SystemStatus {
  total_jobs: number;
  active_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  workers_online: number;
  workers: WorkerStatus[];
}
