import Link from "next/link";
import { notFound } from "next/navigation";

import ProductGallery from "@/components/product-gallery";
import ProductPurchasePanel from "@/components/product-purchase-panel";
import SiteHeader from "@/components/site-header";
import { getProduct } from "@/lib/products-api";

type ProductPageProps = {
  params: Promise<{
    slug: string;
  }>;
};

export default async function ProductPage({
  params,
}: ProductPageProps) {
  const { slug } =
    await params;

  const product =
    await getProduct(slug);

  if (!product) {
    notFound();
  }

  return (
    <main className="min-h-screen bg-white text-black">
      <SiteHeader />

      <section className="mx-auto grid max-w-7xl gap-12 px-6 py-16 lg:grid-cols-2 lg:px-10 lg:py-24">
        <ProductGallery
          productName={
            product.name
          }
          images={
            product.images
          }
        />

        <div className="flex flex-col justify-center">
          <Link
            href="/shop"
            className="mb-8 text-sm text-neutral-500 transition hover:text-black"
          >
            ← Back to Shop
          </Link>

          <p className="mb-3 text-sm uppercase tracking-[0.18em] text-neutral-500">
            {product.category} ·{" "}
            {product.productType}
          </p>

          <h1 className="text-4xl font-semibold tracking-tight md:text-5xl">
            {product.name}
          </h1>

          {product.difficultyLevel !==
            null && (
            <p className="mt-4 text-sm font-medium text-neutral-500">
              Difficulty{" "}
              {
                product.difficultyLevel
              }
              /10
            </p>
          )}

          <p className="mt-6 max-w-xl text-base leading-7 text-neutral-600">
            {
              product.description
            }
          </p>

          <ProductPurchasePanel
            product={product}
          />
        </div>
      </section>
    </main>
  );
}
