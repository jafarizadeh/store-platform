import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";

import AddToCartButton from "@/components/add-to-cart-button";
import SiteHeader from "@/components/site-header";
import {
  formatProductPrice,
  getProduct,
} from "@/lib/products-api";

type ProductPageProps = {
  params: Promise<{
    slug: string;
  }>;
};

export default async function ProductPage({
  params,
}: ProductPageProps) {
  const { slug } = await params;
  const product = await getProduct(slug);

  if (!product) {
    notFound();
  }

  return (
    <main className="min-h-screen bg-white text-black">
      <SiteHeader />

      <section className="mx-auto grid max-w-7xl gap-12 px-6 py-16 lg:grid-cols-2 lg:px-10 lg:py-24">
        <div className="flex min-h-[420px] items-center justify-center bg-neutral-50 p-8">
          <Image
            src={product.image}
            alt={product.name}
            width={700}
            height={700}
            className="h-auto max-h-[520px] w-auto object-contain mix-blend-multiply"
            priority
          />
        </div>

        <div className="flex flex-col justify-center">
          <Link
            href="/shop"
            className="mb-8 text-sm text-neutral-500 transition hover:text-black"
          >
            ← Back to Shop
          </Link>

          <p className="mb-3 text-sm uppercase tracking-[0.18em] text-neutral-500">
            {product.category}
          </p>

          <h1 className="text-4xl font-semibold tracking-tight md:text-5xl">
            {product.name}
          </h1>

          <p className="mt-6 max-w-xl text-base leading-7 text-neutral-600">
            {product.description}
          </p>

          <p className="mt-8 text-2xl font-medium">
            {formatProductPrice(product)}
          </p>

          <p className="mt-3 text-sm text-neutral-500">
            {product.stockQuantity > 0
              ? `${product.stockQuantity} in stock`
              : "Out of stock"}
          </p>

          <div className="mt-8 max-w-sm">
            <AddToCartButton
              product={{
                slug: product.slug,
                name: product.name,
                price: product.price,
                image: product.image,
              }}
            />
          </div>
        </div>
      </section>
    </main>
  );
}
