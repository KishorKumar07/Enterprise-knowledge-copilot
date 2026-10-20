"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { AlertTriangle, ExternalLink, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { agentOpsService } from "@/services/agent-ops";
import type { AgentOpsStats, AgentRun, AgentRunDetail, AgentRunStatus } from "@/types/agent-ops";

// These open in the viewer's browser, so "localhost" would mean *their* machine,
// not the server — the links were dead once deployed. NEXT_PUBLIC_* values are
// inlined at build time, so these come in as build args (see frontend/Dockerfile);
// the fallbacks keep local dev working with no env file.
const GRAFANA_URL = process.env.NEXT_PUBLIC_GRAFANA_URL ?? "http://localhost:3001";
const PHOENIX_URL = process.env.NEXT_PUBLIC_PHOENIX_URL ?? "http://localhost:6006";

const STATUS_VARIANT: Record<AgentRunStatus, "secondary" | "destructive" | "outline"> = {
  completed: "secondary",
  error: "destructive",
  running: "outline",
};

function formatLatency(ms: number | null): string {
  if (ms === null) return "—";
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(2)}s`;
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export default function AgentOpsPage() {
  const [stats, setStats] = useState<AgentOpsStats | null>(null);
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedRun, setSelectedRun] = useState<AgentRunDetail | null>(null);
  const [isLoadingRun, setIsLoadingRun] = useState(false);

  const load = useCallback(async () => {
    setIsLoading(true);
    try {
      const [statsResult, runsResult] = await Promise.all([
        agentOpsService.getStats(60),
        agentOpsService.listRuns(50),
      ]);
      setStats(statsResult);
      setRuns(runsResult);
    } catch {
      toast.error("Could not load agent run history.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const openRun = async (runId: string) => {
    setIsLoadingRun(true);
    try {
      setSelectedRun(await agentOpsService.getRun(runId));
    } catch {
      toast.error("Could not load run detail.");
    } finally {
      setIsLoadingRun(false);
    }
  };

  return (
    <div className="mx-auto max-w-4xl px-6 py-8 lg:px-10">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Agent Ops</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Every LangGraph run for this workspace — the durable audit trail behind the trace and
            metrics dashboards.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={isLoading}>
          <RefreshCw className={`size-4 ${isLoading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <Button variant="outline" size="sm" render={<a href={PHOENIX_URL} target="_blank" rel="noreferrer" />}>
          Open Phoenix traces <ExternalLink className="size-3.5" />
        </Button>
        <Button variant="outline" size="sm" render={<a href={GRAFANA_URL} target="_blank" rel="noreferrer" />}>
          Open Grafana dashboards <ExternalLink className="size-3.5" />
        </Button>
      </div>

      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard label="Runs (60m)" value={stats?.total_runs.toString() ?? null} loading={isLoading} />
        <StatCard
          label="Error rate"
          value={stats ? `${(stats.error_rate * 100).toFixed(1)}%` : null}
          loading={isLoading}
          warn={!!stats && stats.error_rate > 0.1}
        />
        <StatCard label="Avg latency" value={stats ? formatLatency(stats.avg_latency_ms) : null} loading={isLoading} />
        <StatCard label="P95 latency" value={stats ? formatLatency(stats.p95_latency_ms) : null} loading={isLoading} />
      </div>

      <section className="mt-8">
        <h2 className="text-sm font-semibold">Recent runs</h2>
        <div className="mt-3 divide-y divide-border rounded-xl border border-border bg-card">
          {isLoading &&
            Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="m-3 h-12 rounded-lg" />)}

          {!isLoading && runs.length === 0 && (
            <p className="px-5 py-8 text-center text-sm text-muted-foreground">
              No agent runs yet — send a chat message to generate one.
            </p>
          )}

          {!isLoading &&
            runs.map((run) => (
              <button
                key={run.id}
                onClick={() => openRun(run.id)}
                className="flex w-full items-center justify-between gap-4 px-5 py-3 text-left hover:bg-accent/30"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm">{run.query}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">{formatTime(run.started_at)}</p>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <span className="text-xs text-muted-foreground">{formatLatency(run.latency_ms)}</span>
                  <Badge variant={STATUS_VARIANT[run.status]}>{run.status}</Badge>
                </div>
              </button>
            ))}
        </div>
      </section>

      <Dialog open={!!selectedRun || isLoadingRun} onOpenChange={(open) => !open && setSelectedRun(null)}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Run detail</DialogTitle>
          </DialogHeader>
          {isLoadingRun && <Skeleton className="h-40 rounded-lg" />}
          {selectedRun && !isLoadingRun && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">{selectedRun.query}</p>
              {selectedRun.error && (
                <div className="flex items-start gap-2 rounded-lg bg-destructive/10 px-3 py-2 text-xs text-destructive">
                  <AlertTriangle className="mt-0.5 size-3.5 shrink-0" />
                  <span>{selectedRun.error}</span>
                </div>
              )}
              <div className="divide-y divide-border rounded-lg border border-border">
                {selectedRun.steps.map((step) => (
                  <div key={step.id} className="flex items-center justify-between px-3 py-2 text-sm">
                    <span className="font-medium">{step.node_name}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">{formatLatency(step.latency_ms)}</span>
                      <Badge variant={step.status === "error" ? "destructive" : "secondary"}>{step.status}</Badge>
                    </div>
                  </div>
                ))}
                {selectedRun.steps.length === 0 && (
                  <p className="px-3 py-4 text-center text-xs text-muted-foreground">No step data recorded.</p>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function StatCard({
  label,
  value,
  loading,
  warn,
}: {
  label: string;
  value: string | null;
  loading: boolean;
  warn?: boolean;
}) {
  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle className="text-xs font-normal text-muted-foreground">{label}</CardTitle>
      </CardHeader>
      <CardContent>
        {loading || value === null ? (
          <Skeleton className="h-6 w-16" />
        ) : (
          <p className={`text-xl font-semibold tabular-nums ${warn ? "text-destructive" : ""}`}>{value}</p>
        )}
      </CardContent>
    </Card>
  );
}
