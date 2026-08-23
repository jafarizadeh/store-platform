import type { Metadata } from "next";

import AccountPanel from "@/components/account-panel";
import SiteHeader from "@/components/site-header";

export const metadata: Metadata = {
  title: "Account",
  description:
    "Manage your ByNET customer account.",
};

export default function AccountPage() {
  return (
    <main className="min-h-screen bg-neutral-50 text-neutral-950">
      <SiteHeader />

      <section className="mx-auto max-w-5xl px-6 py-14 lg:px-8 lg:py-20">
        <div className="mb-8">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-neutral-500">
            ByNET
          </p>

          <h1 className="mt-3 text-4xl font-semibold tracking-[-0.05em] sm:text-5xl">
            Your account.
          </h1>
        </div>

        <AccountPanel />
      </section>
    </main>
  );
}
