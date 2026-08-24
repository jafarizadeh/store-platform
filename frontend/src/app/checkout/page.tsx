"use client";

import Image from "next/image";
import Link from "next/link";
import {
  useRouter,
} from "next/navigation";
import {
  useEffect,
  useState,
} from "react";

import SiteHeader from "@/components/site-header";
import { useAuth } from "@/context/auth-context";
import { useCart } from "@/context/cart-context";
import { formatMoney } from "@/lib/catalog";
import {
  clearCheckoutOrderIdempotency,
  createOrder,
  orderErrorMessage,
} from "@/lib/orders-client";
import {
  clearPaymentInitiationKey,
  initiatePayment,
  paymentErrorMessage,
  PaymentRequestError,
  preparePayment,
} from "@/lib/payments-client";
import {
  clearPaymentFlow,
  storePaymentFlow,
} from "@/lib/payment-flow";


const PAYMENT_PROVIDER = "paypal";


export default function CheckoutPage() {
  const router = useRouter();

  const {
    user,
    isLoading: isAuthLoading,
  } = useAuth();

  const {
    items,
    totalItems,
    totalPriceCents,
    currency,
    clearCart,
  } = useCart();

  const [error, setError] =
    useState<string | null>(null);

  const [isSubmitting, setIsSubmitting] =
    useState(false);

  const displayCurrency =
    currency ?? "EUR";

  useEffect(() => {
    if (
      items.length > 0
      && !isAuthLoading
      && !user
    ) {
      router.replace(
        "/login?next=/checkout",
      );
    }
  }, [
    items.length,
    isAuthLoading,
    router,
    user,
  ]);

  async function handlePayment():
    Promise<void> {
    if (
      isSubmitting
      || !user
      || items.length === 0
    ) {
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      const order = await createOrder(
        items.map((item) => ({
          offer_id: item.offerId,
          quantity: item.quantity,
        })),
      );

      const payment =
        await preparePayment(
          order.id,
        );

      const initiation =
        await initiatePayment(
          payment.id,
          PAYMENT_PROVIDER,
        );

      if (
        initiation.status === "succeeded"
      ) {
        clearPaymentInitiationKey(
          payment.id,
          PAYMENT_PROVIDER,
        );

        clearPaymentFlow();
        clearCheckoutOrderIdempotency();
        clearCart();

        router.push(
          (
            "/checkout/success"
              + `?attempt=${encodeURIComponent(
                initiation.attempt_id,
              )}`
          ),
        );

        return;
      }

      if (
        initiation.status !== "pending"
        || !initiation.approval_url
      ) {
        clearPaymentInitiationKey(
          payment.id,
          PAYMENT_PROVIDER,
        );

        throw new PaymentRequestError(
          502,
          "payment_provider_error",
        );
      }

      storePaymentFlow({
        orderId: order.id,
        orderNumber:
          order.order_number,
        paymentId: payment.id,
        attemptId:
          initiation.attempt_id,
        provider: "paypal",
      });

      window.location.assign(
        initiation.approval_url,
      );
    } catch (requestError) {
      if (
        requestError
        instanceof PaymentRequestError
      ) {
        if (
          requestError.code
            === "reservation_expired"
          || requestError.code
            === "order_not_payable"
        ) {
          clearCheckoutOrderIdempotency();
          clearPaymentFlow();
        }

        setError(
          paymentErrorMessage(
            requestError,
          ),
        );
      } else {
        setError(
          orderErrorMessage(
            requestError,
          ),
        );
      }

      setIsSubmitting(false);
    }
  }

  if (items.length === 0) {
    return (
      <main className="min-h-screen bg-white text-neutral-950">
        <SiteHeader />

        <section className="mx-auto max-w-7xl px-6 py-20 lg:px-8">
          <div className="mx-auto max-w-xl rounded-3xl bg-neutral-50 px-8 py-20 text-center">
            <p className="text-sm font-medium uppercase tracking-[0.2em] text-neutral-500">
              Checkout
            </p>

            <h1 className="mt-4 text-4xl font-semibold tracking-[-0.04em]">
              Your cart is empty.
            </h1>

            <p className="mt-4 leading-7 text-neutral-500">
              Add something to your cart
              before continuing.
            </p>

            <Link
              href="/shop"
              className="mt-8 inline-block rounded-full bg-neutral-950 px-7 py-3 text-sm font-medium text-white transition hover:bg-neutral-800"
            >
              Go to Shop
            </Link>
          </div>
        </section>
      </main>
    );
  }

  if (
    isAuthLoading
    || !user
  ) {
    return (
      <main className="min-h-screen bg-white text-neutral-950">
        <SiteHeader />

        <section className="mx-auto max-w-7xl px-6 py-20 lg:px-8">
          <div className="mx-auto max-w-xl rounded-3xl bg-neutral-50 px-8 py-20 text-center">
            <p className="text-sm text-neutral-500">
              Checking your account…
            </p>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-white text-neutral-950">
      <SiteHeader />

      <section className="mx-auto max-w-7xl px-6 py-12 lg:px-8 lg:py-16">
        <div className="mb-12">
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-neutral-500">
            Checkout
          </p>

          <h1 className="mt-4 text-5xl font-semibold tracking-[-0.04em]">
            Review and pay.
          </h1>

          <p className="mt-4 max-w-2xl text-lg leading-8 text-neutral-600">
            Prices, availability and totals
            are verified again by the server
            before a payment attempt begins.
          </p>
        </div>

        <div className="grid gap-14 lg:grid-cols-[1fr_420px]">
          <div className="space-y-6">
            <section className="rounded-3xl border border-neutral-200 p-7">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-neutral-500">
                Customer account
              </p>

              <h2 className="mt-3 text-xl font-semibold">
                Signed in
              </h2>

              <p className="mt-2 break-all text-sm text-neutral-600">
                {user.email}
              </p>
            </section>

            <section className="rounded-3xl border border-neutral-200 p-7">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-neutral-500">
                Payment method
              </p>

              <div className="mt-4 flex items-center justify-between gap-6 rounded-2xl bg-neutral-50 p-5">
                <div>
                  <h2 className="font-semibold">
                    PayPal
                  </h2>

                  <p className="mt-1 text-sm leading-6 text-neutral-500">
                    You will continue to
                    PayPal to approve the
                    payment.
                  </p>
                </div>

                <span className="rounded-full border border-neutral-300 bg-white px-4 py-2 text-xs font-semibold">
                  PayPal
                </span>
              </div>
            </section>

            <section className="rounded-3xl bg-neutral-50 p-7">
              <h2 className="text-xl font-semibold">
                Secure payment flow
              </h2>

              <p className="mt-3 max-w-2xl text-sm leading-7 text-neutral-600">
                ByNET creates the order and
                payment attempt server-side.
                A browser redirect never marks
                an order as paid. Payment is
                confirmed only after the server
                verifies the provider result.
              </p>
            </section>

            {error && (
              <div
                role="alert"
                className="rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm leading-6 text-red-800"
              >
                {error}
              </div>
            )}

            <button
              type="button"
              disabled={isSubmitting}
              onClick={() => {
                void handlePayment();
              }}
              className="w-full rounded-full bg-neutral-950 px-8 py-4 text-sm font-semibold text-white transition hover:bg-neutral-700 disabled:cursor-not-allowed disabled:bg-neutral-400"
            >
              {isSubmitting
                ? "Preparing secure payment..."
                : "Continue with PayPal"}
            </button>

            <p className="text-center text-xs leading-5 text-neutral-400">
              Your cart is kept until payment
              is conclusively confirmed.
            </p>
          </div>

          <aside className="h-fit rounded-3xl bg-neutral-950 p-7 text-white lg:sticky lg:top-8">
            <p className="text-sm font-medium uppercase tracking-[0.18em] text-neutral-400">
              Order Summary
            </p>

            <div className="mt-7 divide-y divide-neutral-800 border-y border-neutral-800">
              {items.map((item) => (
                <div
                  key={item.offerId}
                  className="flex gap-4 py-5"
                >
                  <div className="relative h-20 w-20 shrink-0 overflow-hidden rounded-xl bg-white">
                    <Image
                      src={item.image}
                      alt={item.productName}
                      fill
                      sizes="80px"
                      className="object-contain p-2 mix-blend-multiply"
                    />
                  </div>

                  <div className="min-w-0 flex-1">
                    <p className="font-medium">
                      {item.productName}
                    </p>

                    <p className="mt-1 text-sm text-neutral-400">
                      {item.offerName}
                      {" · "}
                      {item.sku}
                    </p>

                    <p className="mt-1 text-sm text-neutral-400">
                      Quantity:{" "}
                      {item.quantity}
                    </p>
                  </div>

                  <p className="whitespace-nowrap font-medium">
                    {formatMoney(
                      item.priceCents
                        * item.quantity,
                      item.currency,
                    )}
                  </p>
                </div>
              ))}
            </div>

            <div className="mt-7 space-y-4 text-sm">
              <div className="flex justify-between">
                <span className="text-neutral-400">
                  Items
                </span>

                <span>{totalItems}</span>
              </div>

              <div className="flex justify-between">
                <span className="text-neutral-400">
                  Total
                </span>

                <span>
                  {formatMoney(
                    totalPriceCents,
                    displayCurrency,
                  )}
                </span>
              </div>
            </div>

            <div className="mt-7 border-t border-neutral-700 pt-7 text-xs leading-5 text-neutral-400">
              The authoritative payment amount
              is taken from the stored order,
              not from this browser summary.
            </div>

            <Link
              href="/cart"
              className="mt-7 block text-center text-sm text-neutral-400 transition hover:text-white"
            >
              ← Edit cart
            </Link>
          </aside>
        </div>
      </section>
    </main>
  );
}
