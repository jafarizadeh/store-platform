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

export type OrderCreateItem = {
  offer_id: number;
  quantity: number;
};

export class OrdersRequestError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(
    status: number,
    code: string,
  ) {
    super(code);

    this.name = "OrdersRequestError";
    this.status = status;
    this.code = code;
  }
}

function errorCode(
  payload: unknown,
): string {
  if (
    typeof payload !== "object" ||
    payload === null
  ) {
    return "request_failed";
  }

  const detail = (
    payload as {
      detail?: unknown;
    }
  ).detail;

  if (
    typeof detail !== "object" ||
    detail === null
  ) {
    return "request_failed";
  }

  const code = (
    detail as {
      code?: unknown;
    }
  ).code;

  return typeof code === "string"
    ? code
    : "request_failed";
}

async function requestError(
  response: Response,
): Promise<OrdersRequestError> {
  let payload: unknown = null;

  try {
    payload = await response.json();
  } catch {
    // Status remains authoritative.
  }

  return new OrdersRequestError(
    response.status,
    errorCode(payload),
  );
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
    throw await requestError(
      response,
    );
  }

  const payload = await response.json();

  return payload as CustomerOrder[];
}

export async function createOrder(
  items: OrderCreateItem[],
): Promise<CustomerOrder> {
  const response = await fetch(
    "/api/orders",
    {
      method: "POST",
      credentials: "same-origin",
      cache: "no-store",
      headers: {
        Accept: "application/json",
        "Content-Type":
          "application/json",
      },
      body: JSON.stringify({
        items,
      }),
    },
  );

  if (!response.ok) {
    throw await requestError(
      response,
    );
  }

  const payload = await response.json();

  return payload as CustomerOrder;
}

export function orderErrorMessage(
  error: unknown,
): string {
  if (
    !(error instanceof OrdersRequestError)
  ) {
    return (
      "Unable to create the order. "
      + "Please try again."
    );
  }

  switch (error.code) {
    case "not_authenticated":
      return "Please sign in to continue.";

    case "offer_unavailable":
      return (
        "One of the selected products "
        + "is no longer available."
      );

    case "insufficient_stock":
      return (
        "Stock changed while you were "
        + "shopping. Review your cart."
      );

    case "quote_required":
      return (
        "One of these items now "
        + "requires a quote."
      );

    case "mixed_currency":
      return (
        "All items must use the "
        + "same currency."
      );

    case "quantity_limit_exceeded":
      return (
        "The maximum order quantity "
        + "for one item is 100."
      );

    case "rate_limited":
      return (
        "Too many order attempts. "
        + "Please wait and try again."
      );

    case "csrf_rejected":
      return (
        "The request could not be "
        + "verified. Refresh and retry."
      );

    default:
      return (
        "Unable to create the order. "
        + "Please try again."
      );
  }
}
