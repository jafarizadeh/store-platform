"use client";

import { useState } from "react";
import { useCart } from "@/context/cart-context";

type Props = {
  product: {
    slug: string;
    name: string;
    price: number;
    image: string;
  };
  fullWidth?: boolean;
};

export default function AddToCartButton({
  product,
  fullWidth = false,
}: Props) {
  const { addItem } = useCart();
  const [added, setAdded] = useState(false);

  function handleAdd() {
    addItem(product);
    setAdded(true);

    window.setTimeout(() => {
      setAdded(false);
    }, 900);
  }

  return (
    <button
      type="button"
      onClick={handleAdd}
      className={`rounded-full bg-neutral-950 px-6 py-3 text-sm font-medium text-white transition hover:bg-neutral-800 ${
        fullWidth ? "w-full" : ""
      }`}
    >
      {added ? "Added ✓" : "Add to Cart"}
    </button>
  );
}
