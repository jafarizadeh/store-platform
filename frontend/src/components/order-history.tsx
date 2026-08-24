"use client";

import {
  useEffect,
  useState,
} from "react";

import {
  type CustomerOrder,
  fetchOrders,
} from "@/lib/orders-client";

function formatMoney(
  cents: number,
  currency: string,
): string {
  try {
    return new Intl.NumberFormat(
      "en",
      {
        style: "currency",
        currency,
      },
    ).format(
      cents / 100,
    );
  } catch {
    return (
      `${(cents / 100).toFixed(2)} `
      + currency
    );
  }
}

function formatDate(
  value: string,
): string {
  const date = new Date(value);

  if (
    Number.isNaN(
      date.getTime(),
    )
  ) {
    return value;
  }

  return new Intl.DateTimeFormat(
    "en",
    {
      dateStyle: "medium",
      timeStyle: "short",
    },
  ).format(date);
}

function statusClasses(
  status: string,
): string {
  switch (status) {
    case "paid":
      return (
        "bg-emerald-50 "
        + "text-emerald-800"
      );

    case "cancelled":
      return (
        "bg-neutral-100 "
        + "text-neutral-600"
      );

    case "refunded":
      return (
        "bg-blue-50 "
        + "text-blue-800"
      );

    default:
      return (
        "bg-amber-50 "
        + "text-amber-800"
      );
  }
}

export default function OrderHistory() {
  const [orders, setOrders] =
    useState<CustomerOrder[]>([]);

  const [isLoading, setIsLoading] =
    useState(true);

  const [error, setError] =
    useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    void fetchOrders()
      .then((result) => {
        if (!cancelled) {
          setOrders(result);
          setError(null);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError(
            "Order history could not be loaded.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (isLoading) {
    return (
      <section className="mt-8 rounded-3xl bg-neutral-50 p-6">
        <h3 className="text-lg font-semibold tracking-[-0.03em]">
          Orders
        </h3>

        <p className="mt-3 text-sm text-neutral-500">
          Loading order history…
        </p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="mt-8 rounded-3xl border border-red-200 bg-red-50 p-6">
        <h3 className="text-lg font-semibold text-red-900">
          Orders
        </h3>

        <p className="mt-2 text-sm leading-6 text-red-800">
          {error}
        </p>
      </section>
    );
  }

  if (orders.length === 0) {
    return (
      <section className="mt-8 rounded-3xl bg-neutral-50 p-6">
        <h3 className="text-lg font-semibold tracking-[-0.03em]">
          Orders
        </h3>

        <p className="mt-2 text-sm leading-6 text-neutral-600">
          You haven&apos;t placed any
          orders yet.
        </p>
      </section>
    );
  }

  return (
    <section className="mt-8">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-neutral-500">
            Purchase history
          </p>

          <h3 className="mt-2 text-2xl font-semibold tracking-[-0.04em]">
            Orders
          </h3>
        </div>

        <span className="text-sm text-neutral-500">
          {orders.length}{" "}
          {orders.length === 1
            ? "order"
            : "orders"}
        </span>
      </div>

      <div className="mt-5 space-y-4">
        {orders.map((order) => (
          <article
            key={order.id}
            className="overflow-hidden rounded-3xl border border-neutral-200 bg-white"
          >
            <div className="flex flex-col gap-4 border-b border-neutral-200 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6">
              <div>
                <p className="font-mono text-xs text-neutral-500">
                  {order.order_number}
                </p>

                <p className="mt-2 text-sm text-neutral-600">
                  {formatDate(
                    order.created_at,
                  )}
                </p>
              </div>

              <div className="flex items-center gap-3">
                <span
                  className={`rounded-full px-3 py-1.5 text-xs font-semibold capitalize ${statusClasses(
                    order.status,
                  )}`}
                >
                  {order.status}
                </span>

                <span className="text-base font-semibold">
                  {formatMoney(
                    order.total_cents,
                    order.currency,
                  )}
                </span>
              </div>
            </div>

            <div className="divide-y divide-neutral-100">
              {order.items.map(
                (item) => (
                  <div
                    key={`${order.id}-${item.offer_id}`}
                    className="grid gap-3 p-5 sm:grid-cols-[1fr_auto] sm:items-center sm:p-6"
                  >
                    <div>
                      <p className="font-medium">
                        {
                          item.product_name
                        }
                      </p>

                      <p className="mt-1 text-sm text-neutral-500">
                        {
                          item.offer_name
                        }
                        {" · "}
                        {item.sku}
                      </p>
                    </div>

                    <div className="text-sm sm:text-right">
                      <p className="font-medium">
                        {
                          item.quantity
                        }
                        {" × "}
                        {formatMoney(
                          item.unit_price_cents,
                          order.currency,
                        )}
                      </p>

                      <p className="mt-1 capitalize text-neutral-500">
                        {
                          item.fulfillment_type
                        }
                      </p>
                    </div>
                  </div>
                ),
              )}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
