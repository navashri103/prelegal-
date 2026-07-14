"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowsClockwise } from "@phosphor-icons/react/ssr";
import { useAuth } from "@/lib/auth-context";
import { ApiError } from "@/lib/api";
import PageHeader from "../page-header";

const MIN_PASSWORD_LENGTH = 8;

export default function SignupPage() {
  const { status, signup } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Already signed in (e.g. back button, bookmark) - a signup form under a header
  // that says "signed in as ..." is a confusing state, so bounce onward instead.
  useEffect(() => {
    if (status === "authenticated") router.replace("/my-documents");
  }, [status, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (password.length < MIN_PASSWORD_LENGTH) {
      setError(`Password must be at least ${MIN_PASSWORD_LENGTH} characters.`);
      return;
    }
    setIsSubmitting(true);
    try {
      await signup(email, password);
      router.push("/my-documents");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="mx-auto flex w-full max-w-md flex-1 flex-col gap-10 px-6 py-10 sm:px-10">
      <PageHeader
        title="Sign up"
        subtitle="Create an account to save and resume your documents."
        backLink={{ href: "/", label: "Back to documents" }}
      />

      {status !== "authenticated" && (
        <form
          onSubmit={handleSubmit}
          className="flex flex-col gap-4 rounded-xl border border-border bg-card p-6 shadow-sm sm:p-7"
        >
          <div className="flex flex-col gap-1.5">
            <label htmlFor="email" className="text-sm font-medium text-foreground">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground shadow-sm transition-colors placeholder:text-muted-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-card"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="password" className="text-sm font-medium text-foreground">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              minLength={MIN_PASSWORD_LENGTH}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground shadow-sm transition-colors placeholder:text-muted-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-card"
            />
            <p className="text-xs text-muted-foreground">At least {MIN_PASSWORD_LENGTH} characters.</p>
          </div>

          {error && <p className="text-xs text-destructive">{error}</p>}

          <button
            type="submit"
            disabled={isSubmitting}
            className="inline-flex cursor-pointer items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground shadow-sm transition-colors duration-200 hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-card disabled:cursor-not-allowed disabled:bg-muted disabled:text-muted-foreground"
          >
            {isSubmitting ? <ArrowsClockwise size={18} weight="bold" className="animate-spin" /> : "Sign up"}
          </button>

          <p className="text-center text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link href="/login" className="font-medium text-primary hover:text-primary-hover">
              Log in
            </Link>
          </p>
        </form>
      )}
    </div>
  );
}
