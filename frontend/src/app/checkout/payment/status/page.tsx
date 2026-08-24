"use client";

import Link from "next/link";
import {
  useRouter,
} from "next/navigation";
import {
  useEffect,
  useRef,
  useState,
} from "react";

import SiteHeader from "@/components/site-header";
import {
  clearCheckoutOrderIdempotency,
} from "@/lib/orders-client";
import {
  clearPaymentInitiationKey,
  paymentErrorMessage,
  refreshPaymentStatus,
} from "@/lib/payments-client";
import {
  clearPaymentFlow,
  readPaymentFlow,
} from "@/lib/payment-flow";


export default function PaymentStatusPage() {
  const router = useRouter();

  const started = useRef(false);

  const [title, setTitle] =
    useState(
      "Checking payment status…",
    );

  const [message, setMessage] =
    useState<string | null>(null);

  useEffect(() => {
    if (started.current) {
      return;
    }

    started.current = true;

    async function reconcile():
      Promise<void> {
      const flow =
        readPaymentFlow();

      if (!flow) {
        setTitle(
          "Payment reference unavailable.",
        );

        setMessage(
          "The local checkout reference is "
          + "missing. Review your account "
          + "before starting another payment.",
        );

        return;
      }

      try {
        const result =
          await refreshPaymentStatus(
            flow.attemptId,
            flow.provider,
          );

        if (
          result.status === "succeeded"
        ) {
          router.replace(
            (
              "/checkout/success"
              + `?attempt=${encodeURIComponent(
                flow.attemptId,
              )}`
            ),
          );

          return;
        }

        if (
          result.status === "failed"
          || result.status === "cancelled"
        ) {
          clearPaymentInitiationKey(
            flow.paymentId,
            flow.provider,
          );

          clearPaymentFlow();
          clearCheckoutOrderIdempotency();

          setTitle(
            "Payment was not completed.",
          );

          setMessage(
            "No successful payment was "
            + "confirmed. You may safely "
            + "return to checkout.",
          );

          return;
        }

        setTitle(
          "Payment is still pending.",
        );

        setMessage(
          "The provider has not confirmed "
          + "a final result yet. Do not start "
          + "another payment attempt while "
          + "this one remains unresolved.",
        );
      } catch (error) {
        setTitle(
          "Payment status is unresolved.",
        );

        setMessage(
          paymentErrorMessage(error),
        );
      }
    }

    void reconcile();
  }, [
    router,
  ]);

  return (
    <main className="min-h-screen bg-neutral-50 text-neutral-950">
      <SiteHeader />

      <section className="mx-auto max-w-2xl px-6 py-24 lg:px-8">
        <div className="rounded-[2rem] border border-neutral-200 bg-white p-8 sm:p-12">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-neutral-500">
            Payment status
          </p>

          <h1 className="mt-4 text-4xl font-semibold tracking-[-0.04em]">
            {title}
          </h1>

          {message && (
            <div className="mt-7 rounded-2xl bg-neutral-50 p-5 text-sm leading-7 text-neutral-700">
              {message}
            </div>
          )}

          <div className="mt-9 flex flex-wrap gap-3">
            <Link
              href="/account"
              className="rounded-full bg-neutral-950 px-6 py-3 text-sm font-semibold text-white"
            >
              View account
            </Link>

            <Link
              href="/checkout"
              className="rounded-full border border-neutral-300 px-6 py-3 text-sm font-semibold"
            >
              Checkout
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}
