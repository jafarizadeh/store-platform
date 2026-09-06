import type { NextRequest } from "next/server";

import {
  proxyJsonAuthMutation,
} from "@/lib/auth-proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const CART_VALIDATE_RATE_LIMIT = {
  limit: 120,
  windowMs: 60 * 1000,
} as const;

export async function POST(
  request: NextRequest,
): Promise<Response> {
  return proxyJsonAuthMutation(
    request,
    "/api/v1/cart/validate",
    "cart-validate",
    CART_VALIDATE_RATE_LIMIT,
  );
}
