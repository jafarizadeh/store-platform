"use client";

import {
  useState,
  type MouseEvent,
} from "react";

import {
  useCart,
  type CartProduct,
} from "@/context/cart-context";

type AddToCartButtonProps = {
  product: CartProduct;
  fullWidth?: boolean;
  disabled?: boolean;
  label?: string;
};

export default function AddToCartButton({
  product,
  fullWidth = false,
  disabled = false,
  label = "Add to cart",
}: AddToCartButtonProps) {
  const {
    addItem,
    canAddItem,
  } = useCart();

  const [message, setMessage] =
    useState<string | null>(
      null,
    );

  const issue =
    canAddItem(product);

  const quantityBlocked =
    issue === "quantity-limit";

  function handleClick(
    event: MouseEvent<HTMLButtonElement>,
  ) {
    event.preventDefault();

    const currentIssue =
      canAddItem(product);

    if (
      currentIssue ===
      "currency-mismatch"
    ) {
      setMessage(
        "Cart items must use the same currency.",
      );
      return;
    }

    if (
      currentIssue ===
      "quantity-limit"
    ) {
      setMessage(
        "Maximum available quantity reached.",
      );
      return;
    }

    addItem(product);
    setMessage("Added to cart.");
  }

  return (
    <div
      className={
        fullWidth ? "w-full" : ""
      }
    >
      <button
        type="button"
        onClick={handleClick}
        disabled={
          disabled ||
          quantityBlocked
        }
        className={[
          "rounded-full bg-neutral-950 px-6 py-3 text-sm font-semibold text-white transition",
          "enabled:hover:bg-neutral-700",
          "disabled:cursor-not-allowed disabled:bg-neutral-300 disabled:text-neutral-500",
          fullWidth
            ? "w-full"
            : "",
        ].join(" ")}
      >
        {quantityBlocked
          ? "Max quantity reached"
          : label}
      </button>

      {message && (
        <p className="mt-2 text-xs text-neutral-500">
          {message}
        </p>
      )}
    </div>
  );
}
