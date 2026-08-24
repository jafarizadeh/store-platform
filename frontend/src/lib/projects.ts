import type {
  StoreOffer,
  StoreProduct,
} from "@/lib/catalog";

export function isProjectCatalogEntry(
  product: Pick<
    StoreProduct,
    "productType"
  >,
): boolean {
  return (
    product.productType === "kit" ||
    product.productType === "project" ||
    product.productType === "solution"
  );
}

export function projectTypeLabel(
  product: Pick<
    StoreProduct,
    "productType"
  >,
): string {
  switch (product.productType) {
    case "project":
      return "Project";
    case "solution":
      return "Ready-made solution";
    case "kit":
      return "Project kit";
    default:
      return "Build";
  }
}

export function projectOfferLabel(
  offer: Pick<
    StoreOffer,
    "fulfillmentType"
  >,
): string {
  switch (offer.fulfillmentType) {
    case "digital":
      return "Guide / software";
    case "service":
      return "Complete solution";
    case "physical":
      return "Parts kit";
  }
}

export function projectAvailabilityLabel(
  offer: Pick<
    StoreOffer,
    | "pricingType"
    | "trackInventory"
    | "stockQuantity"
  >,
): string {
  if (offer.pricingType === "quote") {
    return "Quote required";
  }

  if (
    offer.trackInventory &&
    offer.stockQuantity <= 0
  ) {
    return "Out of stock";
  }

  return "Available";
}
