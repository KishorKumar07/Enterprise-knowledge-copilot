"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { ChevronRight, Folder, FolderOpen, Loader2, X } from "lucide-react";
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
import { ScrollArea } from "@/components/ui/scroll-area";
import { sourcesService } from "@/services/sources";
import { ApiError } from "@/services/api-client";
import type { DriveFolder, KnowledgeSource } from "@/types/sources";

interface Crumb {
  id: string;
  name: string;
}

interface SelectedFolder {
  id: string;
  name: string;
  path: string;
}

export function FolderPickerDialog({
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
  const [crumbs, setCrumbs] = useState<Crumb[]>([{ id: "root", name: "My Drive" }]);
  const [folders, setFolders] = useState<DriveFolder[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selected, setSelected] = useState<Map<string, SelectedFolder>>(new Map());
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setCrumbs([{ id: "root", name: "My Drive" }]);
    setSelected(
      new Map(
        existingSources.map((s) => [s.external_id, { id: s.external_id, name: s.name, path: s.path ?? s.name }])
      )
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const current = crumbs[crumbs.length - 1];
    setIsLoading(true);
    sourcesService
      .listDriveFolders(current.id)
      .then(setFolders)
      .catch((err) => {
        toast.error(err instanceof ApiError ? err.message : "Could not load folders.");
        setFolders([]);
      })
      .finally(() => setIsLoading(false));
  }, [crumbs, open]);

  function currentPath(name: string) {
    return [...crumbs.slice(1).map((c) => c.name), name].join(" / ") || name;
  }

  function toggleSelected(folder: DriveFolder) {
    setSelected((prev) => {
      const next = new Map(prev);
      if (next.has(folder.id)) {
        next.delete(folder.id);
      } else {
        next.set(folder.id, { id: folder.id, name: folder.name, path: currentPath(folder.name) });
      }
      return next;
    });
  }

  function openFolder(folder: DriveFolder) {
    setCrumbs((prev) => [...prev, { id: folder.id, name: folder.name }]);
  }

  async function handleSave() {
    setIsSaving(true);
    try {
      const sources = await sourcesService.selectDriveFolders(Array.from(selected.values()));
      onSaved(sources);
      toast.success("Folder selection saved");
      onOpenChange(false);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not save folder selection.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Choose Google Drive folders</DialogTitle>
          <DialogDescription>
            Only files inside the folders you select will be indexed.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-wrap items-center gap-1 text-sm text-muted-foreground">
          {crumbs.map((crumb, i) => (
            <span key={crumb.id} className="flex items-center gap-1">
              {i > 0 && <ChevronRight className="size-3.5" />}
              <button
                className="rounded px-1 hover:bg-muted hover:text-foreground disabled:pointer-events-none"
                disabled={i === crumbs.length - 1}
                onClick={() => setCrumbs(crumbs.slice(0, i + 1))}
              >
                {crumb.name}
              </button>
            </span>
          ))}
        </div>

        <ScrollArea className="h-64 rounded-md border border-border">
          {isLoading ? (
            <div className="flex h-full items-center justify-center py-16">
              <Loader2 className="size-5 animate-spin text-muted-foreground" />
            </div>
          ) : folders.length === 0 ? (
            <p className="p-6 text-center text-sm text-muted-foreground">No subfolders here.</p>
          ) : (
            <ul className="divide-y divide-border">
              {folders.map((folder) => (
                <li key={folder.id} className="flex items-center gap-2 px-3 py-2 hover:bg-muted/50">
                  <Checkbox
                    checked={selected.has(folder.id)}
                    onCheckedChange={() => toggleSelected(folder)}
                    aria-label={`Select ${folder.name}`}
                  />
                  <Folder className="size-4 shrink-0 text-muted-foreground" />
                  <span className="flex-1 truncate text-sm">{folder.name}</span>
                  <Button variant="ghost" size="icon-sm" onClick={() => openFolder(folder)} aria-label="Open">
                    <ChevronRight className="size-4" />
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </ScrollArea>

        {selected.size > 0 && (
          <div>
            <p className="mb-1.5 text-xs font-medium text-muted-foreground">
              Selected ({selected.size})
            </p>
            <div className="flex flex-wrap gap-1.5">
              {Array.from(selected.values()).map((f) => (
                <span
                  key={f.id}
                  className="flex items-center gap-1 rounded-full bg-accent px-2.5 py-1 text-xs text-accent-foreground"
                >
                  <FolderOpen className="size-3" />
                  {f.name}
                  <button
                    onClick={() =>
                      setSelected((prev) => {
                        const next = new Map(prev);
                        next.delete(f.id);
                        return next;
                      })
                    }
                    aria-label={`Remove ${f.name}`}
                  >
                    <X className="size-3" />
                  </button>
                </span>
              ))}
            </div>
          </div>
        )}

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
