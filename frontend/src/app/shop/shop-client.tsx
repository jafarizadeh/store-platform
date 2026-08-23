"use client";

import Image from "next/image";
import Link from "next/link";
import { useMemo, useState } from "react";

import AddToCartButton from "@/components/add-to-cart-button";
import SiteHeader from "@/components/site-header";
import {
  formatOfferPrice,
  getPrimaryOffer,
  getPrimaryProductImagePath,
  isOfferAvailable,
  type StoreProduct,
} from "@/lib/catalog";

type ShopClientProps = {
  products: StoreProduct[];
  initialSearchTerm?: string;
  initialCategory?: string;
};

export default function ShopClient({
  products,
  initialSearchTerm = "",
  initialCategory = "",
}: ShopClientProps) {
  const categories = [
    "All",
    ...Array.from(
      new Set(
        products.map(
          (product) =>
            product.category,
        ),
      ),
    ),
  ];

  const initialCategoryValue =
    categories.includes(initialCategory)
      ? initialCategory
      : "All";

  const [
    activeCategory,
    setActiveCategory,
  ] = useState(initialCategoryValue);

  const [
    searchTerm,
    setSearchTerm,
  ] = useState(initialSearchTerm);

  const filteredProducts = useMemo(() => {
    const query = searchTerm
      .trim()
      .toLowerCase();

    return products.filter((product) => {
      const matchesCategory =
        activeCategory === "All" ||
        product.category === activeCategory;

      if (!matchesCategory) {
        return false;
      }

      if (!query) {
        return true;
      }

      const searchableValues = [
        product.name,
        product.description,
        product.category,
        product.productType,
        ...product.offers.flatMap((offer) => [
          offer.name,
          offer.sku,
        ]),
      ];

      return searchableValues.some((value) =>
        value.toLowerCase().includes(query),
      );
    });
  }, [
    activeCategory,
    products,
    searchTerm,
  ]);

  return (
    <main className="min-h-screen bg-white text-neutral-950">
      <SiteHeader />

      <section className="mx-auto max-w-7xl px-6 py-16 lg:px-8 lg:py-20">
        <div className="max-w-2xl">
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-neutral-500">
            Shop
          </p>

          <h1 className="mt-4 text-5xl font-semibold tracking-[-0.04em] sm:text-6xl">
            Build it. Learn it. Use
            it.
          </h1>

          <p className="mt-6 text-lg leading-8 text-neutral-600">
            Components, kits,
            projects, complete
            solutions and services
            built around Raspberry Pi
            and real-world systems.
          </p>
        </div>

        <div className="mt-10 max-w-2xl">
          <label
            htmlFor="shop-search"
            className="sr-only"
          >
            Search products
          </label>

          <div className="flex items-center gap-3 rounded-full border border-neutral-300 px-5 transition focus-within:border-neutral-950">
            <svg
              aria-hidden="true"
              viewBox="0 0 24 24"
              fill="none"
              className="h-5 w-5 shrink-0 text-neutral-400"
            >
              <path
                d="m21 21-4.35-4.35m2.35-5.15A7.5 7.5 0 1 1 4 11.5a7.5 7.5 0 0 1 15 0Z"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
              />
            </svg>

            <input
              id="shop-search"
              type="search"
              value={searchTerm}
              onChange={(event) =>
                setSearchTerm(event.target.value)
              }
              placeholder="Search products, sensors, cameras, SKU..."
              className="min-w-0 flex-1 bg-transparent py-3.5 text-sm outline-none placeholder:text-neutral-400"
            />

            {searchTerm && (
              <button
                type="button"
                onClick={() =>
                  setSearchTerm("")
                }
                className="text-xs font-semibold text-neutral-500 transition hover:text-neutral-950"
              >
                Clear
              </button>
            )}
          </div>
        </div>

        <div className="mt-8 flex flex-wrap gap-3 border-b border-neutral-200 pb-6">
          {categories.map(
            (category) => {
              const isActive =
                activeCategory ===
                category;

              return (
                <button
                  key={category}
                  type="button"
                  onClick={() =>
                    setActiveCategory(
                      category,
                    )
                  }
                  className={
                    isActive
                      ? "rounded-full bg-neutral-950 px-5 py-2.5 text-sm font-medium text-white"
                      : "rounded-full border border-neutral-300 px-5 py-2.5 text-sm font-medium transition hover:bg-neutral-100"
                  }
                >
                  {category}
                </button>
              );
            },
          )}
        </div>

        <div className="mt-8 flex items-center justify-between">
          <p className="text-sm text-neutral-500">
            {
              filteredProducts.length
            }{" "}
            {filteredProducts.length ===
            1
              ? "product"
              : "products"}
          </p>

          {activeCategory !==
            "All" && (
            <button
              type="button"
              onClick={() =>
                setActiveCategory(
                  "All",
                )
              }
              className="text-sm font-medium text-neutral-600 hover:text-neutral-950"
            >
              Clear filter
            </button>
          )}
        </div>

        {filteredProducts.length >
        0 ? (
          <div className="mt-8 grid gap-x-6 gap-y-14 md:grid-cols-2 lg:grid-cols-3">
            {filteredProducts.map(
              (product) => {
                const primaryOffer =
                  getPrimaryOffer(
                    product,
                  );

                const primaryImage =
                  getPrimaryProductImagePath(
                    product,
                  );

                const quickAdd =
                  product.offers
                    .length === 1 &&
                  primaryOffer !==
                    null &&
                  primaryOffer.pricingType ===
                    "fixed" &&
                  primaryOffer.priceCents !==
                    null &&
                  primaryOffer.currency !==
                    null;

                return (
                  <article
                    key={product.id}
                    className="group flex flex-col"
                  >
                    <Link
                      href={`/shop/${product.slug}`}
                      className="relative aspect-square overflow-hidden rounded-3xl bg-neutral-100"
                    >
                      <Image
                        src={
                          primaryImage
                        }
                        alt={
                          product.name
                        }
                        fill
                        sizes="(max-width: 768px) 100vw, 33vw"
                        className="object-contain p-8 mix-blend-multiply transition-transform duration-500 group-hover:scale-[1.04]"
                      />
                    </Link>

                    <div className="flex flex-1 flex-col pt-5">
                      <p className="text-xs font-medium uppercase tracking-[0.15em] text-neutral-500">
                        {
                          product.category
                        }{" "}
                        ·{" "}
                        {
                          product.productType
                        }
                      </p>

                      <div className="mt-2 flex items-start justify-between gap-4">
                        <div>
                          <Link
                            href={`/shop/${product.slug}`}
                          >
                            <h2 className="text-xl font-semibold transition hover:text-neutral-500">
                              {
                                product.name
                              }
                            </h2>
                          </Link>

                          <p className="mt-2 min-h-[48px] text-sm leading-6 text-neutral-500">
                            {
                              product.description
                            }
                          </p>
                        </div>

                        <span className="whitespace-nowrap font-semibold">
                          {primaryOffer
                            ? formatOfferPrice(
                                primaryOffer,
                              )
                            : "Unavailable"}
                        </span>
                      </div>

                      <div className="mt-6">
                        {quickAdd &&
                        primaryOffer &&
                        primaryOffer.priceCents !==
                          null &&
                        primaryOffer.currency !==
                          null ? (
                          <AddToCartButton
                            fullWidth
                            disabled={
                              !isOfferAvailable(
                                primaryOffer,
                              )
                            }
                            label={
                              isOfferAvailable(
                                primaryOffer,
                              )
                                ? "Add to cart"
                                : "Out of stock"
                            }
                            product={{
                              offerId:
                                primaryOffer.id,
                              productSlug:
                                product.slug,
                              productName:
                                product.name,
                              offerName:
                                primaryOffer.name,
                              sku:
                                primaryOffer.sku,
                              priceCents:
                                primaryOffer.priceCents,
                              currency:
                                primaryOffer.currency,
                              image:
                                primaryImage,
                              fulfillmentType:
                                primaryOffer.fulfillmentType,
                              maxQuantity:
                                primaryOffer.trackInventory
                                  ? primaryOffer.stockQuantity
                                  : null,
                            }}
                          />
                        ) : (
                          <Link
                            href={`/shop/${product.slug}`}
                            className="block w-full rounded-full bg-neutral-950 px-6 py-3 text-center text-sm font-semibold text-white transition hover:bg-neutral-700"
                          >
                            View options
                          </Link>
                        )}
                      </div>
                    </div>
                  </article>
                );
              },
            )}
          </div>
        ) : (
          <div className="mt-10 flex min-h-[320px] items-center justify-center rounded-3xl border border-dashed border-neutral-300 bg-neutral-50">
            <div className="text-center">
              <p className="text-xl font-semibold">
                No products here yet.
              </p>

              <button
                type="button"
                onClick={() =>
                  setActiveCategory(
                    "All",
                  )
                }
                className="mt-6 rounded-full bg-neutral-950 px-6 py-3 text-sm font-medium text-white"
              >
                View all products
              </button>
            </div>
          </div>
        )}
      </section>
    </main>
  );
}
