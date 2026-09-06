export type CartValidationRequestItem = {
  offer_id: number;
  quantity: number;
};

export type CartValidationIssue =
  | "offer_unavailable"
  | "quote_required"
  | "insufficient_stock"
  | "quantity_limit_exceeded";

export type CartValidationItem = {
  offer_id: number;
  requested_quantity: number;
  issue: CartValidationIssue | null;

  product_slug: string | null;
  product_name: string | null;
  offer_name: string | null;
  sku: string | null;
  fulfillment_type: string | null;

  unit_price_cents: number | null;
  currency: string | null;

  image_path: string | null;

  available_quantity: number | null;
  max_quantity: number | null;
};

export type CartValidationResult = {
  valid: boolean;
  currency: string | null;
  subtotal_cents: number | null;
  mixed_currency: boolean;
  items: CartValidationItem[];
};

export class CartValidationRequestError
  extends Error {
  readonly status: number;
  readonly code: string;

  constructor(
    status: number,
    code: string,
  ) {
    super(code);

    this.name =
      "CartValidationRequestError";
    this.status = status;
    this.code = code;
  }
}

function errorCode(
  payload: unknown,
): string {
  if (
    typeof payload !== "object"
    || payload === null
  ) {
    return "request_failed";
  }

  const detail = (
    payload as {
      detail?: unknown;
    }
  ).detail;

  if (
    typeof detail !== "object"
    || detail === null
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
): Promise<CartValidationRequestError> {
  let payload: unknown = null;

  try {
    payload = await response.json();
  } catch {
    // HTTP status remains authoritative.
  }

  return new CartValidationRequestError(
    response.status,
    errorCode(payload),
  );
}

export async function validateCart(
  items: CartValidationRequestItem[],
): Promise<CartValidationResult> {
  const response = await fetch(
    "/api/cart/validate",
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

  const payload =
    await response.json();

  return payload as CartValidationResult;
}

export function cartValidationErrorMessage(
  error: unknown,
): string {
  if (
    !(
      error
      instanceof CartValidationRequestError
    )
  ) {
    return (
      "Unable to validate the cart. "
      + "Please try again."
    );
  }

  switch (error.code) {
    case "rate_limited":
      return (
        "Too many cart requests. "
        + "Please wait and try again."
      );

    case "csrf_rejected":
      return (
        "The request could not be verified. "
        + "Refresh and try again."
      );

    case "json_required":
    case "invalid_request":
      return (
        "The cart request could not be "
        + "validated."
      );

    case "request_too_large":
      return (
        "The cart contains too much data."
      );

    default:
      return (
        "Unable to validate the cart. "
        + "Please try again."
      );
  }
}
