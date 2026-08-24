import Image from "next/image";
import Link from "next/link";

import SiteHeader from "@/components/site-header";
import {
  formatOfferPrice,
  getPrimaryOffer,
  getPrimaryProductImagePath,
} from "@/lib/catalog";
import { getProducts } from "@/lib/products-api";
import {
  isProjectCatalogEntry,
  projectTypeLabel,
} from "@/lib/projects";

export default async function ProjectsPage() {
  const products = await getProducts();

  const projects = products.filter(
    isProjectCatalogEntry,
  );

  return (
    <main className="min-h-screen bg-white text-neutral-950">
      <SiteHeader />

      <section className="border-b border-neutral-200">
        <div className="mx-auto max-w-7xl px-6 py-16 lg:px-8 lg:py-20">
          <p className="text-xs font-semibold uppercase tracking-[0.26em] text-neutral-500">
            Raspberry Pi projects
          </p>

          <div className="mt-5 grid gap-8 lg:grid-cols-[1.15fr_0.85fr] lg:items-end">
            <h1 className="max-w-4xl text-5xl font-semibold leading-[0.95] tracking-[-0.055em] sm:text-6xl lg:text-7xl">
              Turn components
              <br />
              into something useful.
            </h1>

            <p className="max-w-xl text-base leading-7 text-neutral-600 lg:justify-self-end lg:text-lg lg:leading-8">
              Explore Raspberry Pi kits, builds and complete solutions.
              Start with the hardware, understand what you are building,
              and choose the level of completion that fits your project.
            </p>
          </div>
        </div>
      </section>

      <section className="bg-neutral-50">
        <div className="mx-auto max-w-7xl px-6 py-16 lg:px-8 lg:py-20">
          <div className="mb-9 flex items-end justify-between gap-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-neutral-500">
                Explore builds
              </p>

              <h2 className="mt-3 text-3xl font-semibold tracking-[-0.04em]">
                Choose a project.
              </h2>
            </div>

            <span className="text-sm text-neutral-500">
              {projects.length}{" "}
              {projects.length === 1
                ? "project"
                : "projects"}
            </span>
          </div>

          {projects.length > 0 ? (
            <div className="grid gap-x-6 gap-y-12 md:grid-cols-2 lg:grid-cols-3">
              {projects.map((project) => {
                const image =
                  getPrimaryProductImagePath(
                    project,
                  );

                const offer =
                  getPrimaryOffer(project);

                return (
                  <Link
                    key={project.id}
                    href={`/projects/${project.slug}`}
                    className="group"
                  >
                    <div className="relative aspect-[4/3] overflow-hidden rounded-[1.75rem] bg-white">
                      <Image
                        src={image}
                        alt={project.name}
                        fill
                        sizes="(max-width: 768px) 100vw, 33vw"
                        className="object-contain p-7 mix-blend-multiply transition duration-500 group-hover:scale-[1.04]"
                      />

                      <div className="absolute left-4 top-4 rounded-full border border-black/5 bg-white/90 px-3 py-1.5 text-xs font-semibold backdrop-blur">
                        {projectTypeLabel(
                          project,
                        )}
                      </div>
                    </div>

                    <div className="pt-5">
                      <div className="flex items-start justify-between gap-5">
                        <div>
                          <p className="text-xs font-medium uppercase tracking-[0.16em] text-neutral-400">
                            {project.category}
                          </p>

                          <h3 className="mt-2 text-xl font-semibold tracking-[-0.03em] transition group-hover:text-neutral-500">
                            {project.name}
                          </h3>
                        </div>

                        <span className="shrink-0 text-sm font-semibold">
                          {offer
                            ? formatOfferPrice(
                                offer,
                              )
                            : "View options"}
                        </span>
                      </div>

                      <div className="mt-5 flex items-center justify-between border-t border-neutral-200 pt-4">
                        <span className="text-sm text-neutral-500">
                          {project.difficultyLevel
                            ? `Difficulty ${project.difficultyLevel}/10`
                            : "Difficulty not rated"}
                        </span>

                        <span className="text-sm font-semibold transition group-hover:translate-x-1">
                          View project →
                        </span>
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          ) : (
            <div className="flex min-h-[360px] items-center justify-center rounded-[2rem] border border-dashed border-neutral-300 bg-white">
              <div className="max-w-md text-center">
                <p className="text-2xl font-semibold tracking-[-0.03em]">
                  Projects are coming.
                </p>

                <p className="mt-3 leading-7 text-neutral-500">
                  The project catalog is ready for dedicated Raspberry Pi
                  builds and complete solutions.
                </p>

                <Link
                  href="/shop"
                  className="mt-7 inline-block rounded-full bg-neutral-950 px-6 py-3 text-sm font-semibold text-white"
                >
                  Browse components
                </Link>
              </div>
            </div>
          )}
        </div>
      </section>

      <section className="border-t border-neutral-200 bg-white">
        <div className="mx-auto grid max-w-7xl gap-6 px-6 py-16 lg:grid-cols-2 lg:px-8 lg:py-20">
          <div className="rounded-[2rem] bg-neutral-950 p-8 text-white sm:p-10">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-neutral-500">
              Build it yourself
            </p>

            <h2 className="mt-5 text-3xl font-semibold tracking-[-0.045em]">
              Start with the parts.
            </h2>

            <p className="mt-4 max-w-md leading-7 text-neutral-400">
              Pick the Raspberry Pi, sensors, cameras and accessories
              you need for your own build.
            </p>

            <Link
              href="/shop"
              className="mt-10 inline-flex rounded-full bg-white px-6 py-3 text-sm font-semibold text-neutral-950"
            >
              Shop components
            </Link>
          </div>

          <div className="rounded-[2rem] border border-neutral-200 bg-neutral-50 p-8 sm:p-10">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-neutral-400">
              Need the finished result?
            </p>

            <h2 className="mt-5 text-3xl font-semibold tracking-[-0.045em]">
              Move toward a complete solution.
            </h2>

            <p className="mt-4 max-w-md leading-7 text-neutral-600">
              Project offerings can grow from guides and parts kits into
              configured, tested and ready-to-use Raspberry Pi systems.
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}
