import { getServerUser } from "@/services/server-auth";
import { SourceOverview } from "@/components/dashboard/source-overview";

export default async function DashboardPage() {
  const user = await getServerUser();

  return (
    <div className="mx-auto max-w-5xl px-6 py-8 lg:px-10">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">
          Welcome, {user?.name.split(" ")[0]}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Connect a knowledge source to start asking questions.
        </p>
      </div>

      <SourceOverview />
    </div>
  );
}
