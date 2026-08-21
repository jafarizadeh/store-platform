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
  slug: string;
  name: string;
  price: number;
  image: string;
};

export type CartItem = CartProduct & {
  quantity: number;
};

type CartContextType = {
  items: CartItem[];
  totalItems: number;
  totalPrice: number;
  addItem: (product: CartProduct) => void;
  decreaseItem: (slug: string) => void;
  removeItem: (slug: string) => void;
  clearCart: () => void;
};

const CartContext = createContext<CartContextType | undefined>(undefined);

const emptySubscribe = () => () => {};

function getStoredCart(): CartItem[] {
  if (typeof window === "undefined") {
    return [];
  }

  const saved = window.localStorage.getItem("bynet-cart");

  if (!saved) {
    return [];
  }

  try {
    const parsed = JSON.parse(saved);

    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function CartProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<CartItem[]>(getStoredCart);

  const hydrated = useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false
  );

  useEffect(() => {
    if (!hydrated) {
      return;
    }

    window.localStorage.setItem(
      "bynet-cart",
      JSON.stringify(items)
    );
  }, [items, hydrated]);

  function addItem(product: CartProduct) {
    setItems((current) => {
      const existing = current.find(
        (item) => item.slug === product.slug
      );

      if (existing) {
        return current.map((item) =>
          item.slug === product.slug
            ? {
                ...item,
                quantity: item.quantity + 1,
              }
            : item
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

  function decreaseItem(slug: string) {
    setItems((current) =>
      current
        .map((item) =>
          item.slug === slug
            ? {
                ...item,
                quantity: item.quantity - 1,
              }
            : item
        )
        .filter((item) => item.quantity > 0)
    );
  }

  function removeItem(slug: string) {
    setItems((current) =>
      current.filter((item) => item.slug !== slug)
    );
  }

  function clearCart() {
    setItems([]);
  }

  const visibleItems = hydrated ? items : [];

  const totalItems = visibleItems.reduce(
    (total, item) => total + item.quantity,
    0
  );

  const totalPrice = visibleItems.reduce(
    (total, item) =>
      total + item.price * item.quantity,
    0
  );

  return (
    <CartContext.Provider
      value={{
        items: visibleItems,
        totalItems,
        totalPrice,
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
  const context = useContext(CartContext);

  if (!context) {
    throw new Error(
      "useCart must be used inside CartProvider"
    );
  }

  return context;
}
