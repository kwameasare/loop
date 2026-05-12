import Link from "next/link";

import { EnterpriseSignupForm } from "@/components/signup/enterprise-signup-form";

export default function SignupPage() {
  return (
    <main className="min-h-screen px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto mb-6 flex max-w-6xl items-center justify-between">
        <Link href="/" className="inline-flex items-center gap-2 font-semibold">
          <span className="grid h-9 w-9 place-items-center rounded-md border bg-primary text-primary-foreground">
            L
          </span>
          <span>Loop Studio</span>
        </Link>
        <Link href="/login" className="text-sm font-medium text-muted-foreground hover:text-foreground">
          Sign in
        </Link>
      </div>
      <EnterpriseSignupForm />
    </main>
  );
}
