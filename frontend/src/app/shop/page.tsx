import { getProducts } from "@/lib/products-api";

import ShopClient from "./shop-client";

export default async function ShopPage() {
  const products = await getProducts();

  return <ShopClient products={products} />;
}
