"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react";

export type CartProduct = {
  offerId: number;
  productSlug: string;
  productName: string;
  offerName: string;
  sku: string;
  priceCents: number;
  currency: string;
  image: string;
  fulfillmentType:
    | "physical"
    | "digital"
    | "service";
  maxQuantity: number | null;
};

export type CartItem =
  CartProduct & {
    quantity: number;
  };

export type CartAddIssue =
  | "currency-mismatch"
  | "quantity-limit"
  | null;

type CartContextType = {
  items: CartItem[];
  totalItems: number;
  totalPriceCents: number;
  currency: string | null;
  canAddItem: (
    product: CartProduct,
  ) => CartAddIssue;
  addItem: (
    product: CartProduct,
  ) => void;
  decreaseItem: (
    offerId: number,
  ) => void;
  removeItem: (
    offerId: number,
  ) => void;
  clearCart: () => void;
};

const CartContext =
  createContext<
    CartContextType | undefined
  >(undefined);

const emptySubscribe =
  () => () => {};

function isCartItem(
  value: unknown,
): value is CartItem {
  if (
    typeof value !== "object" ||
    value === null
  ) {
    return false;
  }

  const item =
    value as Partial<CartItem>;

  return (
    Number.isInteger(
      item.offerId,
    ) &&
    typeof item.productSlug ===
      "string" &&
    typeof item.productName ===
      "string" &&
    typeof item.offerName ===
      "string" &&
    typeof item.sku === "string" &&
    Number.isInteger(
      item.priceCents,
    ) &&
    (item.priceCents ?? -1) >= 0 &&
    typeof item.currency ===
      "string" &&
    typeof item.image === "string" &&
    (
      item.fulfillmentType ===
        "physical" ||
      item.fulfillmentType ===
        "digital" ||
      item.fulfillmentType ===
        "service"
    ) &&
    (
      item.maxQuantity === null ||
      (
        Number.isInteger(
          item.maxQuantity,
        ) &&
        (item.maxQuantity ?? -1) >=
          0
      )
    ) &&
    Number.isInteger(
      item.quantity,
    ) &&
    (item.quantity ?? 0) > 0
  );
}

function getStoredCart(): CartItem[] {
  if (
    typeof window === "undefined"
  ) {
    return [];
  }

  const saved =
    window.localStorage.getItem(
      "bynet-cart-v2",
    );

  if (!saved) {
    return [];
  }

  try {
    const parsed: unknown =
      JSON.parse(saved);

    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed.filter(
      isCartItem,
    );
  } catch {
    return [];
  }
}

export function CartProvider({
  children,
}: {
  children: ReactNode;
}) {
  const [items, setItems] =
    useState<CartItem[]>(
      getStoredCart,
    );

  const hydrated =
    useSyncExternalStore(
      emptySubscribe,
      () => true,
      () => false,
    );

  useEffect(() => {
    if (!hydrated) {
      return;
    }

    window.localStorage.setItem(
      "bynet-cart-v2",
      JSON.stringify(items),
    );
  }, [items, hydrated]);

  const visibleItems =
    hydrated ? items : [];

  const currency =
    visibleItems[0]?.currency ??
    null;

  function canAddItem(
    product: CartProduct,
  ): CartAddIssue {
    const existingCurrency =
      visibleItems[0]?.currency;

    if (
      existingCurrency &&
      existingCurrency !==
        product.currency
    ) {
      return "currency-mismatch";
    }

    const existing =
      visibleItems.find(
        (item) =>
          item.offerId ===
          product.offerId,
      );

    if (
      existing &&
      product.maxQuantity !==
        null &&
      existing.quantity >=
        product.maxQuantity
    ) {
      return "quantity-limit";
    }

    if (
      !existing &&
      product.maxQuantity !==
        null &&
      product.maxQuantity <= 0
    ) {
      return "quantity-limit";
    }

    return null;
  }

  function addItem(
    product: CartProduct,
  ) {
    if (
      canAddItem(product) !== null
    ) {
      return;
    }

    setItems((current) => {
      const existing =
        current.find(
          (item) =>
            item.offerId ===
            product.offerId,
        );

      if (existing) {
        return current.map(
          (item) =>
            item.offerId ===
            product.offerId
              ? {
                  ...item,
                  quantity:
                    item.quantity +
                    1,
                }
              : item,
        );
      }

      return [
        ...current,
        {
          ...product,
          quantity: 1,
        },
      ];
    });
  }

  function decreaseItem(
    offerId: number,
  ) {
    setItems((current) =>
      current
        .map((item) =>
          item.offerId === offerId
            ? {
                ...item,
                quantity:
                  item.quantity - 1,
              }
            : item,
        )
        .filter(
          (item) =>
            item.quantity > 0,
        ),
    );
  }

  function removeItem(
    offerId: number,
  ) {
    setItems((current) =>
      current.filter(
        (item) =>
          item.offerId !== offerId,
      ),
    );
  }

  function clearCart() {
    setItems([]);
  }

  const totalItems =
    visibleItems.reduce(
      (total, item) =>
        total + item.quantity,
      0,
    );

  const totalPriceCents =
    visibleItems.reduce(
      (total, item) =>
        total +
        item.priceCents *
          item.quantity,
      0,
    );

  return (
    <CartContext.Provider
      value={{
        items: visibleItems,
        totalItems,
        totalPriceCents,
        currency,
        canAddItem,
        addItem,
        decreaseItem,
        removeItem,
        clearCart,
      }}
    >
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  const context =
    useContext(CartContext);

  if (!context) {
    throw new Error(
      "useCart must be used inside CartProvider",
    );
  }

  return context;
}
