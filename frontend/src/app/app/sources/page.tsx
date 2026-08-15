"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { HardDrive, Hash } from "lucide-react";
import { SourceCard } from "@/components/sources/source-card";
import { FolderPickerDialog } from "@/components/sources/folder-picker-dialog";
import { ChannelPickerDialog } from "@/components/sources/channel-picker-dialog";
import { sourcesService } from "@/services/sources";

const CALLBACK_MESSAGES: Record<string, { type: "success" | "error"; text: string }> = {
  connected: { type: "success", text: "Connected successfully" },
  denied: { type: "error", text: "Authorization was cancelled" },
  error: { type: "error", text: "Something went wrong while connecting. Please try again." },
};

export default function SourcesPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const googleDrive = searchParams.get("google_drive");
    const slack = searchParams.get("slack");
    const result = googleDrive ?? slack;
    const provider = googleDrive ? "Google Drive" : "Slack";

    if (result && CALLBACK_MESSAGES[result]) {
      const { type, text } = CALLBACK_MESSAGES[result];
      if (type === "success") toast.success(`${provider}: ${text}`);
      else toast.error(`${provider}: ${text}`);
      router.replace("/app/sources");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  return (
    <div className="mx-auto max-w-3xl px-6 py-8 lg:px-10">
      <h1 className="text-2xl font-semibold tracking-tight">Sources</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Connect Google Drive and Slack, then choose exactly what gets indexed.
      </p>

      <div className="mt-6 space-y-4">
        <SourceCard
          config={{
            icon: <HardDrive className="size-5" />,
            title: "Google Drive",
            description: "Index selected folders — docs, sheets, and slides become searchable evidence.",
            authorizeUrl: sourcesService.googleDriveAuthorizeUrl(),
            itemLabelPlural: "folders",
            fetchStatus: sourcesService.getGoogleDriveStatus,
            startSync: sourcesService.startDriveSync,
            disconnect: sourcesService.disconnectGoogleDrive,
            renderPicker: (props) => <FolderPickerDialog {...props} />,
          }}
        />

        <SourceCard
          config={{
            icon: <Hash className="size-5" />,
            title: "Slack",
            description: "Index selected channels so conversations and decisions are searchable too.",
            authorizeUrl: sourcesService.slackAuthorizeUrl(),
            itemLabelPlural: "channels",
            fetchStatus: sourcesService.getSlackStatus,
            startSync: sourcesService.startSlackSync,
            disconnect: sourcesService.disconnectSlack,
            renderPicker: (props) => <ChannelPickerDialog {...props} />,
          }}
        />
      </div>
    </div>
  );
}
