"use client";

import {
  useMemo,
  useState,
} from "react";

import AddToCartButton from "@/components/add-to-cart-button";
import {
  formatOfferPrice,
  getPrimaryProductImagePath,
  isOfferAvailable,
  offerAvailabilityLabel,
  type StoreProduct,
} from "@/lib/catalog";

type ProductPurchasePanelProps = {
  product: StoreProduct;
};

export default function ProductPurchasePanel({
  product,
}: ProductPurchasePanelProps) {
  const initialOfferId =
    product.offers[0]?.id ??
    null;

  const [
    selectedOfferId,
    setSelectedOfferId,
  ] = useState<
    number | null
  >(initialOfferId);

  const selectedOffer =
    useMemo(
      () =>
        product.offers.find(
          (offer) =>
            offer.id ===
            selectedOfferId,
        ) ?? null,
      [
        product.offers,
        selectedOfferId,
      ],
    );

  const productImage =
    getPrimaryProductImagePath(
      product,
    );

  if (
    product.offers.length ===
    0
  ) {
    return (
      <div className="mt-8 rounded-2xl bg-neutral-50 p-5 text-sm text-neutral-500">
        This item is not
        currently available for
        purchase.
      </div>
    );
  }

  return (
    <div className="mt-8">
      <p className="text-sm font-semibold">
        Choose an option
      </p>

      <div className="mt-4 space-y-3">
        {product.offers.map(
          (offer) => {
            const selected =
              offer.id ===
              selectedOfferId;

            return (
              <button
                key={offer.id}
                type="button"
                onClick={() =>
                  setSelectedOfferId(
                    offer.id,
                  )
                }
                className={[
                  "w-full rounded-2xl border p-4 text-left transition",
                  selected
                    ? "border-neutral-950 bg-neutral-50"
                    : "border-neutral-200 hover:border-neutral-400",
                ].join(" ")}
              >
                <div className="flex items-start justify-between gap-5">
                  <div>
                    <p className="font-semibold">
                      {offer.name}
                    </p>

                    <p className="mt-1 text-xs uppercase tracking-[0.12em] text-neutral-400">
                      {
                        offer.fulfillmentType
                      }{" "}
                      · {offer.sku}
                    </p>

                    <p className="mt-2 text-sm text-neutral-500">
                      {offerAvailabilityLabel(
                        offer,
                      )}
                    </p>
                  </div>

                  <p className="whitespace-nowrap font-semibold">
                    {formatOfferPrice(
                      offer,
                    )}
                  </p>
                </div>
              </button>
            );
          },
        )}
      </div>

      {selectedOffer && (
        <div className="mt-6">
          {selectedOffer.pricingType ===
            "quote" ||
          selectedOffer.priceCents ===
            null ||
          selectedOffer.currency ===
            null ? (
            <button
              type="button"
              disabled
              className="w-full cursor-not-allowed rounded-full bg-neutral-200 px-6 py-4 text-sm font-semibold text-neutral-500"
            >
              Quote required
            </button>
          ) : (
            <AddToCartButton
              fullWidth
              disabled={
                !isOfferAvailable(
                  selectedOffer,
                )
              }
              label={
                isOfferAvailable(
                  selectedOffer,
                )
                  ? `Add ${selectedOffer.name} to cart`
                  : "Out of stock"
              }
              product={{
                offerId:
                  selectedOffer.id,
                productSlug:
                  product.slug,
                productName:
                  product.name,
                offerName:
                  selectedOffer.name,
                sku:
                  selectedOffer.sku,
                priceCents:
                  selectedOffer.priceCents,
                currency:
                  selectedOffer.currency,
                image:
                  productImage,
                fulfillmentType:
                  selectedOffer.fulfillmentType,
                maxQuantity:
                  selectedOffer.trackInventory
                    ? selectedOffer.stockQuantity
                    : null,
              }}
            />
          )}
        </div>
      )}
    </div>
  );
}
