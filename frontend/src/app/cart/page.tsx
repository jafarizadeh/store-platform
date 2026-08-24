"use client";

import Image from "next/image";
import Link from "next/link";

import SiteHeader from "@/components/site-header";
import { useCart } from "@/context/cart-context";
import { formatMoney } from "@/lib/catalog";

export default function CartPage() {
  const {
    items,
    totalItems,
    totalPriceCents,
    currency,
    addItem,
    decreaseItem,
    removeItem,
    clearCart,
  } = useCart();

  const displayCurrency =
    currency ?? "EUR";

  return (
    <main className="min-h-screen bg-white text-neutral-950">
      <SiteHeader />

      <section className="mx-auto max-w-7xl px-6 py-16 lg:px-8">
        <p className="text-sm font-medium uppercase tracking-[0.2em] text-neutral-500">
          Cart
        </p>

        <h1 className="mt-4 text-5xl font-semibold tracking-[-0.04em]">
          Your cart.
        </h1>

        {items.length === 0 ? (
          <div className="mt-16 rounded-3xl bg-neutral-50 px-8 py-20 text-center">
            <h2 className="text-2xl font-semibold">
              Your cart is empty.
            </h2>

            <Link
              href="/shop"
              className="mt-7 inline-block rounded-full bg-neutral-950 px-7 py-3 text-sm font-medium text-white"
            >
              Browse Products
            </Link>
          </div>
        ) : (
          <div className="mt-14 grid gap-12 lg:grid-cols-[1fr_360px]">
            <div className="divide-y divide-neutral-200 border-y border-neutral-200">
              {items.map((item) => (
                <article
                  key={item.offerId}
                  className="grid grid-cols-[110px_1fr] gap-6 py-7 sm:grid-cols-[140px_1fr]"
                >
                  <div className="relative aspect-square overflow-hidden rounded-2xl bg-neutral-100">
                    <Image
                      src={item.image}
                      alt={
                        item.productName
                      }
                      fill
                      sizes="140px"
                      className="object-contain p-3 mix-blend-multiply"
                    />
                  </div>

                  <div className="flex flex-col justify-between gap-6 sm:flex-row">
                    <div>
                      <Link
                        href={`/shop/${item.productSlug}`}
                        className="text-lg font-semibold hover:text-neutral-500"
                      >
                        {
                          item.productName
                        }
                      </Link>

                      <p className="mt-1 text-sm font-medium text-neutral-600">
                        {item.offerName}
                      </p>

                      <p className="mt-1 text-xs uppercase tracking-[0.1em] text-neutral-400">
                        {item.sku} ·{" "}
                        {
                          item.fulfillmentType
                        }
                      </p>

                      <p className="mt-3 text-sm text-neutral-500">
                        {formatMoney(
                          item.priceCents,
                          item.currency,
                        )}{" "}
                        each
                      </p>

                      <button
                        type="button"
                        onClick={() =>
                          removeItem(
                            item.offerId,
                          )
                        }
                        className="mt-4 text-xs font-medium text-neutral-400 underline hover:text-neutral-950"
                      >
                        Remove
                      </button>
                    </div>

                    <div className="flex items-center justify-between gap-8 sm:flex-col sm:items-end">
                      <div className="flex items-center rounded-full border border-neutral-300">
                        <button
                          type="button"
                          onClick={() =>
                            decreaseItem(
                              item.offerId,
                            )
                          }
                          className="px-4 py-2"
                        >
                          −
                        </button>

                        <span className="min-w-8 text-center text-sm">
                          {
                            item.quantity
                          }
                        </span>

                        <button
                          type="button"
                          onClick={() =>
                            addItem(item)
                          }
                          disabled={
                            item.maxQuantity !==
                              null &&
                            item.quantity >=
                              item.maxQuantity
                          }
                          className="px-4 py-2 disabled:cursor-not-allowed disabled:text-neutral-300"
                        >
                          +
                        </button>
                      </div>

                      <p className="font-semibold">
                        {formatMoney(
                          item.priceCents *
                            item.quantity,
                          item.currency,
                        )}
                      </p>
                    </div>
                  </div>
                </article>
              ))}
            </div>

            <aside className="h-fit rounded-3xl bg-neutral-950 p-8 text-white lg:sticky lg:top-8">
              <p className="text-sm uppercase tracking-[0.18em] text-neutral-400">
                Order Summary
              </p>

              <div className="mt-7 space-y-4 border-b border-neutral-700 pb-7">
                <div className="flex justify-between">
                  <span className="text-neutral-400">
                    Items
                  </span>
                  <span>
                    {totalItems}
                  </span>
                </div>

                <div className="flex justify-between">
                  <span className="text-neutral-400">
                    Subtotal
                  </span>

                  <span>
                    {formatMoney(
                      totalPriceCents,
                      displayCurrency,
                    )}
                  </span>
                </div>

                <div className="flex justify-between">
                  <span className="text-neutral-400">
                    Shipping
                  </span>
                  <span>
                    Calculated later
                  </span>
                </div>
              </div>

              <div className="mt-7 flex items-center justify-between">
                <span className="text-neutral-400">
                  Total
                </span>

                <span className="text-2xl font-semibold">
                  {formatMoney(
                    totalPriceCents,
                    displayCurrency,
                  )}
                </span>
              </div>

              <Link
                href="/checkout"
                className="mt-8 block w-full rounded-full bg-white px-6 py-4 text-center text-sm font-semibold text-neutral-950 transition hover:bg-neutral-200"
              >
                Checkout
              </Link>

              <button
                type="button"
                onClick={clearCart}
                className="mt-4 w-full text-xs text-neutral-500 transition hover:text-white"
              >
                Clear cart
              </button>
            </aside>
          </div>
        )}
      </section>
    </main>
  );
}
