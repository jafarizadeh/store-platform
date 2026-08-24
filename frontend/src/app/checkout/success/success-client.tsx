"use client";

import Link from "next/link";
import {
  useEffect,
  useRef,
  useState,
} from "react";

import { useCart } from "@/context/cart-context";
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


type Props = {
  attemptId: string | null;
};


type VerifiedOrder = {
  id: string;
  number: string;
};


type VerificationState =
  | "checking"
  | "succeeded"
  | "pending"
  | "failed"
  | "error";


export default function CheckoutSuccessClient({
  attemptId,
}: Props) {
  const {
    clearCart,
  } = useCart();

  const started =
    useRef(false);

  const [state, setState] =
    useState<VerificationState>(
      "checking",
    );

  const [message, setMessage] =
    useState<string | null>(null);

  const [
    verifiedOrder,
    setVerifiedOrder,
  ] = useState<VerifiedOrder | null>(
    null,
  );

  useEffect(() => {
    if (started.current) {
      return;
    }

    started.current = true;

    if (!attemptId) {
      return;
    }

    const verifiedAttemptId =
      attemptId;

    async function verify():
      Promise<void> {
      try {
        const result =
          await refreshPaymentStatus(
            verifiedAttemptId,
            "paypal",
          );

        if (
          result.status === "succeeded"
        ) {
          const flow =
            readPaymentFlow();

          if (
            flow
            && flow.attemptId
              === verifiedAttemptId
          ) {
            clearPaymentInitiationKey(
              flow.paymentId,
              flow.provider,
            );
          }

          clearPaymentFlow();
          clearCheckoutOrderIdempotency();
          clearCart();

          setVerifiedOrder({
            id: result.order_id,
            number:
              result.order_number,
          });

          setState("succeeded");
          setMessage(null);

          return;
        }

        if (
          result.status === "failed"
          || result.status
            === "cancelled"
        ) {
          setState("failed");

          setMessage(
            "The payment provider did not "
            + "confirm a successful payment.",
          );

          return;
        }

        setState("pending");

        setMessage(
          "The payment is not in a final "
          + "successful state yet.",
        );
      } catch (error) {
        setState("error");

        setMessage(
          paymentErrorMessage(error),
        );
      }
    }

    void verify();
  }, [
    attemptId,
    clearCart,
  ]);

  if (!attemptId) {
    return (
      <>
        <p className="mt-8 text-xs font-semibold uppercase tracking-[0.24em] text-neutral-500">
          Payment not confirmed
        </p>

        <h1 className="mt-4 text-4xl font-semibold tracking-[-0.05em] sm:text-5xl">
          A valid payment reference is required.
        </h1>

        <div
          role="alert"
          className="mt-7 rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm leading-7 text-amber-900"
        >
          This page cannot show an order as
          paid without a valid payment attempt
          that can be verified by the server.
        </div>

        <div className="mt-9 flex flex-wrap gap-3">
          <Link
            href="/account"
            className="rounded-full bg-neutral-950 px-6 py-3 text-sm font-semibold text-white"
          >
            View account
          </Link>
        </div>
      </>
    );
  }

  if (state === "checking") {
    return (
      <>
        <p className="mt-8 text-xs font-semibold uppercase tracking-[0.24em] text-neutral-500">
          Verifying payment
        </p>

        <h1 className="mt-4 text-4xl font-semibold tracking-[-0.05em] sm:text-5xl">
          Confirming with the server…
        </h1>

        <p className="mt-5 leading-7 text-neutral-600">
          The browser redirect alone is not
          treated as proof of payment.
        </p>
      </>
    );
  }

  if (
    state !== "succeeded"
    || !verifiedOrder
  ) {
    return (
      <>
        <p className="mt-8 text-xs font-semibold uppercase tracking-[0.24em] text-neutral-500">
          Payment not confirmed
        </p>

        <h1 className="mt-4 text-4xl font-semibold tracking-[-0.05em] sm:text-5xl">
          We cannot show this order as paid.
        </h1>

        {message && (
          <div
            role="alert"
            className="mt-7 rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm leading-7 text-amber-900"
          >
            {message}
          </div>
        )}

        <div className="mt-9 flex flex-wrap gap-3">
          <Link
            href="/checkout/payment/status"
            className="rounded-full bg-neutral-950 px-6 py-3 text-sm font-semibold text-white"
          >
            Check payment status
          </Link>

          <Link
            href="/account"
            className="rounded-full border border-neutral-300 px-6 py-3 text-sm font-semibold"
          >
            View account
          </Link>
        </div>
      </>
    );
  }

  return (
    <>
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-50 text-xl text-emerald-700">
        ✓
      </div>

      <p className="mt-8 text-xs font-semibold uppercase tracking-[0.24em] text-emerald-700">
        Payment confirmed
      </p>

      <h1 className="mt-4 text-4xl font-semibold tracking-[-0.05em] sm:text-5xl">
        Order paid.
      </h1>

      <p className="mt-5 max-w-xl text-base leading-7 text-neutral-600">
        The payment and order identity were
        verified from server-side state.
      </p>

      <div className="mt-8 rounded-2xl bg-neutral-950 p-6 text-white">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-neutral-400">
          Order number
        </p>

        <p className="mt-3 font-mono text-xl font-semibold tracking-wide">
          {verifiedOrder.number}
        </p>
      </div>

      <details className="mt-4 rounded-2xl border border-neutral-200 p-5">
        <summary className="cursor-pointer text-sm font-medium text-neutral-600">
          Internal order reference
        </summary>

        <p className="mt-3 break-all font-mono text-xs text-neutral-500">
          {verifiedOrder.id}
        </p>
      </details>

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
    </>
  );
}
