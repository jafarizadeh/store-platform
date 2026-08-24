"use client";

import Link from "next/link";

import { useAuth } from "@/context/auth-context";

export default function AccountLink() {
  const {
    user,
    isLoading,
  } = useAuth();

  if (isLoading) {
    return (
      <span
        className="inline-flex rounded-full border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-400"
        aria-label="Checking account status"
      >
        Account
      </span>
    );
  }

  if (!user) {
    return (
      <Link
        href="/login"
        className="rounded-full border border-neutral-300 px-4 py-2 text-sm font-medium transition hover:border-neutral-950 hover:bg-neutral-50"
      >
        Sign in
      </Link>
    );
  }

  return (
    <Link
      href="/account"
      className="inline-flex items-center gap-2 rounded-full border border-neutral-300 px-4 py-2 text-sm font-medium transition hover:border-neutral-950 hover:bg-neutral-50"
    >
      <span
        className="h-2 w-2 rounded-full bg-emerald-500"
        aria-hidden="true"
      />
      Account
    </Link>
  );
}
