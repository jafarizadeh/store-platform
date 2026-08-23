"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/context/auth-context";
import { authErrorMessage } from "@/lib/auth-client";

export default function AccountPanel() {
  const router = useRouter();

  const {
    user,
    isLoading,
    logout,
  } = useAuth();

  const [error, setError] =
    useState<string | null>(null);

  const [isLoggingOut, setIsLoggingOut] =
    useState(false);

  async function handleLogout(): Promise<void> {
    if (isLoggingOut) {
      return;
    }

    setError(null);
    setIsLoggingOut(true);

    try {
      await logout();

      router.replace("/");
      router.refresh();
    } catch (requestError) {
      setError(
        authErrorMessage(
          requestError,
        ),
      );
    } finally {
      setIsLoggingOut(false);
    }
  }

  if (isLoading) {
    return (
      <div className="rounded-[2rem] border border-neutral-200 bg-white p-8 sm:p-10">
        <p className="text-sm text-neutral-500">
          Loading account…
        </p>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="rounded-[2rem] border border-neutral-200 bg-white p-8 sm:p-10">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-neutral-500">
          Account
        </p>

        <h2 className="mt-4 text-3xl font-semibold tracking-[-0.045em]">
          Sign in required.
        </h2>

        <p className="mt-4 text-sm leading-6 text-neutral-600">
          Sign in to view your account
          and order history.
        </p>

        <Link
          href="/login?next=/account"
          className="mt-7 inline-flex rounded-full bg-neutral-950 px-6 py-3 text-sm font-semibold text-white transition hover:bg-neutral-700"
        >
          Sign in
        </Link>
      </div>
    );
  }

  return (
    <div className="rounded-[2rem] border border-neutral-200 bg-white p-8 shadow-[0_24px_80px_rgba(0,0,0,0.04)] sm:p-10">
      <div className="flex flex-col gap-6 border-b border-neutral-200 pb-8 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-neutral-500">
            Customer account
          </p>

          <h2 className="mt-3 text-3xl font-semibold tracking-[-0.045em]">
            Account
          </h2>
        </div>

        <span className="inline-flex w-fit items-center gap-2 rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-800">
          <span
            className="h-2 w-2 rounded-full bg-emerald-500"
            aria-hidden="true"
          />
          Active
        </span>
      </div>

      <dl className="divide-y divide-neutral-200">
        <div className="grid gap-2 py-6 sm:grid-cols-[160px_1fr]">
          <dt className="text-sm text-neutral-500">
            Email
          </dt>

          <dd className="break-all text-sm font-medium">
            {user.email}
          </dd>
        </div>

        <div className="grid gap-2 py-6 sm:grid-cols-[160px_1fr]">
          <dt className="text-sm text-neutral-500">
            Customer ID
          </dt>

          <dd className="break-all font-mono text-xs text-neutral-700">
            {user.id}
          </dd>
        </div>
      </dl>

      <section className="mt-3 rounded-3xl bg-neutral-50 p-6">
        <h3 className="text-lg font-semibold tracking-[-0.03em]">
          Orders
        </h3>

        <p className="mt-2 text-sm leading-6 text-neutral-600">
          Your customer account is ready.
          Order history will appear here
          after orders are linked to
          authenticated users.
        </p>
      </section>

      {error && (
        <div
          role="alert"
          className="mt-6 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
        >
          {error}
        </div>
      )}

      <div className="mt-8 flex flex-wrap gap-3">
        <Link
          href="/shop"
          className="rounded-full bg-neutral-950 px-6 py-3 text-sm font-semibold text-white transition hover:bg-neutral-700"
        >
          Continue shopping
        </Link>

        <button
          type="button"
          disabled={isLoggingOut}
          onClick={() => {
            void handleLogout();
          }}
          className="rounded-full border border-neutral-300 px-6 py-3 text-sm font-semibold transition hover:border-neutral-950 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:text-neutral-400"
        >
          {isLoggingOut
            ? "Signing out..."
            : "Sign out"}
        </button>
      </div>
    </div>
  );
}
