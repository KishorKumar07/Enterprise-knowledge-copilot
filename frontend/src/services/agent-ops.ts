import { apiClient } from "@/services/api-client";
import type { AgentOpsStats, AgentRun, AgentRunDetail } from "@/types/agent-ops";

export const agentOpsService = {
  listRuns: (limit = 50, offset = 0) =>
    apiClient.get<AgentRun[]>(`/api/admin/agent-runs?limit=${limit}&offset=${offset}`),
  getRun: (runId: string) => apiClient.get<AgentRunDetail>(`/api/admin/agent-runs/${runId}`),
  getStats: (windowMinutes = 60) =>
    apiClient.get<AgentOpsStats>(`/api/admin/agent-runs/stats?window_minutes=${windowMinutes}`),
};
