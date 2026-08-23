import type { NextRequest } from "next/server";

import {
  AUTH_RATE_LIMITS,
  proxyAuthMutation,
} from "@/lib/auth-proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(
  request: NextRequest,
): Promise<Response> {
  return proxyAuthMutation(
    request,
    "/api/v1/auth/logout",
    "auth-logout",
    AUTH_RATE_LIMITS.logout,
  );
}
