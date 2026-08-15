import { redirect } from "next/navigation";
import { getServerUser } from "@/services/server-auth";
import { AppShell } from "@/components/layout/app-shell";

export default async function AppLayout({ children }: LayoutProps<"/app">) {
  const user = await getServerUser();

  if (!user) {
    redirect("/login");
  }

  return <AppShell user={user}>{children}</AppShell>;
}
