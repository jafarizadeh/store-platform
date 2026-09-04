export type CheckoutPaymentFlow = {
  orderId: string;
  orderNumber: string;
  paymentId: string;
  attemptId: string;
  provider: "paypal";
};

const STORAGE_KEY =
  "bynet-checkout-payment-flow-v1";

const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

const ORDER_NUMBER_PATTERN =
  /^(?:BN-\d{6}-\d{4}|BY-\d{4}-\d{8})$/;

function validFlow(
  value: unknown,
): value is CheckoutPaymentFlow {
  if (
    typeof value !== "object"
    || value === null
  ) {
    return false;
  }

  const candidate =
    value as Partial<CheckoutPaymentFlow>;

  return (
    typeof candidate.orderId === "string"
    && UUID_PATTERN.test(
      candidate.orderId,
    )
    && typeof candidate.orderNumber
      === "string"
    && ORDER_NUMBER_PATTERN.test(
      candidate.orderNumber,
    )
    && typeof candidate.paymentId
      === "string"
    && UUID_PATTERN.test(
      candidate.paymentId,
    )
    && typeof candidate.attemptId
      === "string"
    && UUID_PATTERN.test(
      candidate.attemptId,
    )
    && candidate.provider === "paypal"
  );
}

export function storePaymentFlow(
  flow: CheckoutPaymentFlow,
): void {
  window.sessionStorage.setItem(
    STORAGE_KEY,
    JSON.stringify(flow),
  );
}

export function readPaymentFlow():
  CheckoutPaymentFlow | null {
  try {
    const raw =
      window.sessionStorage.getItem(
        STORAGE_KEY,
      );

    if (!raw) {
      return null;
    }

    const parsed: unknown =
      JSON.parse(raw);

    if (!validFlow(parsed)) {
      window.sessionStorage.removeItem(
        STORAGE_KEY,
      );

      return null;
    }

    return parsed;
  } catch {
    return null;
  }
}

export function clearPaymentFlow(): void {
  try {
    window.sessionStorage.removeItem(
      STORAGE_KEY,
    );
  } catch {
    // Nothing else is required.
  }
}
