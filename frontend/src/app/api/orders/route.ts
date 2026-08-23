import type { NextRequest } from "next/server";

import {
  proxyAuthGet,
} from "@/lib/auth-proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const ORDER_HISTORY_RATE_LIMIT = {
  limit: 120,
  windowMs: 60 * 1000,
} as const;

export async function GET(
  request: NextRequest,
): Promise<Response> {
  return proxyAuthGet(
    request,
    "/api/v1/orders",
    "orders-list",
    ORDER_HISTORY_RATE_LIMIT,
  );
}
