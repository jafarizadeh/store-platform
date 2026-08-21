"use client";

import Link from "next/link";
import { useCart } from "@/context/cart-context";

export default function CartLink() {
  const { totalItems } = useCart();

  return (
    <Link
      href="/cart"
      className="relative rounded-full bg-neutral-950 px-4 py-2 text-sm font-medium text-white transition hover:bg-neutral-800"
    >
      Cart
      {totalItems > 0 && (
        <span className="ml-2 inline-flex min-w-5 items-center justify-center rounded-full bg-white px-1.5 py-0.5 text-[11px] font-semibold text-neutral-950">
          {totalItems}
        </span>
      )}
    </Link>
  );
}
