"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "motion/react";
import { AlertCircle, Loader2 } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { sourcesService } from "@/services/sources";
import type { SyncJob } from "@/types/sources";

const POLL_INTERVAL_MS = 1500;

export function SyncProgress({
  jobId,
  onSettled,
}: {
  jobId: string;
  onSettled: (job: SyncJob) => void;
}) {
  const [job, setJob] = useState<SyncJob | null>(null);
  const onSettledRef = useRef(onSettled);
  // Updated after render (not during it); declared before the polling effect so it is
  // current by the time a poll finishes.
  useEffect(() => {
    onSettledRef.current = onSettled;
  });

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;

    async function poll() {
      try {
        const latest = await sourcesService.getSyncJob(jobId);
        if (cancelled) return;
        setJob(latest);

        if (["success", "failed", "partial"].includes(latest.status)) {
          onSettledRef.current(latest);
          return;
        }
      } catch {
        // transient network hiccup — keep polling
      }
      timer = setTimeout(poll, POLL_INTERVAL_MS);
    }

    poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [jobId]);

  if (!job) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="size-4 animate-spin" />
        Starting sync…
      </div>
    );
  }

  if (job.status === "failed") {
    return (
      <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
        <AlertCircle className="mt-0.5 size-4 shrink-0" />
        <span>{job.error ?? "Sync failed. Please try again."}</span>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      transition={{ duration: 0.2 }}
      className="space-y-2 rounded-lg border border-border bg-muted/40 p-3"
    >
      <div className="flex items-center justify-between text-sm">
        <span className="flex items-center gap-1.5 font-medium">
          <Loader2 className="size-3.5 animate-spin" />
          Syncing…
        </span>
        <span className="text-muted-foreground">{job.progress_percent}%</span>
      </div>
      <Progress value={job.progress_percent} />
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>
          {job.processed_items} / {job.total_items || "?"} items
        </span>
        {job.current_item && <span className="max-w-48 truncate">{job.current_item}</span>}
      </div>
    </motion.div>
  );
}
