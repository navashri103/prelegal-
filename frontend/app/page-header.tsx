"use client";

import Link from "next/link";
import { ArrowLeft, ShieldCheck } from "@phosphor-icons/react/ssr";
import { useAuth } from "@/lib/auth-context";
import ThemeToggle from "./theme-toggle";

type PageHeaderProps = {
  title: string;
  subtitle: string;
  backLink?: { href: string; label: string };
};

export default function PageHeader({ title, subtitle, backLink }: PageHeaderProps) {
  const { status, user, logout } = useAuth();

  return (
    <header className="flex items-start justify-between gap-4">
      <div className="flex items-start gap-3">
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
          <ShieldCheck size={22} weight="fill" />
        </span>
        <div className="flex flex-col gap-1">
          {backLink && (
            <Link
              href={backLink.href}
              className="inline-flex w-fit items-center gap-1 text-xs font-medium text-muted-foreground transition-colors duration-200 hover:text-foreground"
            >
              <ArrowLeft size={12} weight="bold" />
              {backLink.label}
            </Link>
          )}
          <h1 className="font-serif text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
            {title}
          </h1>
          <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground">{subtitle}</p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {status === "authenticated" && user && (
          <div className="hidden items-center gap-3 sm:flex">
            <Link
              href="/my-documents"
              className="text-sm font-medium text-muted-foreground transition-colors duration-200 hover:text-foreground"
            >
              My Documents
            </Link>
            <span className="text-sm text-muted-foreground">{user.email}</span>
            <button
              type="button"
              onClick={() => void logout()}
              className="cursor-pointer text-sm font-medium text-muted-foreground transition-colors duration-200 hover:text-foreground"
            >
              Log out
            </button>
          </div>
        )}
        {status === "guest" && (
          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="text-sm font-medium text-muted-foreground transition-colors duration-200 hover:text-foreground"
            >
              Log in
            </Link>
            <Link
              href="/signup"
              className="text-sm font-medium text-primary transition-colors duration-200 hover:text-primary-hover"
            >
              Sign up
            </Link>
          </div>
        )}
        <ThemeToggle />
      </div>
    </header>
  );
}
