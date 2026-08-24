export type PaymentAttemptStatus =
  | "created"
  | "pending"
  | "succeeded"
  | "failed"
  | "cancelled";

export type PaymentRecord = {
  id: string;
  order_id: string;
  status: string;
  amount_cents: number;
  currency: string;
  created_at: string;
  updated_at: string;
};

export type PaymentInitiation = {
  attempt_id: string;
  status: PaymentAttemptStatus;
  provider_reference: string | null;
  approval_url: string | null;
  failure_code: string | null;
};

export type PaymentCompletion = {
  attempt_id: string;
  status: PaymentAttemptStatus;
  provider_reference: string;
  failure_code: string | null;
};

export type PaymentStatusRefresh = {
  attempt_id: string;
  order_id: string;
  order_number: string;
  status: PaymentAttemptStatus;
  provider_reference: string;
  failure_code: string | null;
};

const IDEMPOTENCY_PREFIX =
  "bynet-payment-initiation-v1:";

const IDEMPOTENCY_KEY_PATTERN =
  /^[A-Za-z0-9._~-]{16,128}$/;

export class PaymentRequestError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(
    status: number,
    code: string,
  ) {
    super(code);

    this.name = "PaymentRequestError";
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
): Promise<PaymentRequestError> {
  let payload: unknown = null;

  try {
    payload = await response.json();
  } catch {
    // HTTP status remains authoritative.
  }

  return new PaymentRequestError(
    response.status,
    errorCode(payload),
  );
}

async function postJson<T>(
  path: string,
  body: unknown,
  extraHeaders?: HeadersInit,
): Promise<T> {
  const headers = new Headers(
    extraHeaders,
  );

  headers.set(
    "Accept",
    "application/json",
  );

  headers.set(
    "Content-Type",
    "application/json",
  );

  const response = await fetch(
    path,
    {
      method: "POST",
      credentials: "same-origin",
      cache: "no-store",
      headers,
      body: JSON.stringify(body),
    },
  );

  if (!response.ok) {
    throw await requestError(
      response,
    );
  }

  return await response.json() as T;
}

function initiationStorageKey(
  paymentId: string,
  provider: string,
): string {
  return (
    IDEMPOTENCY_PREFIX
    + paymentId
    + ":"
    + provider
  );
}

function initiationIdempotencyKey(
  paymentId: string,
  provider: string,
): string {
  const storageKey =
    initiationStorageKey(
      paymentId,
      provider,
    );

  try {
    const stored =
      window.sessionStorage.getItem(
        storageKey,
      );

    if (
      stored
      && IDEMPOTENCY_KEY_PATTERN.test(
        stored,
      )
    ) {
      return stored;
    }
  } catch {
    // Generate a safe key even if storage
    // is unavailable.
  }

  const key = crypto.randomUUID();

  try {
    window.sessionStorage.setItem(
      storageKey,
      key,
    );
  } catch {
    // Current request remains idempotent.
  }

  return key;
}

export function clearPaymentInitiationKey(
  paymentId: string,
  provider: string,
): void {
  try {
    window.sessionStorage.removeItem(
      initiationStorageKey(
        paymentId,
        provider,
      ),
    );
  } catch {
    // Nothing else is required.
  }
}

export async function preparePayment(
  orderId: string,
): Promise<PaymentRecord> {
  return postJson<PaymentRecord>(
    "/api/payments",
    {
      order_id: orderId,
    },
  );
}

export async function initiatePayment(
  paymentId: string,
  provider: string,
): Promise<PaymentInitiation> {
  const idempotencyKey =
    initiationIdempotencyKey(
      paymentId,
      provider,
    );

  return postJson<PaymentInitiation>(
    (
      `/api/payments/${encodeURIComponent(
        paymentId,
      )}/initiate`
    ),
    {
      provider,
    },
    {
      "Idempotency-Key":
        idempotencyKey,
    },
  );
}

export async function completePayment(
  attemptId: string,
  provider: string,
): Promise<PaymentCompletion> {
  return postJson<PaymentCompletion>(
    (
      "/api/payments/attempts/"
      + `${encodeURIComponent(
        attemptId,
      )}/complete`
    ),
    {
      provider,
    },
  );
}

export async function refreshPaymentStatus(
  attemptId: string,
  provider: string,
): Promise<PaymentStatusRefresh> {
  return postJson<PaymentStatusRefresh>(
    (
      "/api/payments/attempts/"
      + `${encodeURIComponent(
        attemptId,
      )}/refresh`
    ),
    {
      provider,
    },
  );
}

export function paymentErrorMessage(
  error: unknown,
): string {
  if (
    !(error instanceof PaymentRequestError)
  ) {
    return (
      "Unable to continue payment. "
      + "Please try again."
    );
  }

  switch (error.code) {
    case "not_authenticated":
      return "Please sign in to continue.";

    case "payment_order_unavailable":
    case "payment_attempt_unavailable":
      return (
        "This payment is no longer "
        + "available."
      );

    case "reservation_expired":
      return (
        "The order reservation expired. "
        + "Please review your cart again."
      );

    case "order_not_payable":
      return (
        "This order can no longer "
        + "be paid."
      );

    case "payment_not_pending":
      return (
        "This payment is already in a "
        + "final state."
      );

    case "unsupported_payment_provider":
      return (
        "The selected payment method "
        + "is not available."
      );

    case "unresolved_payment_attempt":
      return (
        "A payment attempt is already "
        + "in progress."
      );

    case "payment_provider_unavailable":
    case "payment_backend_unavailable":
      return (
        "The payment service is "
        + "temporarily unavailable. "
        + "No new payment should be "
        + "started yet."
      );

    case "payment_provider_error":
      return (
        "The payment provider returned "
        + "an invalid response. "
        + "Please retry safely."
      );

    case "invalid_idempotency_key":
    case "idempotency_conflict":
      return (
        "The payment attempt could not "
        + "be safely verified. "
        + "Refresh and try again."
      );

    case "rate_limited":
      return (
        "Too many payment requests. "
        + "Please wait and try again."
      );

    case "csrf_rejected":
      return (
        "The payment request could not "
        + "be verified. Refresh and retry."
      );

    default:
      return (
        "Unable to continue payment. "
        + "Please try again."
      );
  }
}
