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
import { useCart } from "@/context/cart-context";
import {
  clearCheckoutOrderIdempotency,
} from "@/lib/orders-client";
import {
  clearPaymentInitiationKey,
  completePayment,
  paymentErrorMessage,
  refreshPaymentStatus,
} from "@/lib/payments-client";
import {
  clearPaymentFlow,
  readPaymentFlow,
} from "@/lib/payment-flow";


export default function PaymentReturnPage() {
  const router = useRouter();

  const {
    clearCart,
  } = useCart();

  const started =
    useRef(false);

  const [message, setMessage] =
    useState(
      "Verifying your payment…",
    );

  const [error, setError] =
    useState<string | null>(null);

  useEffect(() => {
    if (started.current) {
      return;
    }

    started.current = true;

    async function verify():
      Promise<void> {
      const flow =
        readPaymentFlow();

      if (!flow) {
        setMessage(
          "Payment verification could not start.",
        );

        setError(
          "The local checkout reference is missing. "
          + "Open your account before attempting "
          + "another payment.",
        );

        return;
      }

      try {
        // First reconcile in case a previous
        // capture completed but the browser
        // never received the response.
        const refreshed =
          await refreshPaymentStatus(
            flow.attemptId,
            flow.provider,
          );

        let status =
          refreshed.status;

        if (status === "pending") {
          const completed =
            await completePayment(
              flow.attemptId,
              flow.provider,
            );

          status =
            completed.status;
        }

        if (status === "succeeded") {
          clearPaymentInitiationKey(
            flow.paymentId,
            flow.provider,
          );

          clearPaymentFlow();
          clearCheckoutOrderIdempotency();
          clearCart();

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
          status === "failed"
          || status === "cancelled"
        ) {
          clearPaymentInitiationKey(
            flow.paymentId,
            flow.provider,
          );

          clearPaymentFlow();

          setMessage(
            "Payment was not completed.",
          );

          setError(
            "No successful payment was confirmed. "
            + "You can return to checkout.",
          );

          return;
        }

        setMessage(
          "Payment is still pending.",
        );

        setError(
          "We could not conclusively confirm "
          + "the payment yet. Do not start "
          + "another payment attempt.",
        );
      } catch (requestError) {
        setMessage(
          "Payment verification is pending.",
        );

        setError(
          paymentErrorMessage(
            requestError,
          ),
        );
      }
    }

    void verify();
  }, [
    clearCart,
    router,
  ]);

  return (
    <main className="min-h-screen bg-neutral-50 text-neutral-950">
      <SiteHeader />

      <section className="mx-auto max-w-2xl px-6 py-24 lg:px-8">
        <div className="rounded-[2rem] border border-neutral-200 bg-white p-8 sm:p-12">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-neutral-500">
            Payment verification
          </p>

          <h1 className="mt-4 text-4xl font-semibold tracking-[-0.04em]">
            {message}
          </h1>

          <p className="mt-5 leading-7 text-neutral-600">
            ByNET verifies the provider
            server-side before an order is
            marked as paid.
          </p>

          {error && (
            <div
              role="alert"
              className="mt-7 rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm leading-6 text-amber-900"
            >
              {error}
            </div>
          )}

          {error && (
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href="/account"
                className="rounded-full bg-neutral-950 px-6 py-3 text-sm font-semibold text-white"
              >
                View account
              </Link>

              <Link
                href="/checkout/payment/status"
                className="rounded-full border border-neutral-300 px-6 py-3 text-sm font-semibold"
              >
                Recheck payment status
              </Link>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
