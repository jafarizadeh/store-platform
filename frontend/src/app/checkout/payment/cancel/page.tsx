import Link from "next/link";

import SiteHeader from "@/components/site-header";


export default function PaymentCancelPage() {
  return (
    <main className="min-h-screen bg-neutral-50 text-neutral-950">
      <SiteHeader />

      <section className="mx-auto max-w-2xl px-6 py-24 lg:px-8">
        <div className="rounded-[2rem] border border-neutral-200 bg-white p-8 sm:p-12">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-neutral-500">
            Payment not completed
          </p>

          <h1 className="mt-4 text-4xl font-semibold tracking-[-0.04em]">
            You returned before payment was confirmed.
          </h1>

          <p className="mt-5 leading-7 text-neutral-600">
            Your browser cannot cancel or
            confirm a payment by itself.
            ByNET keeps the payment attempt
            available for server-side
            reconciliation.
          </p>

          <div className="mt-9 flex flex-wrap gap-3">
            <Link
              href="/checkout/payment/status"
              className="rounded-full bg-neutral-950 px-6 py-3 text-sm font-semibold text-white"
            >
              Recheck payment status
            </Link>

            <Link
              href="/account"
              className="rounded-full border border-neutral-300 px-6 py-3 text-sm font-semibold"
            >
              View account
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}
