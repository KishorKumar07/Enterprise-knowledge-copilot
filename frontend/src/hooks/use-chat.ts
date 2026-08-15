"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { chatService, regenerateMessage, streamMessage } from "@/services/chat";
import { ApiError } from "@/services/api-client";
import type { Message } from "@/types/chat";

function tempId() {
  return `temp-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export function useChat(conversationId: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    chatService
      .getConversation(conversationId)
      .then((conv) => {
        if (!cancelled) setMessages(conv.messages);
      })
      .catch(() => {
        if (!cancelled) toast.error("Could not load this conversation.");
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [conversationId]);

  const consumeStream = useCallback(
    async (generator: AsyncGenerator<import("@/types/chat").StreamEvent>, assistantId: string) => {
      try {
        for await (const event of generator) {
          if (event.type === "token") {
            setMessages((prev) =>
              prev.map((m) => (m.id === assistantId ? { ...m, content: m.content + event.text } : m))
            );
          } else if (event.type === "error") {
            toast.error(event.text);
            setMessages((prev) =>
              prev.map((m) => (m.id === assistantId && !m.content ? { ...m, content: event.text } : m))
            );
          } else if (event.type === "done") {
            setMessages((prev) =>
              prev.map((m) => (m.id === assistantId ? { ...m, id: event.message_id, citations: event.citations } : m))
            );
          }
        }
      } catch (err) {
        if (!(err instanceof DOMException && err.name === "AbortError")) {
          toast.error(err instanceof Error ? err.message : "Something went wrong.");
        }
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    []
  );

  const sendMessage = useCallback(
    async (content: string) => {
      const userMessage: Message = {
        id: tempId(),
        role: "user",
        content,
        citations: [],
        feedback: null,
        created_at: new Date().toISOString(),
      };
      const assistantId = tempId();
      const assistantPlaceholder: Message = {
        id: assistantId,
        role: "assistant",
        content: "",
        citations: [],
        feedback: null,
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMessage, assistantPlaceholder]);
      setIsStreaming(true);

      const controller = new AbortController();
      abortRef.current = controller;
      await consumeStream(streamMessage(conversationId, content, controller.signal), assistantId);
    },
    [conversationId, consumeStream]
  );

  const regenerate = useCallback(async () => {
    setMessages((prev) => {
      const last = prev[prev.length - 1];
      if (!last || last.role !== "assistant") return prev;
      return prev.map((m) => (m.id === last.id ? { ...m, content: "", citations: [] } : m));
    });
    setIsStreaming(true);

    const assistantId = messages[messages.length - 1]?.id;
    if (!assistantId) return;

    const controller = new AbortController();
    abortRef.current = controller;
    await consumeStream(regenerateMessage(conversationId, controller.signal), assistantId);
  }, [conversationId, consumeStream, messages]);

  function stop() {
    abortRef.current?.abort();
    setIsStreaming(false);
  }

  async function setFeedback(messageId: string, feedback: "up" | "down") {
    const next = messages.find((m) => m.id === messageId)?.feedback === feedback ? null : feedback;
    setMessages((prev) => prev.map((m) => (m.id === messageId ? { ...m, feedback: next } : m)));
    try {
      await chatService.setFeedback(messageId, next);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not save feedback.");
    }
  }

  return { messages, isLoading, isStreaming, sendMessage, regenerate, stop, setFeedback };
}
