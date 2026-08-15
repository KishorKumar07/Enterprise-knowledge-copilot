"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { MessageSquareText, Sparkles } from "lucide-react";
import { ChatInput } from "@/components/chat/chat-input";
import { chatService } from "@/services/chat";
import { ApiError } from "@/services/api-client";
import { useChatContext } from "@/components/chat/chat-context";

const SUGGESTIONS = [
  "What is our authentication architecture?",
  "What is the leave policy?",
  "Summarize our latest backend deployment discussion.",
  "Which documents discuss payment failures?",
];

export default function ChatIndexPage() {
  const router = useRouter();
  const { upsertLocal } = useChatContext();
  const [value, setValue] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  async function startConversation(message: string) {
    if (!message.trim() || isCreating) return;
    setIsCreating(true);
    try {
      const conversation = await chatService.createConversation();
      upsertLocal(conversation);
      router.push(`/app/chat/${conversation.id}?q=${encodeURIComponent(message)}`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not start a new chat.");
      setIsCreating(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-1 flex-col items-center justify-center px-6 text-center">
        <div className="mb-4 flex size-12 items-center justify-center rounded-full bg-accent text-accent-foreground">
          <MessageSquareText className="size-6" />
        </div>
        <h1 className="text-lg font-semibold">Ask your knowledge copilot</h1>
        <p className="mt-1 max-w-sm text-sm text-muted-foreground">
          Questions are answered using your connected Google Drive and Slack content, with citations.
        </p>

        <div className="mt-6 grid w-full max-w-lg grid-cols-1 gap-2 sm:grid-cols-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => startConversation(s)}
              className="flex items-start gap-2 rounded-lg border border-border bg-card p-3 text-left text-xs hover:border-primary/40 hover:bg-accent/40"
            >
              <Sparkles className="mt-0.5 size-3.5 shrink-0 text-muted-foreground" />
              {s}
            </button>
          ))}
        </div>
      </div>

      <ChatInput
        value={value}
        onChange={setValue}
        onSend={() => startConversation(value)}
        onStop={() => {}}
        isStreaming={false}
        disabled={isCreating}
      />
    </div>
  );
}
