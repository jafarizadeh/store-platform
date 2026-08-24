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
  order_number: string;
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

type StoredIdempotencyState = {
  signature: string;
  key: string;
};

const IDEMPOTENCY_STORAGE_KEY =
  "bynet-checkout-idempotency-v1";

const IDEMPOTENCY_KEY_PATTERN =
  /^[A-Za-z0-9._~-]{16,128}$/;

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
    // HTTP status remains authoritative.
  }

  return new OrdersRequestError(
    response.status,
    errorCode(payload),
  );
}

function itemSignature(
  items: OrderCreateItem[],
): string {
  const quantities =
    new Map<number, number>();

  for (const item of items) {
    quantities.set(
      item.offer_id,
      (
        quantities.get(
          item.offer_id,
        ) ?? 0
      ) + item.quantity,
    );
  }

  return JSON.stringify(
    Array.from(
      quantities.entries(),
    )
      .sort(
        ([left], [right]) =>
          left - right,
      )
      .map(
        ([offerId, quantity]) => ({
          offer_id: offerId,
          quantity,
        }),
      ),
  );
}

function readStoredIdempotencyState():
  StoredIdempotencyState | null {
  try {
    const raw =
      window.sessionStorage.getItem(
        IDEMPOTENCY_STORAGE_KEY,
      );

    if (!raw) {
      return null;
    }

    const parsed: unknown =
      JSON.parse(raw);

    if (
      typeof parsed !== "object" ||
      parsed === null
    ) {
      return null;
    }

    const candidate =
      parsed as Partial<
        StoredIdempotencyState
      >;

    if (
      typeof candidate.signature
        !== "string" ||
      typeof candidate.key
        !== "string" ||
      !IDEMPOTENCY_KEY_PATTERN.test(
        candidate.key,
      )
    ) {
      return null;
    }

    return {
      signature:
        candidate.signature,
      key: candidate.key,
    };
  } catch {
    return null;
  }
}

function idempotencyKeyFor(
  items: OrderCreateItem[],
): string {
  const signature =
    itemSignature(items);

  const stored =
    readStoredIdempotencyState();

  if (
    stored?.signature === signature
  ) {
    return stored.key;
  }

  const key =
    crypto.randomUUID();

  try {
    window.sessionStorage.setItem(
      IDEMPOTENCY_STORAGE_KEY,
      JSON.stringify({
        signature,
        key,
      }),
    );
  } catch {
    // The request remains safe for this
    // attempt even if storage is disabled.
  }

  return key;
}

function clearIdempotencyKey(
  key: string,
): void {
  const stored =
    readStoredIdempotencyState();

  if (stored?.key !== key) {
    return;
  }

  try {
    window.sessionStorage.removeItem(
      IDEMPOTENCY_STORAGE_KEY,
    );
  } catch {
    // Nothing else is required.
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
    throw await requestError(
      response,
    );
  }

  const payload =
    await response.json();

  return payload as CustomerOrder[];
}

export async function createOrder(
  items: OrderCreateItem[],
): Promise<CustomerOrder> {
  const idempotencyKey =
    idempotencyKeyFor(items);

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
        "Idempotency-Key":
          idempotencyKey,
      },
      body: JSON.stringify({
        items,
      }),
    },
  );

  if (!response.ok) {
    const error =
      await requestError(
        response,
      );

    if (
      error.code ===
      "idempotency_conflict"
    ) {
      clearIdempotencyKey(
        idempotencyKey,
      );
    }

    throw error;
  }

  const payload =
    await response.json();

  clearIdempotencyKey(
    idempotencyKey,
  );

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
      return (
        "Please sign in to continue."
      );

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

    case "invalid_idempotency_key":
      return (
        "The checkout request could not "
        + "be validated. Refresh and retry."
      );

    case "idempotency_conflict":
      return (
        "This checkout attempt changed "
        + "unexpectedly. Please retry."
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
