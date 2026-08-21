"use client";

import Image from "next/image";
import Link from "next/link";

import SiteHeader from "@/components/site-header";
import { useCart } from "@/context/cart-context";

export default function CheckoutPage() {
  const { items, totalItems, totalPrice } = useCart();

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
              Add something to your cart before continuing to checkout.
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

  return (
    <main className="min-h-screen bg-white text-neutral-950">
      <SiteHeader />

      <section className="mx-auto max-w-7xl px-6 py-12 lg:px-8 lg:py-16">
        <div className="mb-12">
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-neutral-500">
            Checkout
          </p>

          <h1 className="mt-4 text-5xl font-semibold tracking-[-0.04em]">
            Delivery details.
          </h1>

          <p className="mt-4 max-w-2xl text-lg leading-8 text-neutral-600">
            Enter your contact and delivery information. Payment will be
            connected in a later step.
          </p>
        </div>

        <div className="grid gap-14 lg:grid-cols-[1fr_420px]">
          <form
            className="space-y-10"
            onSubmit={(event) => event.preventDefault()}
          >
            <section>
              <h2 className="text-xl font-semibold">
                Contact information
              </h2>

              <div className="mt-6 grid gap-5 sm:grid-cols-2">
                <label className="block">
                  <span className="text-sm font-medium">
                    First name
                  </span>

                  <input
                    type="text"
                    name="firstName"
                    autoComplete="given-name"
                    required
                    className="mt-2 w-full rounded-2xl border border-neutral-300 bg-white px-4 py-3 outline-none transition focus:border-neutral-950"
                  />
                </label>

                <label className="block">
                  <span className="text-sm font-medium">
                    Last name
                  </span>

                  <input
                    type="text"
                    name="lastName"
                    autoComplete="family-name"
                    required
                    className="mt-2 w-full rounded-2xl border border-neutral-300 bg-white px-4 py-3 outline-none transition focus:border-neutral-950"
                  />
                </label>

                <label className="block sm:col-span-2">
                  <span className="text-sm font-medium">
                    Email
                  </span>

                  <input
                    type="email"
                    name="email"
                    autoComplete="email"
                    required
                    className="mt-2 w-full rounded-2xl border border-neutral-300 bg-white px-4 py-3 outline-none transition focus:border-neutral-950"
                  />
                </label>

                <label className="block sm:col-span-2">
                  <span className="text-sm font-medium">
                    Phone
                  </span>

                  <input
                    type="tel"
                    name="phone"
                    autoComplete="tel"
                    className="mt-2 w-full rounded-2xl border border-neutral-300 bg-white px-4 py-3 outline-none transition focus:border-neutral-950"
                  />
                </label>
              </div>
            </section>

            <section className="border-t border-neutral-200 pt-10">
              <h2 className="text-xl font-semibold">
                Shipping address
              </h2>

              <div className="mt-6 grid gap-5 sm:grid-cols-2">
                <label className="block sm:col-span-2">
                  <span className="text-sm font-medium">
                    Address
                  </span>

                  <input
                    type="text"
                    name="address"
                    autoComplete="street-address"
                    required
                    className="mt-2 w-full rounded-2xl border border-neutral-300 bg-white px-4 py-3 outline-none transition focus:border-neutral-950"
                  />
                </label>

                <label className="block">
                  <span className="text-sm font-medium">
                    Postal code
                  </span>

                  <input
                    type="text"
                    name="postalCode"
                    autoComplete="postal-code"
                    required
                    className="mt-2 w-full rounded-2xl border border-neutral-300 bg-white px-4 py-3 outline-none transition focus:border-neutral-950"
                  />
                </label>

                <label className="block">
                  <span className="text-sm font-medium">
                    City
                  </span>

                  <input
                    type="text"
                    name="city"
                    autoComplete="address-level2"
                    required
                    className="mt-2 w-full rounded-2xl border border-neutral-300 bg-white px-4 py-3 outline-none transition focus:border-neutral-950"
                  />
                </label>

                <label className="block sm:col-span-2">
                  <span className="text-sm font-medium">
                    Country
                  </span>

                  <select
                    name="country"
                    autoComplete="country-name"
                    required
                    defaultValue="France"
                    className="mt-2 w-full rounded-2xl border border-neutral-300 bg-white px-4 py-3 outline-none transition focus:border-neutral-950"
                  >
                    <option>France</option>
                    <option>Belgium</option>
                    <option>Germany</option>
                    <option>Netherlands</option>
                    <option>Spain</option>
                    <option>Italy</option>
                  </select>
                </label>
              </div>
            </section>

            <div className="border-t border-neutral-200 pt-8">
              <button
                type="submit"
                disabled
                className="w-full cursor-not-allowed rounded-full bg-neutral-300 px-8 py-4 text-sm font-semibold text-neutral-500"
              >
                Continue to Payment
              </button>

              <p className="mt-3 text-center text-xs leading-5 text-neutral-400">
                Payment is intentionally disabled until the payment provider
                and checkout architecture are selected.
              </p>
            </div>
          </form>

          <aside className="h-fit rounded-3xl bg-neutral-950 p-7 text-white lg:sticky lg:top-8">
            <p className="text-sm font-medium uppercase tracking-[0.18em] text-neutral-400">
              Order Summary
            </p>

            <div className="mt-7 divide-y divide-neutral-800 border-y border-neutral-800">
              {items.map((item) => (
                <div
                  key={item.slug}
                  className="flex gap-4 py-5"
                >
                  <div className="relative h-20 w-20 shrink-0 overflow-hidden rounded-xl bg-white">
                    <Image
                      src={item.image}
                      alt={item.name}
                      fill
                      sizes="80px"
                      className="object-contain p-2 mix-blend-multiply"
                    />
                  </div>

                  <div className="min-w-0 flex-1">
                    <p className="font-medium">
                      {item.name}
                    </p>

                    <p className="mt-1 text-sm text-neutral-400">
                      Quantity: {item.quantity}
                    </p>
                  </div>

                  <p className="whitespace-nowrap font-medium">
                    €{(item.price * item.quantity).toFixed(2)}
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
                  Subtotal
                </span>

                <span>€{totalPrice.toFixed(2)}</span>
              </div>

              <div className="flex justify-between">
                <span className="text-neutral-400">
                  Shipping
                </span>

                <span>Calculated later</span>
              </div>
            </div>

            <div className="mt-7 flex items-center justify-between border-t border-neutral-700 pt-7">
              <span className="text-neutral-400">
                Total
              </span>

              <span className="text-2xl font-semibold">
                €{totalPrice.toFixed(2)}
              </span>
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
