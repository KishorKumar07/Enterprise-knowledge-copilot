export interface KnowledgeSource {
  id: string;
  external_id: string;
  name: string;
  path: string | null;
  document_count: number;
  last_synced_at: string | null;
}

export interface ConnectionStatus {
  connected: boolean;
  configured: boolean;
  status: string | null;
  account_label: string | null;
  last_error: string | null;
  sources: KnowledgeSource[];
  active_sync_job_id: string | null;
}

export interface DriveFolder {
  id: string;
  name: string;
  parent_id: string | null;
}

export interface SlackChannel {
  id: string;
  name: string;
  is_private: boolean;
}

export interface SyncJob {
  id: string;
  provider: string;
  status: "queued" | "running" | "success" | "failed" | "partial";
  total_items: number;
  processed_items: number;
  progress_percent: number;
  current_item: string | null;
  error: string | null;
  started_at: string;
  completed_at: string | null;
}
