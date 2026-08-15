"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { ExternalLink, FileText, Hash } from "lucide-react";
import type { Citation } from "@/types/chat";

function CitationCard({ citation }: { citation: Citation }) {
  const [expanded, setExpanded] = useState(false);
  const Icon = citation.provider === "slack" ? Hash : FileText;

  return (
    <div className="rounded-lg border border-border bg-card">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs"
      >
        <Icon className="size-3.5 shrink-0 text-muted-foreground" />
        <span className="truncate font-medium">
          [{citation.index}] {citation.title}
        </span>
      </button>
      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.18 }}
            className="overflow-hidden"
          >
            <div className="border-t border-border px-3 py-2">
              <p className="text-xs text-muted-foreground">{citation.snippet}…</p>
              {citation.source_url && (
                <a
                  href={citation.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                >
                  Open source <ExternalLink className="size-3" />
                </a>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function CitationList({ citations }: { citations: Citation[] }) {
  if (citations.length === 0) return null;

  return (
    <div className="mt-3 space-y-1.5">
      <p className="text-xs font-medium text-muted-foreground">Sources</p>
      <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
        {citations.map((c) => (
          <CitationCard key={c.index} citation={c} />
        ))}
      </div>
    </div>
  );
}
