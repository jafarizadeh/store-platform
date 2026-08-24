import type { Metadata } from "next";
import Link from "next/link";

import SiteHeader from "@/components/site-header";

export const metadata: Metadata = {
  title: "Order created",
};

type PageProps = {
  searchParams: Promise<{
    order?: string | string[];
    number?: string | string[];
  }>;
};

function firstParam(
  value: string | string[] | undefined,
): string | null {
  if (Array.isArray(value)) {
    return value[0] ?? null;
  }

  return value ?? null;
}

export default async function CheckoutSuccessPage({
  searchParams,
}: PageProps) {
  const params = await searchParams;

  const rawOrderId = firstParam(
    params.order,
  );

  const rawOrderNumber = firstParam(
    params.number,
  );

  const orderId =
    rawOrderId &&
    /^[0-9a-f-]{36}$/i.test(
      rawOrderId,
    )
      ? rawOrderId
      : null;

  const orderNumber =
    rawOrderNumber &&
    /^BY-\d{4}-\d{8}$/.test(
      rawOrderNumber,
    )
      ? rawOrderNumber
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

          {orderNumber && (
            <div className="mt-8 rounded-2xl bg-neutral-950 p-6 text-white">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-neutral-400">
                Order number
              </p>

              <p className="mt-3 font-mono text-xl font-semibold tracking-wide">
                {orderNumber}
              </p>

              <p className="mt-3 text-xs leading-5 text-neutral-400">
                Keep this number for future
                payment, shipping and support
                references.
              </p>
            </div>
          )}

          {orderId && (
            <details className="mt-4 rounded-2xl border border-neutral-200 p-5">
              <summary className="cursor-pointer text-sm font-medium text-neutral-600">
                Internal order reference
              </summary>

              <p className="mt-3 break-all font-mono text-xs text-neutral-500">
                {orderId}
              </p>
            </details>
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
