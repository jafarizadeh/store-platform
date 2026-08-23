import type { NextRequest } from "next/server";

import {
  AUTH_RATE_LIMITS,
  proxyJsonAuthMutation,
} from "@/lib/auth-proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(
  request: NextRequest,
): Promise<Response> {
  return proxyJsonAuthMutation(
    request,
    "/api/v1/auth/register",
    "auth-register",
    AUTH_RATE_LIMITS.register,
  );
}
