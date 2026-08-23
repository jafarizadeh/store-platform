import type { NextRequest } from "next/server";

import {
  proxyAuthenticatedJsonMutation,
  proxyAuthGet,
} from "@/lib/auth-proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const ORDER_HISTORY_RATE_LIMIT = {
  limit: 120,
  windowMs: 60 * 1000,
} as const;

const ORDER_CREATE_RATE_LIMIT = {
  limit: 20,
  windowMs: 10 * 60 * 1000,
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

export async function POST(
  request: NextRequest,
): Promise<Response> {
  return proxyAuthenticatedJsonMutation(
    request,
    "/api/v1/orders",
    "orders-create",
    ORDER_CREATE_RATE_LIMIT,
  );
}
