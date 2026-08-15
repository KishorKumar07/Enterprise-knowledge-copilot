import { ConversationSidebar } from "@/components/chat/conversation-sidebar";
import { ChatProvider } from "@/components/chat/chat-context";

export default function ChatLayout({ children }: LayoutProps<"/app/chat">) {
  return (
    <ChatProvider>
      <div className="flex h-full min-h-0">
        <ConversationSidebar />
        <div className="flex min-w-0 flex-1 flex-col">{children}</div>
      </div>
    </ChatProvider>
  );
}
