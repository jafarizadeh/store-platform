import { getProducts } from "@/lib/products-api";

import ShopClient from "./shop-client";

type ShopPageProps = {
  searchParams: Promise<{
    q?: string | string[];
    category?: string | string[];
  }>;
};

function getSingleParam(
  value: string | string[] | undefined,
): string {
  if (Array.isArray(value)) {
    return value[0] ?? "";
  }

  return value ?? "";
}

export default async function ShopPage({
  searchParams,
}: ShopPageProps) {
  const [products, params] = await Promise.all([
    getProducts(),
    searchParams,
  ]);

  return (
    <ShopClient
      products={products}
      initialSearchTerm={getSingleParam(params.q)}
      initialCategory={getSingleParam(params.category)}
    />
  );
}
