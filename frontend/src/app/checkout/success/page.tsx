import type { Metadata } from "next";
import Link from "next/link";

import SiteHeader from "@/components/site-header";

export const metadata: Metadata = {
  title: "Order created",
};

type PageProps = {
  searchParams: Promise<{
    order?: string | string[];
  }>;
};

export default async function CheckoutSuccessPage({
  searchParams,
}: PageProps) {
  const params = await searchParams;

  const rawOrderId =
    Array.isArray(params.order)
      ? params.order[0]
      : params.order;

  const orderId =
    rawOrderId &&
    /^[0-9a-f-]{36}$/i.test(
      rawOrderId,
    )
      ? rawOrderId
      : null;

  return (
    <main className="min-h-screen bg-neutral-50 text-neutral-950">
      <SiteHeader />

      <section className="mx-auto max-w-3xl px-6 py-20 lg:px-8 lg:py-28">
        <div className="rounded-[2rem] border border-neutral-200 bg-white p-8 shadow-[0_24px_80px_rgba(0,0,0,0.05)] sm:p-12">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-50 text-xl text-emerald-700">
            ✓
          </div>

          <p className="mt-8 text-xs font-semibold uppercase tracking-[0.24em] text-neutral-500">
            Pending order created
          </p>

          <h1 className="mt-4 text-4xl font-semibold tracking-[-0.05em] sm:text-5xl">
            Order saved.
          </h1>

          <p className="mt-5 max-w-xl text-base leading-7 text-neutral-600">
            Your order is linked to your
            ByNET account. Payment has not
            been charged or connected yet.
          </p>

          {orderId && (
            <div className="mt-8 rounded-2xl bg-neutral-50 p-5">
              <p className="text-xs uppercase tracking-[0.18em] text-neutral-500">
                Order ID
              </p>

              <p className="mt-2 break-all font-mono text-sm">
                {orderId}
              </p>
            </div>
          )}

          <div className="mt-9 flex flex-wrap gap-3">
            <Link
              href="/account"
              className="rounded-full bg-neutral-950 px-6 py-3 text-sm font-semibold text-white transition hover:bg-neutral-700"
            >
              View account
            </Link>

            <Link
              href="/shop"
              className="rounded-full border border-neutral-300 px-6 py-3 text-sm font-semibold transition hover:border-neutral-950"
            >
              Continue shopping
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}
