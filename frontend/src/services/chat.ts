import { apiClient } from "@/services/api-client";
import type { Conversation, ConversationDetail, Message, StreamEvent } from "@/types/chat";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const chatService = {
  listConversations: () => apiClient.get<Conversation[]>("/api/chat/conversations"),
  createConversation: () => apiClient.post<Conversation>("/api/chat/conversations"),
  getConversation: (id: string) => apiClient.get<ConversationDetail>(`/api/chat/conversations/${id}`),
  renameConversation: (id: string, title: string) =>
    apiClient.patch<Conversation>(`/api/chat/conversations/${id}`, { title }),
  deleteConversation: (id: string) => apiClient.delete<void>(`/api/chat/conversations/${id}`),
  setFeedback: (messageId: string, feedback: "up" | "down" | null) =>
    apiClient.patch<Message>(`/api/chat/messages/${messageId}/feedback`, { feedback }),
};

async function* parseSSE(response: Response): AsyncGenerator<StreamEvent> {
  if (!response.body) return;
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";

    for (const part of parts) {
      const line = part.split("\n").find((l) => l.startsWith("data: "));
      if (!line) continue;
      try {
        yield JSON.parse(line.slice(6)) as StreamEvent;
      } catch {
        // ignore malformed chunk
      }
    }
  }
}

export async function* streamMessage(
  conversationId: string,
  content: string,
  signal: AbortSignal
): AsyncGenerator<StreamEvent> {
  const response = await fetch(`${API_URL}/api/chat/conversations/${conversationId}/messages`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
    signal,
  });

  if (!response.ok) {
    throw new Error("Could not send message. Please try again.");
  }

  yield* parseSSE(response);
}

export async function* regenerateMessage(
  conversationId: string,
  signal: AbortSignal
): AsyncGenerator<StreamEvent> {
  const response = await fetch(`${API_URL}/api/chat/conversations/${conversationId}/regenerate`, {
    method: "POST",
    credentials: "include",
    signal,
  });

  if (!response.ok) {
    throw new Error("Could not regenerate. Please try again.");
  }

  yield* parseSSE(response);
}
