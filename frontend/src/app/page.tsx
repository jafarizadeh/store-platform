import Image from "next/image";
import Link from "next/link";

import SiteHeader from "@/components/site-header";
export default function Home() {
  return (
    <main className="min-h-screen bg-white text-neutral-950">

      {/* Header */}
      <SiteHeader />

      {/* Hero */}
      <section className="mx-auto grid max-w-7xl items-center gap-12 px-6 py-10 lg:min-h-[610px] lg:grid-cols-2 lg:px-8">
        <div>
          <p className="mb-5 text-sm font-medium uppercase tracking-[0.24em] text-neutral-500">
            Build. Learn. Create.
          </p>

          <h1 className="max-w-2xl text-5xl font-semibold leading-[1.03] tracking-[-0.045em] sm:text-6xl lg:text-7xl">
            Everything you need to build with Raspberry Pi.
          </h1>

          <p className="mt-7 max-w-xl text-lg leading-8 text-neutral-600">
            Components, complete kits, ready-made solutions and guided projects
            — carefully selected for makers, students and curious minds.
          </p>

          <div className="mt-9 flex flex-wrap gap-4">
            <Link
              href="/shop"
              className="rounded-full bg-neutral-950 px-7 py-3.5 text-sm font-medium text-white transition hover:bg-neutral-800"
            >
              Shop Products
            </Link>

            <a
              href="#categories"
              className="rounded-full border border-neutral-300 px-7 py-3.5 text-sm font-medium transition hover:bg-neutral-100"
            >
              Explore Projects
            </a>
          </div>

        </div>

        <div className="group relative aspect-[4/3] overflow-hidden rounded-[2rem] bg-neutral-100">
          <Image
            src="/assets/products/raspberry-pi/rpi01.png"
            alt="Raspberry Pi"
            fill
            priority
            sizes="(max-width: 1024px) 100vw, 50vw"
            className="object-contain p-3 transition-transform duration-700 ease-out group-hover:scale-[1.06] lg:p-4"
          />
        </div>
      </section>

      {/* Main paths */}
      <section
        id="categories"
        className="border-t border-neutral-200 bg-neutral-50"
      >
        <div className="mx-auto max-w-7xl px-6 py-20 lg:px-8">
          <div className="mb-10">
            <p className="text-sm font-medium uppercase tracking-[0.2em] text-neutral-500">
              Start here
            </p>

            <h2 className="mt-3 text-3xl font-semibold tracking-[-0.03em]">
              What are you looking for?
            </h2>
          </div>

          <div className="grid gap-5 md:grid-cols-3">

            {/* Shop */}
            <Link
              href="/shop"
              className="group rounded-3xl border border-neutral-200 bg-white p-8 transition duration-300 hover:-translate-y-1 hover:border-neutral-400 hover:shadow-lg"
            >
              <div className="mb-12 flex h-12 w-12 items-center justify-center rounded-full bg-neutral-950 text-white">
                01
              </div>

              <h3 className="text-2xl font-semibold tracking-[-0.03em]">
                Shop Products
              </h3>

              <p className="mt-4 max-w-sm leading-7 text-neutral-600">
                Raspberry Pi boards, displays, sensors, accessories and
                individual components.
              </p>

              <div className="mt-8 text-sm font-medium">
                Browse products
                <span className="ml-2 transition group-hover:ml-3">→</span>
              </div>
            </Link>

            {/* Projects */}
            <a
              href="#"
              className="group rounded-3xl border border-neutral-200 bg-white p-8 transition duration-300 hover:-translate-y-1 hover:border-neutral-400 hover:shadow-lg"
            >
              <div className="mb-12 flex h-12 w-12 items-center justify-center rounded-full bg-neutral-200 text-neutral-700">
                02
              </div>

              <h3 className="text-2xl font-semibold tracking-[-0.03em]">
                Project Kits
              </h3>

              <p className="mt-4 max-w-sm leading-7 text-neutral-600">
                Complete project packages with components, software and
                step-by-step instructions from level 1 to 10.
              </p>

              <div className="mt-8 text-sm font-medium">
                Explore projects
                <span className="ml-2 transition group-hover:ml-3">→</span>
              </div>
            </a>

            {/* Solutions */}
            <a
              href="#"
              className="group rounded-3xl border border-neutral-200 bg-white p-8 text-neutral-950 transition duration-300 hover:-translate-y-1 hover:border-neutral-400 hover:shadow-lg"
            >
              <div className="mb-12 flex h-12 w-12 items-center justify-center rounded-full bg-neutral-200 text-neutral-700">
                03
              </div>

              <h3 className="text-2xl font-semibold tracking-[-0.03em]">
                Ready-made Solutions
              </h3>

              <p className="mt-4 max-w-sm leading-7 text-neutral-600">
                Finished and tested Raspberry Pi solutions for real-world use,
                ready to install and operate.
              </p>

              <div className="mt-8 text-sm font-medium">
                View solutions
                <span className="ml-2 transition group-hover:ml-3">→</span>
              </div>
            </a>

          </div>
        </div>
      </section>


      {/* Featured Products */}
      <section id="featured-products" className="bg-white">
        <div className="mx-auto max-w-7xl px-6 py-24 lg:px-8">

          <div className="mb-12 flex items-end justify-between gap-6">
            <div>
              <p className="text-sm font-medium uppercase tracking-[0.2em] text-neutral-500">
                Featured Products
              </p>

              <h2 className="mt-3 text-3xl font-semibold tracking-[-0.03em] sm:text-4xl">
                Start building.
              </h2>
            </div>

            <Link
              href="/shop"
              className="hidden text-sm font-medium text-neutral-600 transition hover:text-neutral-950 sm:block"
            >
              View all products →
            </Link>
          </div>

          <div className="grid gap-6 md:grid-cols-3">

            {/* Product 1 */}
            <article className="group flex h-full flex-col">
              <div className="relative aspect-square overflow-hidden rounded-3xl bg-neutral-100">
                <Image
                  src="/assets/products/raspberry-pi/rpi01.png"
                  alt="Raspberry Pi board"
                  fill
                  sizes="(max-width: 768px) 100vw, 33vw"
                  className="object-contain p-8 mix-blend-multiply transition-transform duration-500 group-hover:scale-[1.04]"
                />
              </div>

              <div className="flex flex-1 flex-col pt-5">
                <p className="text-xs font-medium uppercase tracking-[0.15em] text-neutral-500">
                  Raspberry Pi
                </p>

                <div className="mt-2 flex items-start justify-between gap-4">
                  <div>
                    <h3 className="text-lg font-semibold">
                      Raspberry Pi 5
                    </h3>

                    <p className="mt-1 min-h-[42px] text-sm leading-6 text-neutral-500">
                      Powerful board for modern projects.
                    </p>
                  </div>

                  <p className="whitespace-nowrap font-semibold">
                    €79
                  </p>
                </div>

                <button className="mt-auto w-full rounded-full bg-neutral-950 px-5 py-3 text-sm font-medium text-white transition hover:bg-neutral-800">
                  Add to Cart
                </button>
              </div>
            </article>

            {/* Product 2 */}
            <article className="group flex h-full flex-col">
              <div className="relative aspect-square overflow-hidden rounded-3xl bg-neutral-100">
                <Image
                  src="/assets/products/raspberry-pi/rpi02.png"
                  alt="Raspberry Pi module"
                  fill
                  sizes="(max-width: 768px) 100vw, 33vw"
                  className="object-contain p-8 mix-blend-multiply transition-transform duration-500 group-hover:scale-[1.04]"
                />
              </div>

              <div className="flex flex-1 flex-col pt-5">
                <p className="text-xs font-medium uppercase tracking-[0.15em] text-neutral-500">
                  Module
                </p>

                <div className="mt-2 flex items-start justify-between gap-4">
                  <div>
                    <h3 className="text-lg font-semibold">
                      Compute Module
                    </h3>

                    <p className="mt-1 min-h-[42px] text-sm leading-6 text-neutral-500">
                      Compact platform for embedded builds.
                    </p>
                  </div>

                  <p className="whitespace-nowrap font-semibold">
                    €59
                  </p>
                </div>

                <button className="mt-auto w-full rounded-full bg-neutral-950 px-5 py-3 text-sm font-medium text-white transition hover:bg-neutral-800">
                  Add to Cart
                </button>
              </div>
            </article>

            {/* Product 3 */}
            <article className="group flex h-full flex-col">
              <div className="relative aspect-square overflow-hidden rounded-3xl bg-neutral-100">
                <Image
                  src="/assets/products/raspberry-pi/rpi03.png"
                  alt="Raspberry Pi microcontroller"
                  fill
                  sizes="(max-width: 768px) 100vw, 33vw"
                  className="object-contain p-8 mix-blend-multiply transition-transform duration-500 group-hover:scale-[1.04]"
                />
              </div>

              <div className="flex flex-1 flex-col pt-5">
                <p className="text-xs font-medium uppercase tracking-[0.15em] text-neutral-500">
                  Microcontroller
                </p>

                <div className="mt-2 flex items-start justify-between gap-4">
                  <div>
                    <h3 className="text-lg font-semibold">
                      Raspberry Pi Pico
                    </h3>

                    <p className="mt-1 min-h-[42px] text-sm leading-6 text-neutral-500">
                      Small, affordable and made for experiments.
                    </p>
                  </div>

                  <p className="whitespace-nowrap font-semibold">
                    €9
                  </p>
                </div>

                <button className="mt-auto w-full rounded-full bg-neutral-950 px-5 py-3 text-sm font-medium text-white transition hover:bg-neutral-800">
                  Add to Cart
                </button>
              </div>
            </article>

          </div>

          <Link
            href="/shop"
            className="mt-10 block text-center text-sm font-medium sm:hidden"
          >
            View all products →
          </Link>

        </div>
      </section>

    </main>
  );
}
