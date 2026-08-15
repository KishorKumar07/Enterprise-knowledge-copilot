"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Skeleton } from "@/components/ui/skeleton";
import { ChatInput } from "@/components/chat/chat-input";
import { MessageBubble } from "@/components/chat/message-bubble";
import { useChat } from "@/hooks/use-chat";
import { useChatContext } from "@/components/chat/chat-context";

function initials(name: string) {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");
}

export default function ChatThreadPage() {
  const params = useParams<{ conversationId: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { messages, isLoading, isStreaming, sendMessage, regenerate, stop, setFeedback } = useChat(
    params.conversationId
  );
  const { refresh: refreshConversations } = useChatContext();
  const [value, setValue] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const sentInitial = useRef(false);
  const wasStreaming = useRef(false);

  useEffect(() => {
    const initial = searchParams.get("q");
    if (initial && !sentInitial.current && !isLoading) {
      sentInitial.current = true;
      sendMessage(initial);
      router.replace(`/app/chat/${params.conversationId}`);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoading]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (wasStreaming.current && !isStreaming) {
      refreshConversations();
    }
    wasStreaming.current = isStreaming;
  }, [isStreaming, refreshConversations]);

  function handleSend() {
    if (!value.trim() || isStreaming) return;
    sendMessage(value);
    setValue("");
  }

  const lastAssistantId = [...messages].reverse().find((m) => m.role === "assistant")?.id;

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="space-y-4 p-4">
            <Skeleton className="h-16 w-2/3" />
            <Skeleton className="h-24 w-3/4" />
          </div>
        ) : (
          <div className="mx-auto max-w-3xl py-2">
            {messages.map((message, i) => (
              <MessageBubble
                key={message.id}
                message={message}
                userInitials={initials("You")}
                isLast={message.id === lastAssistantId}
                isStreaming={isStreaming && i === messages.length - 1}
                onRegenerate={message.id === lastAssistantId && !isStreaming ? regenerate : undefined}
                onFeedback={
                  message.role === "assistant" && !isStreaming
                    ? (fb) => setFeedback(message.id, fb)
                    : undefined
                }
              />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      <ChatInput
        value={value}
        onChange={setValue}
        onSend={handleSend}
        onStop={stop}
        isStreaming={isStreaming}
      />
    </div>
  );
}
