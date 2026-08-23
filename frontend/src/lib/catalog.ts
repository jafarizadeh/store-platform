export type StoreProductImage = {
  id: number;
  imagePath: string;
  altText: string | null;
  position: number;
  isPrimary: boolean;
};

export type StoreOffer = {
  id: number;
  sku: string;
  name: string;
  pricingType: "fixed" | "quote";
  fulfillmentType:
    | "physical"
    | "digital"
    | "service";
  priceCents: number | null;
  currency: string | null;
  trackInventory: boolean;
  stockQuantity: number;
  position: number;
};

export type StoreProduct = {
  id: number;
  slug: string;
  name: string;
  description: string;
  productType:
    | "component"
    | "kit"
    | "project"
    | "solution"
    | "service";
  category: string;
  difficultyLevel: number | null;
  images: StoreProductImage[];
  offers: StoreOffer[];
};

export const PRODUCT_PLACEHOLDER_IMAGE =
  "/assets/products/placeholder.png";

export function getPrimaryProductImage(
  product: Pick<
    StoreProduct,
    "images"
  >,
): StoreProductImage | null {
  return (
    product.images.find(
      (image) =>
        image.isPrimary,
    ) ??
    product.images[0] ??
    null
  );
}

export function getPrimaryProductImagePath(
  product: Pick<
    StoreProduct,
    "images"
  >,
): string {
  return (
    getPrimaryProductImage(product)
      ?.imagePath ??
    PRODUCT_PLACEHOLDER_IMAGE
  );
}

export function getPrimaryOffer(
  product: Pick<
    StoreProduct,
    "offers"
  >,
): StoreOffer | null {
  return (
    product.offers.find(
      (offer) =>
        offer.pricingType ===
          "fixed" &&
        offer.priceCents !==
          null &&
        offer.currency !== null,
    ) ??
    product.offers[0] ??
    null
  );
}

export function formatMoney(
  priceCents: number,
  currency: string,
): string {
  return new Intl.NumberFormat(
    "en",
    {
      style: "currency",
      currency,
    },
  ).format(
    priceCents / 100,
  );
}

export function formatOfferPrice(
  offer: Pick<
    StoreOffer,
    | "pricingType"
    | "priceCents"
    | "currency"
  >,
): string {
  if (
    offer.pricingType ===
      "quote" ||
    offer.priceCents === null ||
    offer.currency === null
  ) {
    return "Request a quote";
  }

  return formatMoney(
    offer.priceCents,
    offer.currency,
  );
}

export function isOfferAvailable(
  offer: Pick<
    StoreOffer,
    | "pricingType"
    | "trackInventory"
    | "stockQuantity"
  >,
): boolean {
  if (
    offer.pricingType !== "fixed"
  ) {
    return false;
  }

  if (!offer.trackInventory) {
    return true;
  }

  return (
    offer.stockQuantity > 0
  );
}

export function offerAvailabilityLabel(
  offer: Pick<
    StoreOffer,
    | "pricingType"
    | "trackInventory"
    | "stockQuantity"
    | "fulfillmentType"
  >,
): string {
  if (
    offer.pricingType === "quote"
  ) {
    return "Quote required";
  }

  if (!offer.trackInventory) {
    if (
      offer.fulfillmentType ===
      "digital"
    ) {
      return "Digital delivery";
    }

    return "Available";
  }

  if (
    offer.stockQuantity <= 0
  ) {
    return "Out of stock";
  }

  return `${offer.stockQuantity} in stock`;
}
