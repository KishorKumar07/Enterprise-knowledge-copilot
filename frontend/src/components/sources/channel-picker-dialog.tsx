"use client";

import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Hash, Loader2, Lock } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { sourcesService } from "@/services/sources";
import { ApiError } from "@/services/api-client";
import type { KnowledgeSource, SlackChannel } from "@/types/sources";

export function ChannelPickerDialog({
  open,
  onOpenChange,
  existingSources,
  onSaved,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  existingSources: KnowledgeSource[];
  onSaved: (sources: KnowledgeSource[]) => void;
}) {
  const [channels, setChannels] = useState<SlackChannel[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Map<string, string>>(new Map());
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setSelected(new Map(existingSources.map((s) => [s.external_id, s.name])));
    setSearch("");
    setIsLoading(true);
    sourcesService
      .listSlackChannels()
      .then(setChannels)
      .catch((err) => {
        toast.error(err instanceof ApiError ? err.message : "Could not load Slack channels.");
        setChannels([]);
      })
      .finally(() => setIsLoading(false));
  }, [open, existingSources]);

  const filtered = useMemo(
    () => channels.filter((c) => c.name.toLowerCase().includes(search.toLowerCase())),
    [channels, search]
  );

  function toggle(channel: SlackChannel) {
    setSelected((prev) => {
      const next = new Map(prev);
      if (next.has(channel.id)) {
        next.delete(channel.id);
      } else {
        next.set(channel.id, channel.name);
      }
      return next;
    });
  }

  async function handleSave() {
    setIsSaving(true);
    try {
      const channelsPayload = Array.from(selected.entries()).map(([id, name]) => ({ id, name }));
      const sources = await sourcesService.selectSlackChannels(channelsPayload);
      onSaved(sources);
      toast.success("Channel selection saved");
      onOpenChange(false);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not save channel selection.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Choose Slack channels</DialogTitle>
          <DialogDescription>
            Only messages in the channels you select will be indexed. The bot must be invited to
            private channels first.
          </DialogDescription>
        </DialogHeader>

        <Input placeholder="Search channels…" value={search} onChange={(e) => setSearch(e.target.value)} />

        <ScrollArea className="h-64 rounded-md border border-border">
          {isLoading ? (
            <div className="flex h-full items-center justify-center py-16">
              <Loader2 className="size-5 animate-spin text-muted-foreground" />
            </div>
          ) : filtered.length === 0 ? (
            <p className="p-6 text-center text-sm text-muted-foreground">No channels found.</p>
          ) : (
            <ul className="divide-y divide-border">
              {filtered.map((channel) => (
                <li key={channel.id} className="flex items-center gap-2 px-3 py-2 hover:bg-muted/50">
                  <Checkbox
                    checked={selected.has(channel.id)}
                    onCheckedChange={() => toggle(channel)}
                    aria-label={`Select #${channel.name}`}
                  />
                  {channel.is_private ? (
                    <Lock className="size-4 shrink-0 text-muted-foreground" />
                  ) : (
                    <Hash className="size-4 shrink-0 text-muted-foreground" />
                  )}
                  <span className="flex-1 truncate text-sm">{channel.name}</span>
                </li>
              ))}
            </ul>
          )}
        </ScrollArea>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={isSaving}>
            {isSaving ? "Saving…" : "Save selection"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
