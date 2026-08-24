"use client";

import Image from "next/image";
import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  PRODUCT_PLACEHOLDER_IMAGE,
  type StoreProductImage,
} from "@/lib/catalog";

type ProductGalleryProps = {
  productName: string;
  images: StoreProductImage[];
};

export default function ProductGallery({
  productName,
  images,
}: ProductGalleryProps) {
  const galleryImages =
    useMemo<
      StoreProductImage[]
    >(
      () =>
        images.length > 0
          ? images
          : [
              {
                id: -1,
                imagePath:
                  PRODUCT_PLACEHOLDER_IMAGE,
                altText:
                  productName,
                position: 0,
                isPrimary: true,
              },
            ],
      [images, productName],
    );

  const [
    selectedIndex,
    setSelectedIndex,
  ] = useState(0);

  const [
    lightboxOpen,
    setLightboxOpen,
  ] = useState(false);

  const selected =
    galleryImages[
      selectedIndex
    ] ??
    galleryImages[0];

  useEffect(() => {
    if (!lightboxOpen) {
      return;
    }

    function handleKeyDown(
      event: KeyboardEvent,
    ) {
      if (
        event.key === "Escape"
      ) {
        setLightboxOpen(false);
      }

      if (
        event.key ===
        "ArrowRight"
      ) {
        setSelectedIndex(
          (current) =>
            (current + 1) %
            galleryImages.length,
        );
      }

      if (
        event.key ===
        "ArrowLeft"
      ) {
        setSelectedIndex(
          (current) =>
            (
              current -
              1 +
              galleryImages.length
            ) %
            galleryImages.length,
        );
      }
    }

    window.addEventListener(
      "keydown",
      handleKeyDown,
    );

    return () => {
      window.removeEventListener(
        "keydown",
        handleKeyDown,
      );
    };
  }, [
    galleryImages.length,
    lightboxOpen,
  ]);

  function previous() {
    setSelectedIndex(
      (current) =>
        (
          current -
          1 +
          galleryImages.length
        ) %
        galleryImages.length,
    );
  }

  function next() {
    setSelectedIndex(
      (current) =>
        (current + 1) %
        galleryImages.length,
    );
  }

  const alt =
    selected.altText ??
    `${productName} image ${selectedIndex + 1}`;

  return (
    <>
      <div>
        <div className="group relative aspect-square overflow-hidden rounded-3xl bg-neutral-50">
          <button
            type="button"
            onClick={() =>
              setLightboxOpen(
                true,
              )
            }
            className="relative h-full w-full cursor-zoom-in"
            aria-label={`Open ${productName} image gallery`}
          >
            <Image
              src={
                selected.imagePath
              }
              alt={alt}
              fill
              sizes="(max-width: 1024px) 100vw, 50vw"
              className="object-contain p-8 mix-blend-multiply"
              priority
            />
          </button>

          {galleryImages.length >
            1 && (
            <>
              <button
                type="button"
                onClick={previous}
                aria-label="Previous image"
                className="absolute left-4 top-1/2 -translate-y-1/2 rounded-full bg-white/90 px-4 py-3 text-lg shadow-sm backdrop-blur transition hover:bg-white"
              >
                ←
              </button>

              <button
                type="button"
                onClick={next}
                aria-label="Next image"
                className="absolute right-4 top-1/2 -translate-y-1/2 rounded-full bg-white/90 px-4 py-3 text-lg shadow-sm backdrop-blur transition hover:bg-white"
              >
                →
              </button>

              <div className="absolute bottom-4 right-4 rounded-full bg-neutral-950/80 px-3 py-1.5 text-xs font-medium text-white backdrop-blur">
                {selectedIndex + 1}
                {" / "}
                {
                  galleryImages.length
                }
              </div>
            </>
          )}
        </div>

        {galleryImages.length >
          1 && (
          <div className="mt-4 flex gap-3 overflow-x-auto pb-2">
            {galleryImages.map(
              (image, index) => {
                const active =
                  index ===
                  selectedIndex;

                return (
                  <button
                    key={image.id}
                    type="button"
                    onClick={() =>
                      setSelectedIndex(
                        index,
                      )
                    }
                    className={[
                      "relative h-20 w-20 shrink-0 overflow-hidden rounded-xl border bg-neutral-50 transition",
                      active
                        ? "border-neutral-950"
                        : "border-neutral-200 hover:border-neutral-500",
                    ].join(" ")}
                    aria-label={`View image ${index + 1}`}
                  >
                    <Image
                      src={
                        image.imagePath
                      }
                      alt={
                        image.altText ??
                        productName
                      }
                      fill
                      sizes="80px"
                      className="object-contain p-2 mix-blend-multiply"
                    />
                  </button>
                );
              },
            )}
          </div>
        )}
      </div>

      {lightboxOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={`${productName} image viewer`}
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/90 p-4"
        >
          <button
            type="button"
            onClick={() =>
              setLightboxOpen(
                false,
              )
            }
            aria-label="Close image viewer"
            className="absolute right-5 top-5 rounded-full bg-white px-4 py-2 text-xl text-black"
          >
            ×
          </button>

          {galleryImages.length >
            1 && (
            <button
              type="button"
              onClick={previous}
              aria-label="Previous image"
              className="absolute left-5 rounded-full bg-white px-4 py-3 text-black"
            >
              ←
            </button>
          )}

          <div className="relative h-[85vh] w-[85vw]">
            <Image
              src={
                selected.imagePath
              }
              alt={alt}
              fill
              sizes="90vw"
              className="object-contain"
            />
          </div>

          {galleryImages.length >
            1 && (
            <button
              type="button"
              onClick={next}
              aria-label="Next image"
              className="absolute right-5 rounded-full bg-white px-4 py-3 text-black"
            >
              →
            </button>
          )}
        </div>
      )}
    </>
  );
}
