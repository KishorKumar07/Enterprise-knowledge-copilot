import { getServerUser } from "@/services/server-auth";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

function initials(name: string) {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export default async function ProfilePage() {
  const user = await getServerUser();

  if (!user) {
    return null;
  }

  return (
    <div className="mx-auto max-w-2xl px-6 py-8 lg:px-10">
      <h1 className="text-2xl font-semibold tracking-tight">Profile</h1>
      <p className="mt-1 text-sm text-muted-foreground">Your account details.</p>

      <div className="mt-8 flex items-center gap-4 rounded-xl border border-border bg-card p-5">
        <Avatar className="size-14">
          <AvatarFallback className="text-lg">{initials(user.name)}</AvatarFallback>
        </Avatar>
        <div>
          <p className="text-sm font-semibold">{user.name}</p>
          <p className="text-sm text-muted-foreground">{user.email}</p>
        </div>
      </div>

      <dl className="mt-6 divide-y divide-border rounded-xl border border-border bg-card">
        <div className="flex items-center justify-between px-5 py-4">
          <dt className="text-sm text-muted-foreground">Organization ID</dt>
          <dd className="font-mono text-xs text-muted-foreground">{user.organization_id}</dd>
        </div>
        <div className="flex items-center justify-between px-5 py-4">
          <dt className="text-sm text-muted-foreground">User ID</dt>
          <dd className="font-mono text-xs text-muted-foreground">{user.id}</dd>
        </div>
      </dl>
    </div>
  );
}
