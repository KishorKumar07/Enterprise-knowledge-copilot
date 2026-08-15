"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { chatService } from "@/services/chat";
import type { Conversation } from "@/types/chat";

interface ChatContextValue {
  conversations: Conversation[];
  isLoading: boolean;
  refresh: () => Promise<void>;
  removeLocal: (id: string) => void;
  upsertLocal: (conversation: Conversation) => void;
}

const ChatContext = createContext<ChatContextValue | null>(null);

export function ChatProvider({ children }: { children: ReactNode }) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      setConversations(await chatService.listConversations());
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  function removeLocal(id: string) {
    setConversations((prev) => prev.filter((c) => c.id !== id));
  }

  function upsertLocal(conversation: Conversation) {
    setConversations((prev) => {
      const exists = prev.some((c) => c.id === conversation.id);
      const next = exists ? prev.map((c) => (c.id === conversation.id ? conversation : c)) : [conversation, ...prev];
      return next.sort((a, b) => (a.updated_at < b.updated_at ? 1 : -1));
    });
  }

  return (
    <ChatContext.Provider value={{ conversations, isLoading, refresh, removeLocal, upsertLocal }}>
      {children}
    </ChatContext.Provider>
  );
}

export function useChatContext() {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChatContext must be used within ChatProvider");
  return ctx;
}
