import Link from "next/link";
import { AuthShell } from "@/components/layout/auth-shell";
import { SignupForm } from "@/components/onboarding/signup-form";

export default function SignupPage() {
  return (
    <AuthShell
      title="Create your workspace"
      description="One account, one organization — you can invite teammates later."
      footer={
        <>
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-foreground underline underline-offset-4">
            Log in
          </Link>
        </>
      }
    >
      <SignupForm />
    </AuthShell>
  );
}
