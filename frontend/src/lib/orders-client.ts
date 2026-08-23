export type OrderItem = {
  offer_id: number;
  product_name: string;
  offer_name: string;
  sku: string;
  fulfillment_type: string;
  unit_price_cents: number;
  quantity: number;
};

export type CustomerOrder = {
  id: string;
  status: string;
  currency: string;
  total_cents: number;
  created_at: string;
  items: OrderItem[];
};

export class OrdersRequestError extends Error {
  readonly status: number;

  constructor(
    status: number,
  ) {
    super(
      `Orders request failed with status ${status}`,
    );

    this.name = "OrdersRequestError";
    this.status = status;
  }
}

export async function fetchOrders(): Promise<
  CustomerOrder[]
> {
  const response = await fetch(
    "/api/orders",
    {
      method: "GET",
      credentials: "same-origin",
      cache: "no-store",
      headers: {
        Accept: "application/json",
      },
    },
  );

  if (!response.ok) {
    throw new OrdersRequestError(
      response.status,
    );
  }

  const payload = await response.json();

  return payload as CustomerOrder[];
}
