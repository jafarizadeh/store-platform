import type { Metadata } from "next";

import AuthForm from "@/components/auth-form";
import SiteHeader from "@/components/site-header";

export const metadata: Metadata = {
  title: "Sign in",
  description:
    "Sign in to your ByNET account.",
};

export default function LoginPage() {
  return (
    <main className="min-h-screen bg-white text-neutral-950">
      <SiteHeader />

      <section className="border-b border-neutral-200 bg-neutral-50">
        <div className="mx-auto grid max-w-6xl gap-12 px-6 py-16 lg:grid-cols-[1fr_480px] lg:items-center lg:px-8 lg:py-24">
          <div className="max-w-xl">
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-neutral-500">
              ByNET account
            </p>

            <h1 className="mt-5 text-5xl font-semibold leading-[0.95] tracking-[-0.055em] sm:text-6xl">
              Your builds,
              <br />
              in one place.
            </h1>

            <p className="mt-6 max-w-lg text-base leading-7 text-neutral-600 sm:text-lg">
              Sign in to manage purchases,
              orders and the Raspberry Pi
              projects connected to your
              account.
            </p>
          </div>

          <AuthForm mode="login" />
        </div>
      </section>
    </main>
  );
}
