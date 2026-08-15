"use client";

import { useState } from "react";
import Link from "next/link";
import { AnimatePresence, motion } from "motion/react";
import { X } from "lucide-react";
import { AppSidebarNav } from "@/components/layout/app-sidebar";
import { AppTopbar } from "@/components/layout/app-topbar";
import type { User } from "@/types/user";

export function AppShell({ user, children }: { user: User; children: React.ReactNode }) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <aside className="hidden w-60 shrink-0 flex-col border-r border-sidebar-border bg-sidebar py-4 lg:flex">
        <Link href="/app" className="mb-6 flex items-center gap-2 px-4 font-semibold tracking-tight text-sidebar-foreground">
          <span className="flex size-7 items-center justify-center rounded-md bg-sidebar-primary text-sm text-sidebar-primary-foreground">
            K
          </span>
          Knowledge Copilot
        </Link>
        <AppSidebarNav />
      </aside>

      <AnimatePresence>
        {mobileNavOpen && (
          <>
            <motion.div
              className="fixed inset-0 z-40 bg-black/40 lg:hidden"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              onClick={() => setMobileNavOpen(false)}
            />
            <motion.aside
              className="fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-sidebar-border bg-sidebar py-4 lg:hidden"
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
            >
              <div className="mb-6 flex items-center justify-between px-4">
                <Link
                  href="/app"
                  onClick={() => setMobileNavOpen(false)}
                  className="flex items-center gap-2 font-semibold tracking-tight text-sidebar-foreground"
                >
                  <span className="flex size-7 items-center justify-center rounded-md bg-sidebar-primary text-sm text-sidebar-primary-foreground">
                    K
                  </span>
                  Knowledge Copilot
                </Link>
                <button
                  onClick={() => setMobileNavOpen(false)}
                  aria-label="Close navigation"
                  className="text-sidebar-foreground/70 hover:text-sidebar-foreground"
                >
                  <X className="size-5" />
                </button>
              </div>
              <AppSidebarNav onNavigate={() => setMobileNavOpen(false)} />
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      <div className="flex min-w-0 flex-1 flex-col">
        <AppTopbar user={user} onMenuClick={() => setMobileNavOpen(true)} />
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
