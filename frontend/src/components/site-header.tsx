import Link from "next/link";

import AccountLink from "@/components/account-link";
import CartLink from "@/components/cart-link";

export default function SiteHeader() {
  return (
    <header className="border-b border-neutral-200 bg-white">
      <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-6 lg:px-8">
        <Link
          href="/"
          className="text-2xl font-semibold tracking-[-0.04em]"
        >
          ByNET
        </Link>

        <nav className="hidden items-center gap-10 text-[15px] font-medium md:flex">
          <Link
            href="/shop"
            className="transition hover:text-neutral-500"
          >
            Shop
          </Link>

          <Link
            href="/shop?category=Kits%20%26%20Robotics"
            className="transition hover:text-neutral-500"
          >
            Kits
          </Link>

          <Link
            href="/projects"
            className="transition hover:text-neutral-500"
          >
            Projects
          </Link>

          <Link
            href="/projects"
            className="transition hover:text-neutral-500"
          >
            Solutions
          </Link>

          <Link
            href="/#contact"
            className="transition hover:text-neutral-500"
          >
            Contact
          </Link>
        </nav>

        <div className="flex items-center gap-2 sm:gap-3">
          <Link
            href="/shop"
            className="hidden rounded-full border border-neutral-300 px-4 py-2 text-sm font-medium transition hover:bg-neutral-100 lg:inline-flex"
          >
            Search
          </Link>

          <AccountLink />

          <CartLink />
        </div>
      </div>
    </header>
  );
}
