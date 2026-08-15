import { apiClient } from "@/services/api-client";
import type { ConnectionStatus, DriveFolder, KnowledgeSource, SlackChannel, SyncJob } from "@/types/sources";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const sourcesService = {
  googleDriveAuthorizeUrl: () => `${API_URL}/api/sources/google-drive/authorize`,
  slackAuthorizeUrl: () => `${API_URL}/api/sources/slack/authorize`,

  getGoogleDriveStatus: () => apiClient.get<ConnectionStatus>("/api/sources/google-drive"),
  listDriveFolders: (parentId: string) =>
    apiClient.get<DriveFolder[]>(`/api/sources/google-drive/folders?parent_id=${encodeURIComponent(parentId)}`),
  selectDriveFolders: (folders: { id: string; name: string; path: string }[]) =>
    apiClient.post<KnowledgeSource[]>("/api/sources/google-drive/folders", { folders }),
  startDriveSync: () => apiClient.post<SyncJob>("/api/sources/google-drive/sync"),
  disconnectGoogleDrive: () => apiClient.delete<void>("/api/sources/google-drive"),

  getSlackStatus: () => apiClient.get<ConnectionStatus>("/api/sources/slack"),
  listSlackChannels: () => apiClient.get<SlackChannel[]>("/api/sources/slack/channels"),
  selectSlackChannels: (channels: { id: string; name: string }[]) =>
    apiClient.post<KnowledgeSource[]>("/api/sources/slack/channels", { channels }),
  startSlackSync: () => apiClient.post<SyncJob>("/api/sources/slack/sync"),
  disconnectSlack: () => apiClient.delete<void>("/api/sources/slack"),

  getSyncJob: (jobId: string) => apiClient.get<SyncJob>(`/api/sync-jobs/${jobId}`),
};
