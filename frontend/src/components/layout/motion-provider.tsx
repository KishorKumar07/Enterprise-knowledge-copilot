"use client";

import { MotionConfig } from "motion/react";

// Automatically shortens/disables animations when the user has requested
// reduced motion at the OS level (prefers-reduced-motion).
export function MotionProvider({ children }: { children: React.ReactNode }) {
  return <MotionConfig reducedMotion="user">{children}</MotionConfig>;
}
