import Link from "next/link";
import { ArrowRight, Database } from "lucide-react";
import { getServerUser } from "@/services/server-auth";

export default async function SettingsPage() {
  const user = await getServerUser();

  if (!user) return null;

  return (
    <div className="mx-auto max-w-2xl px-6 py-8 lg:px-10">
      <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
      <p className="mt-1 text-sm text-muted-foreground">Manage your account and knowledge sources.</p>

      <section className="mt-8">
        <h2 className="text-sm font-semibold">Account</h2>
        <div className="mt-3 divide-y divide-border rounded-xl border border-border bg-card">
          <div className="flex items-center justify-between px-5 py-4">
            <span className="text-sm text-muted-foreground">Name</span>
            <span className="text-sm">{user.name}</span>
          </div>
          <div className="flex items-center justify-between px-5 py-4">
            <span className="text-sm text-muted-foreground">Email</span>
            <span className="text-sm">{user.email}</span>
          </div>
        </div>
      </section>

      <section className="mt-8">
        <h2 className="text-sm font-semibold">Knowledge sources</h2>
        <Link
          href="/app/sources"
          className="mt-3 flex items-center justify-between rounded-xl border border-border bg-card px-5 py-4 hover:border-primary/40 hover:bg-accent/30"
        >
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-lg bg-accent text-accent-foreground">
              <Database className="size-4" />
            </div>
            <div>
              <p className="text-sm font-medium">Google Drive &amp; Slack connections</p>
              <p className="text-xs text-muted-foreground">Connect, sync, or disconnect sources</p>
            </div>
          </div>
          <ArrowRight className="size-4 text-muted-foreground" />
        </Link>
      </section>

      <section className="mt-8">
        <h2 className="text-sm font-semibold">Workspace</h2>
        <div className="mt-3 rounded-xl border border-border bg-card px-5 py-4">
          <p className="text-sm text-muted-foreground">
            Team members and role-based access aren&apos;t available yet — each workspace currently
            supports a single member.
          </p>
        </div>
      </section>
    </div>
  );
}
