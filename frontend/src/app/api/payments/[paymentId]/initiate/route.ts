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
    paymentId: string;
  }>;
};

export async function POST(
  request: NextRequest,
  context: RouteContext,
): Promise<Response> {
  const {
    paymentId,
  } = await context.params;

  if (!isUuidPathValue(paymentId)) {
    return invalidPaymentPathResponse();
  }

  return proxyPaymentMutation(
    request,
    `/api/v1/payments/${paymentId}/initiate`,
    "payments-initiate",
    PAYMENT_RATE_LIMITS.initiate,
  );
}
