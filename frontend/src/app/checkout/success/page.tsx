import type { Metadata } from "next";

import SiteHeader from "@/components/site-header";

import CheckoutSuccessClient from "./success-client";


export const metadata: Metadata = {
  title: "Payment status",
};


type PageProps = {
  searchParams: Promise<{
    attempt?: string | string[];
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


function validUuid(
  value: string | null,
): string | null {
  return (
    value
    && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
      value,
    )
  )
    ? value
    : null;
}


export default async function CheckoutSuccessPage({
  searchParams,
}: PageProps) {
  const params =
    await searchParams;

  const attemptId =
    validUuid(
      firstParam(
        params.attempt,
      ),
    );

  return (
    <main className="min-h-screen bg-neutral-50 text-neutral-950">
      <SiteHeader />

      <section className="mx-auto max-w-3xl px-6 py-20 lg:px-8 lg:py-28">
        <div className="rounded-[2rem] border border-neutral-200 bg-white p-8 shadow-[0_24px_80px_rgba(0,0,0,0.05)] sm:p-12">
          <CheckoutSuccessClient
            attemptId={attemptId}
          />
        </div>
      </section>
    </main>
  );
}
