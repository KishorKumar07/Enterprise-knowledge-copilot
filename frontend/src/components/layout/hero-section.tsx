"use client";

import Link from "next/link";
import { motion } from "motion/react";
import { Button } from "@/components/ui/button";
import { FileText, MessageSquareText, Hash } from "lucide-react";

const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  show: (delay: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, delay, ease: [0.16, 1, 0.3, 1] as const },
  }),
};

export function HeroSection() {
  return (
    <section className="mx-auto flex max-w-4xl flex-col items-center px-6 pt-24 pb-20 text-center">
      <motion.span
        initial="hidden"
        animate="show"
        custom={0}
        variants={fadeUp}
        className="mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-muted px-3 py-1 text-xs font-medium text-muted-foreground"
      >
        Google Drive + Slack, in one AI copilot
      </motion.span>

      <motion.h1
        initial="hidden"
        animate="show"
        custom={0.08}
        variants={fadeUp}
        className="text-4xl font-semibold tracking-tight text-balance sm:text-5xl"
      >
        Ask your company&apos;s knowledge base a question.
        <br className="hidden sm:block" /> Get a grounded answer.
      </motion.h1>

      <motion.p
        initial="hidden"
        animate="show"
        custom={0.16}
        variants={fadeUp}
        className="mt-6 max-w-2xl text-balance text-lg text-muted-foreground"
      >
        Connect Google Drive and Slack, pick the folders and channels that matter, and let a
        multi-agent AI copilot answer questions with real citations back to the source.
      </motion.p>

      <motion.div
        initial="hidden"
        animate="show"
        custom={0.24}
        variants={fadeUp}
        className="mt-10 flex flex-col gap-3 sm:flex-row"
      >
        <Button size="lg" nativeButton={false} render={<Link href="/signup" />}>
          Start for free
        </Button>
        <Button size="lg" variant="outline" nativeButton={false} render={<Link href="/login" />}>
          I already have an account
        </Button>
      </motion.div>

      <motion.div
        initial="hidden"
        animate="show"
        custom={0.32}
        variants={fadeUp}
        className="mt-20 grid w-full grid-cols-1 gap-4 text-left sm:grid-cols-3"
      >
        <FeatureCard
          icon={<FileText className="size-5" />}
          title="Connect your sources"
          description="Authorize Drive and Slack once, then choose exactly which folders and channels get indexed."
        />
        <FeatureCard
          icon={<MessageSquareText className="size-5" />}
          title="Ask in plain English"
          description="A supervisor agent routes your question, retrieves evidence, and reasons across documents and threads."
        />
        <FeatureCard
          icon={<Hash className="size-5" />}
          title="Trust every answer"
          description="Every response links back to the exact document or Slack message it came from — never a guess."
        />
      </motion.div>
    </section>
  );
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="mb-3 flex size-9 items-center justify-center rounded-lg bg-accent text-accent-foreground">
        {icon}
      </div>
      <h3 className="mb-1 text-sm font-semibold">{title}</h3>
      <p className="text-sm text-muted-foreground">{description}</p>
    </div>
  );
}
