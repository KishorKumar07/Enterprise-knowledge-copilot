"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { HardDrive, Hash, MessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { sourcesService } from "@/services/sources";
import type { ConnectionStatus } from "@/types/sources";

function SourceCard({
  icon,
  title,
  description,
  status,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  status: ConnectionStatus | null;
}) {
  const docCount = status?.sources.reduce((sum, s) => sum + s.document_count, 0) ?? 0;

  return (
    <div className="flex items-start gap-4 rounded-xl border border-border bg-card p-5">
      <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-foreground">
        {icon}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold">{title}</h3>
          <span
            className={
              "rounded-full border px-2 py-0.5 text-xs " +
              (status?.connected
                ? "border-emerald-600/30 text-emerald-700 dark:border-emerald-400/30 dark:text-emerald-400"
                : "border-border text-muted-foreground")
            }
          >
            {status?.connected ? "Connected" : "Not connected"}
          </span>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          {status?.connected ? `${status.sources.length} sources · ${docCount} documents` : description}
        </p>
        <Button
          variant="link"
          size="sm"
          className="mt-1 h-auto px-0"
          nativeButton={false}
          render={<Link href="/app/sources" />}
        >
          {status?.connected ? "Manage" : "Connect"}
        </Button>
      </div>
    </div>
  );
}

export function SourceOverview() {
  const [drive, setDrive] = useState<ConnectionStatus | null>(null);
  const [slack, setSlack] = useState<ConnectionStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    Promise.allSettled([sourcesService.getGoogleDriveStatus(), sourcesService.getSlackStatus()]).then(
      ([driveResult, slackResult]) => {
        if (driveResult.status === "fulfilled") setDrive(driveResult.value);
        if (slackResult.status === "fulfilled") setSlack(slackResult.value);
        setIsLoading(false);
      }
    );
  }, []);

  const anyConnected = drive?.connected || slack?.connected;

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Skeleton className="h-28 rounded-xl" />
        <Skeleton className="h-28 rounded-xl" />
      </div>
    );
  }

  return (
    <>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <SourceCard
          icon={<HardDrive className="size-5" />}
          title="Google Drive"
          description="Index selected folders — docs, sheets, and slides become searchable evidence."
          status={drive}
        />
        <SourceCard
          icon={<Hash className="size-5" />}
          title="Slack"
          description="Index selected channels so conversations and decisions are searchable too."
          status={slack}
        />
      </div>

      {!anyConnected && (
        <div className="mt-10 flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card/50 px-6 py-16 text-center">
          <div className="mb-4 flex size-12 items-center justify-center rounded-full bg-accent text-accent-foreground">
            <MessageSquare className="size-6" />
          </div>
          <h2 className="text-base font-semibold">No knowledge sources connected yet</h2>
          <p className="mt-1 max-w-sm text-sm text-muted-foreground">
            Once you connect Google Drive or Slack and sync some content, you&apos;ll be able to
            chat with your knowledge base here.
          </p>
          <Button className="mt-6" nativeButton={false} render={<Link href="/app/sources" />}>
            Connect a source
          </Button>
        </div>
      )}
    </>
  );
}
