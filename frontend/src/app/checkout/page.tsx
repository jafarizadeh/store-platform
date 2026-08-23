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
  createOrder,
  orderErrorMessage,
} from "@/lib/orders-client";

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
      items.length > 0 &&
      !isAuthLoading &&
      !user
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

  async function handleCreateOrder(): Promise<void> {
    if (
      isSubmitting ||
      !user ||
      items.length === 0
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

      clearCart();

      router.push(
        `/checkout/success?order=${encodeURIComponent(
          order.id,
        )}`,
      );
    } catch (requestError) {
      setError(
        orderErrorMessage(
          requestError,
        ),
      );
    } finally {
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
    isAuthLoading ||
    !user
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
            Review your order.
          </h1>

          <p className="mt-4 max-w-2xl text-lg leading-8 text-neutral-600">
            Create a pending order from
            your cart. Prices, availability
            and totals are verified again
            by the server.
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

            <section className="rounded-3xl bg-neutral-50 p-7">
              <h2 className="text-xl font-semibold">
                What happens next?
              </h2>

              <p className="mt-3 max-w-2xl text-sm leading-7 text-neutral-600">
                This creates a pending
                order linked to your
                account. Payment and
                delivery details are not
                collected yet and will be
                added in the next checkout
                stages.
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
                void handleCreateOrder();
              }}
              className="w-full rounded-full bg-neutral-950 px-8 py-4 text-sm font-semibold text-white transition hover:bg-neutral-700 disabled:cursor-not-allowed disabled:bg-neutral-400"
            >
              {isSubmitting
                ? "Creating order..."
                : "Create pending order"}
            </button>

            <p className="text-center text-xs leading-5 text-neutral-400">
              No payment will be charged
              at this stage.
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
                  Estimated subtotal
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
              The final stored total is
              calculated from current
              server-side offer prices.
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
