import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";

import SiteHeader from "@/components/site-header";
import {
  formatOfferPrice,
  getPrimaryProductImagePath,
} from "@/lib/catalog";
import { getProduct } from "@/lib/products-api";
import {
  isProjectCatalogEntry,
  projectAvailabilityLabel,
  projectOfferLabel,
  projectTypeLabel,
} from "@/lib/projects";

type ProjectPageProps = {
  params: Promise<{
    slug: string;
  }>;
};

export default async function ProjectPage({
  params,
}: ProjectPageProps) {
  const { slug } = await params;

  const project = await getProduct(
    slug,
  );

  if (
    !project ||
    !isProjectCatalogEntry(project)
  ) {
    notFound();
  }

  const primaryImage =
    getPrimaryProductImagePath(
      project,
    );

  const secondaryImages =
    project.images
      .filter(
        (image) =>
          image.imagePath !==
          primaryImage,
      )
      .slice(0, 3);

  return (
    <main className="min-h-screen bg-white text-neutral-950">
      <SiteHeader />

      <section className="mx-auto max-w-7xl px-6 py-10 lg:px-8 lg:py-14">
        <Link
          href="/projects"
          className="text-sm font-medium text-neutral-500 transition hover:text-neutral-950"
        >
          ← All projects
        </Link>

        <div className="mt-8 grid gap-10 lg:grid-cols-[1.1fr_0.9fr] lg:gap-14">
          <div>
            <div className="relative aspect-[4/3] overflow-hidden rounded-[2rem] bg-neutral-100">
              <Image
                src={primaryImage}
                alt={project.name}
                fill
                priority
                sizes="(max-width: 1024px) 100vw, 55vw"
                className="object-contain p-8 mix-blend-multiply"
              />
            </div>

            {secondaryImages.length >
              0 && (
              <div className="mt-4 grid grid-cols-3 gap-4">
                {secondaryImages.map(
                  (image) => (
                    <div
                      key={image.id}
                      className="relative aspect-square overflow-hidden rounded-2xl bg-neutral-100"
                    >
                      <Image
                        src={
                          image.imagePath
                        }
                        alt={
                          image.altText ??
                          project.name
                        }
                        fill
                        sizes="20vw"
                        className="object-contain p-4 mix-blend-multiply"
                      />
                    </div>
                  ),
                )}
              </div>
            )}
          </div>

          <div className="lg:pt-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-neutral-950 px-3 py-1.5 text-xs font-semibold text-white">
                {projectTypeLabel(
                  project,
                )}
              </span>

              <span className="rounded-full border border-neutral-300 px-3 py-1.5 text-xs font-semibold text-neutral-600">
                {project.category}
              </span>
            </div>

            <h1 className="mt-6 text-4xl font-semibold leading-[0.98] tracking-[-0.05em] sm:text-5xl">
              {project.name}
            </h1>

            {project.description && (
              <p className="mt-6 text-lg leading-8 text-neutral-600">
                {project.description}
              </p>
            )}

            <div className="mt-8 flex items-center gap-8 border-y border-neutral-200 py-5">
              <div>
                <p className="text-xs font-medium uppercase tracking-[0.16em] text-neutral-400">
                  Difficulty
                </p>

                <p className="mt-1 font-semibold">
                  {project.difficultyLevel
                    ? `${project.difficultyLevel}/10`
                    : "Not rated"}
                </p>
              </div>

              <div>
                <p className="text-xs font-medium uppercase tracking-[0.16em] text-neutral-400">
                  Type
                </p>

                <p className="mt-1 font-semibold">
                  {projectTypeLabel(
                    project,
                  )}
                </p>
              </div>
            </div>

            <div className="mt-8">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-neutral-500">
                Available options
              </p>

              <div className="mt-4 space-y-3">
                {project.offers.length >
                0 ? (
                  project.offers.map(
                    (offer) => (
                      <div
                        key={offer.id}
                        className="rounded-2xl border border-neutral-200 p-5"
                      >
                        <div className="flex items-start justify-between gap-5">
                          <div>
                            <p className="font-semibold">
                              {
                                offer.name
                              }
                            </p>

                            <p className="mt-1 text-sm text-neutral-500">
                              {projectOfferLabel(
                                offer,
                              )}
                              {" · "}
                              {projectAvailabilityLabel(
                                offer,
                              )}
                            </p>
                          </div>

                          <p className="shrink-0 font-semibold">
                            {formatOfferPrice(
                              offer,
                            )}
                          </p>
                        </div>
                      </div>
                    ),
                  )
                ) : (
                  <div className="rounded-2xl border border-neutral-200 bg-neutral-50 p-5 text-sm text-neutral-500">
                    Commercial options have not been published yet.
                  </div>
                )}
              </div>
            </div>

            <Link
              href={`/shop/${project.slug}`}
              className="mt-7 block w-full rounded-full bg-neutral-950 px-7 py-4 text-center text-sm font-semibold text-white transition hover:bg-neutral-700"
            >
              View purchase options
            </Link>

            <p className="mt-4 text-center text-xs leading-5 text-neutral-400">
              Pricing and availability are confirmed through the product
              offer before checkout.
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}
