export type AgentRunStatus = "running" | "completed" | "error";
export type AgentStepStatus = "success" | "error";

export interface AgentStep {
  id: string;
  node_name: string;
  status: AgentStepStatus;
  latency_ms: number;
  error: string | null;
  started_at: string;
}

export interface AgentRun {
  id: string;
  conversation_id: string;
  query: string;
  status: AgentRunStatus;
  error: string | null;
  latency_ms: number | null;
  started_at: string;
  finished_at: string | null;
}

export interface AgentRunDetail extends AgentRun {
  steps: AgentStep[];
}

export interface AgentOpsStats {
  window_minutes: number;
  total_runs: number;
  error_count: number;
  error_rate: number;
  avg_latency_ms: number | null;
  p95_latency_ms: number | null;
}
