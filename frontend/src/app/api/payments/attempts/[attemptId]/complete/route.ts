import type { NextRequest } from "next/server";

import {
  invalidPaymentPathResponse,
  isUuidPathValue,
  PAYMENT_RATE_LIMITS,
  proxyPaymentMutation,
} from "@/lib/payment-bff";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type RouteContext = {
  params: Promise<{
    attemptId: string;
  }>;
};

export async function POST(
  request: NextRequest,
  context: RouteContext,
): Promise<Response> {
  const {
    attemptId,
  } = await context.params;

  if (!isUuidPathValue(attemptId)) {
    return invalidPaymentPathResponse();
  }

  return proxyPaymentMutation(
    request,
    (
      "/api/v1/payments/attempts/"
      + `${attemptId}/complete`
    ),
    "payments-complete",
    PAYMENT_RATE_LIMITS.complete,
  );
}
