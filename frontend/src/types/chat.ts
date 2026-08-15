export interface Citation {
  index: number;
  title: string;
  snippet: string;
  provider: string | null;
  source_url: string | null;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  feedback: "up" | "down" | null;
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

export type StreamEvent =
  | { type: "token"; text: string }
  | { type: "error"; text: string }
  | { type: "done"; message_id: string; citations: Citation[] };
