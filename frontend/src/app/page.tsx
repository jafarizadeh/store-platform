import Image from "next/image";
import Link from "next/link";

import SiteHeader from "@/components/site-header";

const categories = [
  {
    name: "Raspberry Pi",
    description: "Boards & computers",
  },
  {
    name: "Cameras",
    description: "Vision & imaging",
  },
  {
    name: "Cooling",
    description: "Thermal solutions",
  },
  {
    name: "Sensors",
    description: "Sense the world",
  },
  {
    name: "Kits & Robotics",
    description: "Build complete systems",
  },
];

export default function Home() {
  return (
    <main className="min-h-screen bg-white text-neutral-950">
      <SiteHeader />

      {/* Hero */}
      <section className="relative overflow-hidden border-b border-neutral-200">
        <div className="mx-auto grid max-w-7xl items-center gap-8 px-6 py-12 lg:min-h-[560px] lg:grid-cols-2 lg:px-8 lg:py-14">
          <div className="relative z-10">
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-neutral-500">
              Raspberry Pi ecosystem
            </p>

            <h1 className="mt-5 max-w-[620px] text-[clamp(3.4rem,6vw,6rem)] font-semibold leading-[0.92] tracking-[-0.065em]">
              Build more with
              <br />
              Raspberry Pi.
            </h1>

            <p className="mt-6 max-w-[560px] text-base leading-7 text-neutral-600 sm:text-lg sm:leading-8">
              Boards, cameras, sensors, cooling, robotics and practical
              projects — everything around Raspberry Pi in one place.
            </p>

            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href="/shop"
                className="rounded-full bg-neutral-950 px-7 py-3.5 text-sm font-semibold text-white transition duration-200 hover:bg-neutral-700"
              >
                Shop products
              </Link>

              <a
                href="#paths"
                className="rounded-full border border-neutral-300 bg-white px-7 py-3.5 text-sm font-semibold transition duration-200 hover:border-neutral-950 hover:bg-neutral-50"
              >
                Explore projects
              </a>
            </div>
          </div>

          <div className="relative min-h-[380px] sm:min-h-[470px] lg:min-h-[520px]">
            <div className="absolute inset-0 scale-[1.06] rounded-[3rem] bg-[radial-gradient(circle_at_center,_#f3f3f3_0%,_#fafafa_46%,_#ffffff_72%)]" />

            <Image
              src="/assets/home/raspberry-pi-5-hero.png"
              alt="Raspberry Pi 5"
              fill
              priority
              sizes="(max-width: 1024px) 100vw, 52vw"
              className="relative z-10 scale-[1.12] object-contain p-3 sm:p-5 lg:scale-[1.16]"
            />
          </div>
        </div>
      </section>

      {/* Search */}
      <section className="bg-neutral-50">
        <div className="mx-auto max-w-6xl px-6 py-12 lg:px-8 lg:py-14">
          <div className="mx-auto max-w-4xl text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-neutral-500">
              Quick access
            </p>

            <h2 className="mt-3 text-2xl font-semibold tracking-[-0.04em] sm:text-3xl">
              Find what you need.
            </h2>

            <form
              action="/shop"
              method="get"
              className="mx-auto mt-7 flex max-w-4xl items-center gap-3 rounded-full border border-neutral-300 bg-white p-2.5 shadow-[0_14px_50px_rgba(0,0,0,0.06)] transition focus-within:border-neutral-950 focus-within:shadow-[0_18px_60px_rgba(0,0,0,0.09)]"
            >
              <div className="flex min-w-0 flex-1 items-center gap-3 pl-4">
                <svg
                  aria-hidden="true"
                  viewBox="0 0 24 24"
                  fill="none"
                  className="h-5 w-5 shrink-0 text-neutral-400"
                >
                  <path
                    d="m21 21-4.35-4.35m2.35-5.15A7.5 7.5 0 1 1 4 11.5a7.5 7.5 0 0 1 15 0Z"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                  />
                </svg>

                <input
                  type="search"
                  name="q"
                  autoComplete="off"
                  placeholder="Search Raspberry Pi, cameras, sensors, cooling, kits..."
                  className="min-w-0 flex-1 bg-transparent py-3.5 text-base outline-none placeholder:text-neutral-400"
                />
              </div>

              <button
                type="submit"
                className="shrink-0 rounded-full bg-neutral-950 px-7 py-3.5 text-sm font-semibold text-white transition hover:bg-neutral-700"
              >
                Search
              </button>
            </form>

            <p className="mt-4 text-xs text-neutral-400">
              Search products, categories, variants or SKU.
            </p>
          </div>
        </div>
      </section>

      {/* Categories */}
      <section className="border-t border-neutral-200 bg-white">
        <div className="mx-auto max-w-7xl px-6 py-16 lg:px-8 lg:py-20">
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-neutral-500">
                Browse
              </p>

              <h2 className="mt-3 text-3xl font-semibold tracking-[-0.045em] sm:text-4xl">
                The Raspberry Pi toolbox.
              </h2>
            </div>

            <Link
              href="/shop"
              className="text-sm font-semibold text-neutral-500 transition hover:text-neutral-950"
            >
              View all products →
            </Link>
          </div>

          <div className="mt-8 grid overflow-hidden rounded-[1.75rem] border border-neutral-200 bg-white sm:grid-cols-2 lg:grid-cols-5">
            {categories.map((category, index) => (
              <Link
                key={category.name}
                href={{
                  pathname: "/shop",
                  query: {
                    category: category.name,
                  },
                }}
                className={`group relative min-h-48 p-6 transition duration-300 hover:bg-neutral-950 hover:text-white ${
                  index !== categories.length - 1
                    ? "border-b border-neutral-200 lg:border-b-0 lg:border-r"
                    : ""
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-neutral-400 transition group-hover:text-neutral-500">
                    {String(index + 1).padStart(2, "0")}
                  </span>

                  <span className="translate-x-[-4px] text-sm opacity-0 transition duration-300 group-hover:translate-x-0 group-hover:opacity-100">
                    →
                  </span>
                </div>

                <div className="absolute bottom-6 left-6 right-6">
                  <h3 className="text-lg font-semibold tracking-[-0.025em]">
                    {category.name}
                  </h3>

                  <p className="mt-2 text-sm text-neutral-500 transition group-hover:text-neutral-300">
                    {category.description}
                  </p>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Main paths */}
      <section
        id="paths"
        className="border-t border-neutral-200 bg-neutral-50"
      >
        <div className="mx-auto max-w-7xl px-6 py-16 lg:px-8 lg:py-20">
          <div className="mb-9">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-neutral-500">
              Choose your path
            </p>

            <h2 className="mt-3 max-w-3xl text-3xl font-semibold leading-[0.98] tracking-[-0.05em] sm:text-5xl">
              Buy the parts.
              <br />
              Or build the idea.
            </h2>
          </div>

          <div className="grid gap-5 lg:grid-cols-2">
            <Link
              href="/shop"
              className="group relative flex min-h-[360px] flex-col justify-between overflow-hidden rounded-[2rem] border border-neutral-200 bg-white p-8 transition duration-300 hover:-translate-y-1 hover:border-neutral-300 hover:shadow-[0_24px_70px_rgba(0,0,0,0.08)] sm:p-10"
            >
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-[0.22em] text-neutral-400">
                    Products
                  </span>

                  <span className="text-xs text-neutral-400">
                    01
                  </span>
                </div>

                <h3 className="mt-6 text-4xl font-semibold tracking-[-0.05em]">
                  Shop components.
                </h3>

                <p className="mt-5 max-w-md text-base leading-7 text-neutral-600">
                  Raspberry Pi boards, cameras, sensors, cooling, accessories
                  and robotics hardware.
                </p>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold">
                  Browse the shop
                </span>

                <span className="flex h-12 w-12 items-center justify-center rounded-full bg-neutral-950 text-xl text-white transition duration-300 group-hover:translate-x-1">
                  →
                </span>
              </div>
            </Link>

            <Link
              href={{
                pathname: "/shop",
                query: {
                  category: "Kits & Robotics",
                },
              }}
              className="group relative flex min-h-[360px] flex-col justify-between overflow-hidden rounded-[2rem] bg-neutral-950 p-8 text-white transition duration-300 hover:-translate-y-1 hover:shadow-[0_24px_70px_rgba(0,0,0,0.16)] sm:p-10"
            >
              <div className="pointer-events-none absolute -right-24 -top-24 h-80 w-80 rounded-full bg-white/[0.035] blur-2xl" />

              <div className="relative">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-[0.22em] text-neutral-500">
                    Projects
                  </span>

                  <span className="text-xs text-neutral-600">
                    02
                  </span>
                </div>

                <h3 className="mt-6 text-4xl font-semibold tracking-[-0.05em]">
                  Explore projects.
                </h3>

                <p className="mt-5 max-w-md text-base leading-7 text-neutral-400">
                  Complete kits and robotics builds designed to turn Raspberry
                  Pi into working real-world systems.
                </p>
              </div>

              <div className="relative flex items-center justify-between">
                <span className="text-sm font-semibold">
                  Explore builds
                </span>

                <span className="flex h-12 w-12 items-center justify-center rounded-full bg-white text-xl text-neutral-950 transition duration-300 group-hover:translate-x-1">
                  →
                </span>
              </div>
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}
