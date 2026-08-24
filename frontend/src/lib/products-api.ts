import "server-only";

import type {
  StoreOffer,
  StoreProduct,
  StoreProductImage,
} from "@/lib/catalog";

export type ApiProductImage = {
  id: number;
  image_path: string;
  alt_text: string | null;
  position: number;
  is_primary: boolean;
};

export type ApiProductOffer = {
  id: number;
  sku: string;
  name: string;
  pricing_type:
    | "fixed"
    | "quote";
  fulfillment_type:
    | "physical"
    | "digital"
    | "service";
  price_cents: number | null;
  currency: string | null;
  track_inventory: boolean;
  stock_quantity: number;
  position: number;
};

export type ApiProduct = {
  id: number;
  slug: string;
  name: string;
  description: string | null;
  product_type:
    | "component"
    | "kit"
    | "project"
    | "solution"
    | "service";
  category: string;
  difficulty_level: number | null;
  images: ApiProductImage[];
  offers: ApiProductOffer[];
};

const backendApiUrl =
  process.env.BACKEND_API_URL;

if (!backendApiUrl) {
  throw new Error(
    "BACKEND_API_URL is not configured",
  );
}

async function backendFetch(
  path: string,
): Promise<Response> {
  const url = new URL(
    path,
    backendApiUrl,
  );

  return fetch(url, {
    cache: "no-store",
    headers: {
      Accept:
        "application/json",
    },
    signal:
      AbortSignal.timeout(
        5000,
      ),
  });
}

function toStoreImage(
  image: ApiProductImage,
): StoreProductImage {
  return {
    id: image.id,
    imagePath:
      image.image_path,
    altText:
      image.alt_text,
    position:
      image.position,
    isPrimary:
      image.is_primary,
  };
}

function toStoreOffer(
  offer: ApiProductOffer,
): StoreOffer {
  return {
    id: offer.id,
    sku: offer.sku,
    name: offer.name,
    pricingType:
      offer.pricing_type,
    fulfillmentType:
      offer.fulfillment_type,
    priceCents:
      offer.price_cents,
    currency:
      offer.currency,
    trackInventory:
      offer.track_inventory,
    stockQuantity:
      offer.stock_quantity,
    position:
      offer.position,
  };
}

function toStoreProduct(
  product: ApiProduct,
): StoreProduct {
  const images = product.images
    .map(toStoreImage)
    .sort(
      (left, right) =>
        left.position -
          right.position ||
        left.id - right.id,
    );

  const offers = product.offers
    .map(toStoreOffer)
    .sort(
      (left, right) =>
        left.position -
          right.position ||
        left.id - right.id,
    );

  return {
    id: product.id,
    slug: product.slug,
    name: product.name,
    description:
      product.description ?? "",
    productType:
      product.product_type,
    category:
      product.category,
    difficultyLevel:
      product.difficulty_level,
    images,
    offers,
  };
}

export async function getProducts(): Promise<
  StoreProduct[]
> {
  const response =
    await backendFetch(
      "/api/v1/products",
    );

  if (!response.ok) {
    throw new Error(
      `Backend product request failed with status ${response.status}`,
    );
  }

  const products: ApiProduct[] =
    await response.json();

  return products.map(
    toStoreProduct,
  );
}

export async function getProduct(
  slug: string,
): Promise<StoreProduct | null> {
  const response =
    await backendFetch(
      `/api/v1/products/${encodeURIComponent(slug)}`,
    );

  if (
    response.status === 404
  ) {
    return null;
  }

  if (!response.ok) {
    throw new Error(
      `Backend product request failed with status ${response.status}`,
    );
  }

  const product: ApiProduct =
    await response.json();

  return toStoreProduct(
    product,
  );
}
