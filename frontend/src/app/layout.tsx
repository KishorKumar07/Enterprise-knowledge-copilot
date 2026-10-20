import type { Metadata } from "next";
// Self-hosted via the `geist` package rather than next/font/google, so the build
// never has to reach fonts.googleapis.com (fails behind proxies / in locked-down CI).
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { Toaster } from "@/components/ui/sonner";
import { MotionProvider } from "@/components/layout/motion-provider";
import { ThemeProvider } from "@/components/layout/theme-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: "Enterprise Knowledge Copilot",
  description: "Ask questions across Google Drive and Slack, and get grounded answers with citations.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${GeistSans.variable} ${GeistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <ThemeProvider>
          <MotionProvider>{children}</MotionProvider>
          <Toaster position="top-center" />
        </ThemeProvider>
      </body>
    </html>
  );
}
