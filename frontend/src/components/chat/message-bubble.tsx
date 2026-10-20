"use client";

import { useState } from "react";
import { motion } from "motion/react";
import { Check, Copy, RefreshCw, ThumbsDown, ThumbsUp } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { MarkdownContent } from "@/components/chat/markdown-content";
import { CitationList } from "@/components/chat/citation-list";
import type { Message } from "@/types/chat";
import { cn } from "@/lib/utils";

export function MessageBubble({
  message,
  userInitials,
  isLast,
  isStreaming,
  onRegenerate,
  onFeedback,
}: {
  message: Message;
  userInitials: string;
  isLast: boolean;
  isStreaming: boolean;
  onRegenerate?: () => void;
  onFeedback?: (feedback: "up" | "down") => void;
}) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === "user";

  async function handleCopy() {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
      className={cn("flex gap-3 px-4 py-3", isUser ? "flex-row-reverse" : "flex-row")}
    >
      <Avatar className="size-7 shrink-0">
        <AvatarFallback className="text-[10px]">
          {isUser ? userInitials : "AI"}
        </AvatarFallback>
      </Avatar>

      <div className={cn("min-w-0 max-w-[85%] sm:max-w-[75%]", isUser && "flex flex-col items-end")}>
        <div
          className={cn(
            "rounded-2xl px-4 py-2.5",
            isUser ? "bg-primary text-primary-foreground" : "bg-muted text-foreground"
          )}
        >
          {isUser ? (
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
          ) : message.content ? (
            <MarkdownContent content={message.content} />
          ) : isStreaming ? (
            <span className="flex gap-1 py-1">
              <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.3s]" />
              <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.15s]" />
              <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground" />
            </span>
          ) : null}
        </div>

        {!isUser && !isStreaming && message.content && (
          <>
            <CitationList citations={message.citations} />
            <div className="mt-1.5 flex items-center gap-1">
              <button
                onClick={handleCopy}
                className="rounded p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
                aria-label="Copy response"
              >
                {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
              </button>
              {isLast && onRegenerate && (
                <button
                  onClick={onRegenerate}
                  className="rounded p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
                  aria-label="Regenerate response"
                >
                  <RefreshCw className="size-3.5" />
                </button>
              )}
              {onFeedback && (
                <>
                  <button
                    onClick={() => onFeedback("up")}
                    className={cn(
                      "rounded p-1.5 hover:bg-muted",
                      message.feedback === "up"
                        ? "text-emerald-600 dark:text-emerald-400"
                        : "text-muted-foreground hover:text-foreground"
                    )}
                    aria-label="Good response"
                  >
                    <ThumbsUp className="size-3.5" />
                  </button>
                  <button
                    onClick={() => onFeedback("down")}
                    className={cn(
                      "rounded p-1.5 hover:bg-muted",
                      message.feedback === "down" ? "text-destructive" : "text-muted-foreground hover:text-foreground"
                    )}
                    aria-label="Poor response"
                  >
                    <ThumbsDown className="size-3.5" />
                  </button>
                </>
              )}
            </div>
          </>
        )}

        {!isUser && !isStreaming && !message.content && (
          <p className="mt-1 text-xs text-destructive">Something went wrong. Try again.</p>
        )}
      </div>
    </motion.div>
  );
}
