"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import { Check, MessageSquarePlus, Pencil, Trash2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { chatService } from "@/services/chat";
import { ApiError } from "@/services/api-client";
import { useChatContext } from "@/components/chat/chat-context";
import { cn } from "@/lib/utils";

export function ConversationSidebar() {
  const router = useRouter();
  const params = useParams<{ conversationId?: string }>();
  const activeId = params?.conversationId;
  const { conversations, isLoading, removeLocal, upsertLocal } = useChatContext();

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");

  async function handleNewChat() {
    try {
      const conversation = await chatService.createConversation();
      upsertLocal(conversation);
      router.push(`/app/chat/${conversation.id}`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not start a new chat.");
    }
  }

  async function handleDelete(id: string) {
    try {
      await chatService.deleteConversation(id);
      removeLocal(id);
      if (activeId === id) router.push("/app/chat");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not delete conversation.");
    }
  }

  async function commitRename(id: string) {
    const title = editValue.trim();
    setEditingId(null);
    if (!title) return;
    try {
      upsertLocal(await chatService.renameConversation(id, title));
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not rename conversation.");
    }
  }

  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-border md:flex">
      <div className="p-3">
        <Button variant="outline" className="w-full justify-start gap-2" onClick={handleNewChat}>
          <MessageSquarePlus className="size-4" />
          New chat
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-3">
        {isLoading ? (
          <p className="px-2 py-3 text-xs text-muted-foreground">Loading…</p>
        ) : conversations.length === 0 ? (
          <p className="px-2 py-3 text-xs text-muted-foreground">No conversations yet.</p>
        ) : (
          <ul className="space-y-0.5">
            {conversations.map((c) => (
              <li key={c.id} className="group relative">
                {editingId === c.id ? (
                  <div className="flex items-center gap-1 px-1 py-1">
                    <Input
                      autoFocus
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") commitRename(c.id);
                        if (e.key === "Escape") setEditingId(null);
                      }}
                      className="h-7 text-xs"
                    />
                    <button onClick={() => commitRename(c.id)} className="text-muted-foreground hover:text-foreground">
                      <Check className="size-3.5" />
                    </button>
                    <button onClick={() => setEditingId(null)} className="text-muted-foreground hover:text-foreground">
                      <X className="size-3.5" />
                    </button>
                  </div>
                ) : (
                  <Link
                    href={`/app/chat/${c.id}`}
                    className={cn(
                      "flex items-center justify-between rounded-md px-2 py-1.5 text-sm",
                      activeId === c.id ? "bg-accent text-accent-foreground" : "hover:bg-muted"
                    )}
                  >
                    <span className="truncate">{c.title}</span>
                    <span className="ml-1 hidden shrink-0 items-center gap-0.5 group-hover:flex">
                      <button
                        onClick={(e) => {
                          e.preventDefault();
                          setEditingId(c.id);
                          setEditValue(c.title);
                        }}
                        className="rounded p-1 text-muted-foreground hover:bg-background hover:text-foreground"
                        aria-label="Rename"
                      >
                        <Pencil className="size-3" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.preventDefault();
                          handleDelete(c.id);
                        }}
                        className="rounded p-1 text-muted-foreground hover:bg-background hover:text-destructive"
                        aria-label="Delete"
                      >
                        <Trash2 className="size-3" />
                      </button>
                    </span>
                  </Link>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}
