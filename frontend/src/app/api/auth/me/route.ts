import type { NextRequest } from "next/server";

import {
  AUTH_RATE_LIMITS,
  proxyAuthGet,
} from "@/lib/auth-proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(
  request: NextRequest,
): Promise<Response> {
  return proxyAuthGet(
    request,
    "/api/v1/auth/me",
    "auth-me",
    AUTH_RATE_LIMITS.me,
  );
}
