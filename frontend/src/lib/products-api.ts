import "server-only";

export type ApiProduct = {
  id: number;
  slug: string;
  name: string;
  description: string | null;
  category: string;
  image_path: string | null;
  price_cents: number;
  currency: string;
  stock_quantity: number;
};

export type StoreProduct = {
  id: number;
  slug: string;
  name: string;
  description: string;
  category: string;
  image: string;
  price: number;
  priceCents: number;
  currency: string;
  stockQuantity: number;
};

const backendApiUrl = process.env.BACKEND_API_URL;

if (!backendApiUrl) {
  throw new Error("BACKEND_API_URL is not configured");
}

async function backendFetch(path: string): Promise<Response> {
  const url = new URL(path, backendApiUrl);

  return fetch(url, {
    cache: "no-store",
    headers: {
      Accept: "application/json",
    },
    signal: AbortSignal.timeout(5000),
  });
}

function toStoreProduct(product: ApiProduct): StoreProduct {
  return {
    id: product.id,
    slug: product.slug,
    name: product.name,
    description: product.description ?? "",
    category: product.category,
    image: product.image_path ?? "/assets/products/placeholder.png",
    price: product.price_cents / 100,
    priceCents: product.price_cents,
    currency: product.currency,
    stockQuantity: product.stock_quantity,
  };
}

export async function getProducts(): Promise<StoreProduct[]> {
  const response = await backendFetch("/api/v1/products");

  if (!response.ok) {
    throw new Error(
      `Backend product request failed with status ${response.status}`,
    );
  }

  const products: ApiProduct[] = await response.json();

  return products.map(toStoreProduct);
}

export async function getProduct(
  slug: string,
): Promise<StoreProduct | null> {
  const response = await backendFetch(
    `/api/v1/products/${encodeURIComponent(slug)}`,
  );

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error(
      `Backend product request failed with status ${response.status}`,
    );
  }

  const product: ApiProduct = await response.json();

  return toStoreProduct(product);
}

export function formatProductPrice(
  product: Pick<StoreProduct, "priceCents" | "currency">,
): string {
  return new Intl.NumberFormat("en", {
    style: "currency",
    currency: product.currency,
  }).format(product.priceCents / 100);
}
