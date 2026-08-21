"use client";

import type { StoreProduct } from "@/lib/products-api";

type ShopClientProps = {
  products: StoreProduct[];
};


import { useState } from "react";
import Image from "next/image";
import Link from "next/link";

import AddToCartButton from "@/components/add-to-cart-button";

import SiteHeader from "@/components/site-header";
export default function ShopClient({ products }: ShopClientProps) {
  const categories = [
    "All",
    ...Array.from(new Set(products.map((product) => product.category))),
  ];
  const [activeCategory, setActiveCategory] = useState("All");

  const filteredProducts =
    activeCategory === "All"
      ? products
      : products.filter(
          (product) => product.category === activeCategory
        );

  return (
    <main className="min-h-screen bg-white text-neutral-950">
      <SiteHeader />

      <section className="mx-auto max-w-7xl px-6 py-16 lg:px-8 lg:py-20">

        <div className="max-w-2xl">
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-neutral-500">
            Shop
          </p>

          <h1 className="mt-4 text-5xl font-semibold tracking-[-0.04em] sm:text-6xl">
            Components for your next build.
          </h1>

          <p className="mt-6 text-lg leading-8 text-neutral-600">
            Raspberry Pi boards, modules, microcontrollers and accessories
            selected for makers, students and real-world projects.
          </p>
        </div>

        <div className="mt-14 flex flex-wrap gap-3 border-b border-neutral-200 pb-6">
          {categories.map((category) => {
            const isActive = activeCategory === category;

            return (
              <button
                key={category}
                type="button"
                onClick={() => setActiveCategory(category)}
                className={
                  isActive
                    ? "rounded-full bg-neutral-950 px-5 py-2.5 text-sm font-medium text-white"
                    : "rounded-full border border-neutral-300 px-5 py-2.5 text-sm font-medium transition hover:bg-neutral-100"
                }
              >
                {category}
              </button>
            );
          })}
        </div>

        <div className="mt-8 flex items-center justify-between">
          <p className="text-sm text-neutral-500">
            {filteredProducts.length}{" "}
            {filteredProducts.length === 1 ? "product" : "products"}
          </p>

          {activeCategory !== "All" && (
            <button
              type="button"
              onClick={() => setActiveCategory("All")}
              className="text-sm font-medium text-neutral-600 hover:text-neutral-950"
            >
              Clear filter
            </button>
          )}
        </div>

        {filteredProducts.length > 0 ? (
          <div className="mt-8 grid gap-x-6 gap-y-14 md:grid-cols-2 lg:grid-cols-3">

            {filteredProducts.map((product) => (
              <article
                key={product.id}
                className="group flex flex-col"
              >

                <Link
                  href={`/shop/${product.slug}`}
                  className="relative aspect-square overflow-hidden rounded-3xl bg-neutral-100"
                >
                  <Image
                    src={product.image}
                    alt={product.name}
                    fill
                    sizes="(max-width: 768px) 100vw, 33vw"
                    className="object-contain p-8 mix-blend-multiply transition-transform duration-500 group-hover:scale-[1.04]"
                  />
                </Link>

                <div className="flex flex-1 flex-col pt-5">

                  <p className="text-xs font-medium uppercase tracking-[0.15em] text-neutral-500">
                    {product.category}
                  </p>

                  <div className="mt-2 flex items-start justify-between gap-4">

                    <div>
                      <Link href={`/shop/${product.slug}`}>
                        <h2 className="text-xl font-semibold transition hover:text-neutral-500">
                          {product.name}
                        </h2>
                      </Link>

                      <p className="mt-2 min-h-[48px] text-sm leading-6 text-neutral-500">
                        {product.description}
                      </p>
                    </div>

                    <span className="whitespace-nowrap font-semibold">
                      €{product.price}
                    </span>

                  </div>

                  <div className="mt-6">
                    <AddToCartButton
                      fullWidth
                      product={{
                        slug: product.slug,
                        name: product.name,
                        price: product.price,
                        image: product.image,
                      }}
                    />
                  </div>

                </div>
              </article>
            ))}

          </div>
        ) : (
          <div className="mt-10 flex min-h-[320px] items-center justify-center rounded-3xl border border-dashed border-neutral-300 bg-neutral-50">

            <div className="text-center">
              <p className="text-xl font-semibold">
                No products here yet.
              </p>

              <p className="mt-3 text-neutral-500">
                Products for this category will be added soon.
              </p>

              <button
                type="button"
                onClick={() => setActiveCategory("All")}
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
