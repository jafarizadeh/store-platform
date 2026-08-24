import type { NextRequest } from "next/server";

import {
  PAYMENT_RATE_LIMITS,
  proxyPaymentMutation,
} from "@/lib/payment-bff";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(
  request: NextRequest,
): Promise<Response> {
  return proxyPaymentMutation(
    request,
    "/api/v1/payments",
    "payments-prepare",
    PAYMENT_RATE_LIMITS.prepare,
  );
}
