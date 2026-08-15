"use client";

import { useEffect, useState, type ReactNode } from "react";
import { toast } from "sonner";
import { AlertCircle, CheckCircle2, RefreshCw, Settings2, Unlink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ApiError } from "@/services/api-client";
import { SyncProgress } from "@/components/sources/sync-progress";
import type { ConnectionStatus, KnowledgeSource, SyncJob } from "@/types/sources";

export interface SourceCardConfig {
  icon: ReactNode;
  title: string;
  description: string;
  authorizeUrl: string;
  itemLabelPlural: string;
  fetchStatus: () => Promise<ConnectionStatus>;
  startSync: () => Promise<SyncJob>;
  disconnect: () => Promise<void>;
  renderPicker: (props: {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    existingSources: KnowledgeSource[];
    onSaved: (sources: KnowledgeSource[]) => void;
  }) => ReactNode;
}

function relativeTime(iso: string | null) {
  if (!iso) return "Never";
  const diffMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.round(diffMs / 60000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export function SourceCard({ config }: { config: SourceCardConfig }) {
  const [status, setStatus] = useState<ConnectionStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [isStartingSync, setIsStartingSync] = useState(false);
  const [isDisconnecting, setIsDisconnecting] = useState(false);

  async function load() {
    try {
      const data = await config.fetchStatus();
      setStatus(data);
      setActiveJobId(data.active_sync_job_id);
    } catch {
      // status fetch failing shouldn't break the page — card just stays in loading/empty state
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSync() {
    setIsStartingSync(true);
    try {
      const job = await config.startSync();
      setActiveJobId(job.id);
      toast.success("Sync started");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not start sync.");
    } finally {
      setIsStartingSync(false);
    }
  }

  async function handleDisconnect() {
    setIsDisconnecting(true);
    try {
      await config.disconnect();
      toast.success(`${config.title} disconnected`);
      await load();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not disconnect.");
    } finally {
      setIsDisconnecting(false);
    }
  }

  const totalDocs = status?.sources.reduce((sum, s) => sum + s.document_count, 0) ?? 0;
  const lastSync = status?.sources
    .map((s) => s.last_synced_at)
    .filter((v): v is string => Boolean(v))
    .sort()
    .at(-1);

  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-foreground">
            {config.icon}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold">{config.title}</h3>
              {isLoading ? null : status?.connected ? (
                <Badge variant="secondary" className="gap-1 text-emerald-700 dark:text-emerald-400">
                  <CheckCircle2 className="size-3" />
                  Connected
                </Badge>
              ) : (
                <Badge variant="outline" className="text-muted-foreground">
                  Not connected
                </Badge>
              )}
            </div>
            <p className="mt-1 text-sm text-muted-foreground">{config.description}</p>
          </div>
        </div>
      </div>

      {status?.last_error && (
        <div className="mt-3 flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
          <AlertCircle className="mt-0.5 size-4 shrink-0" />
          <span>{status.last_error}</span>
        </div>
      )}

      {status?.connected && (
        <div className="mt-4 space-y-3">
          {status.account_label && (
            <p className="text-xs text-muted-foreground">Connected as {status.account_label}</p>
          )}

          {status.sources.length > 0 ? (
            <div className="rounded-lg border border-border">
              <div className="flex items-center justify-between border-b border-border px-3 py-2 text-xs text-muted-foreground">
                <span>
                  {status.sources.length} {config.itemLabelPlural} · {totalDocs} documents
                </span>
                <span>Last synced {relativeTime(lastSync ?? null)}</span>
              </div>
              <ul className="max-h-32 divide-y divide-border overflow-y-auto">
                {status.sources.map((s) => (
                  <li key={s.id} className="flex items-center justify-between px-3 py-1.5 text-sm">
                    <span className="truncate">{s.path ?? s.name}</span>
                    <span className="shrink-0 text-xs text-muted-foreground">{s.document_count}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              No {config.itemLabelPlural} selected yet.
            </p>
          )}

          {activeJobId && (
            <SyncProgress
              jobId={activeJobId}
              onSettled={(job) => {
                setActiveJobId(null);
                if (job.status === "success") toast.success("Sync complete");
                else if (job.status === "partial") toast.warning("Some items could not be processed.");
                load();
              }}
            />
          )}

          <div className="flex flex-wrap gap-2 pt-1">
            <Button
              size="sm"
              variant="outline"
              onClick={handleSync}
              disabled={Boolean(activeJobId) || isStartingSync || status.sources.length === 0}
            >
              <RefreshCw className="size-3.5" />
              Sync now
            </Button>
            <Button size="sm" variant="outline" onClick={() => setPickerOpen(true)}>
              <Settings2 className="size-3.5" />
              Manage {config.itemLabelPlural}
            </Button>
            <Button size="sm" variant="ghost" onClick={handleDisconnect} disabled={isDisconnecting}>
              <Unlink className="size-3.5" />
              Disconnect
            </Button>
          </div>
        </div>
      )}

      {!isLoading && !status?.connected && (
        <div className="mt-4">
          {status?.configured ? (
            <Button size="sm" nativeButton={false} render={<a href={config.authorizeUrl} />}>
              Connect
            </Button>
          ) : (
            <Badge variant="outline" className="text-muted-foreground">
              Not available in this environment
            </Badge>
          )}
        </div>
      )}

      {config.renderPicker({
        open: pickerOpen,
        onOpenChange: setPickerOpen,
        existingSources: status?.sources ?? [],
        onSaved: (sources) => setStatus((prev) => (prev ? { ...prev, sources } : prev)),
      })}
    </div>
  );
}
