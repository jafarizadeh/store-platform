import "server-only";

import type { NextRequest } from "next/server";

import {
  proxyAuthenticatedJsonMutation,
} from "@/lib/auth-proxy";

type RateLimitPolicy = Readonly<{
  limit: number;
  windowMs: number;
}>;

const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

const PAYMENT_BACKEND_OPTIONS = {
  // Backend provider timeout is capped at
  // 30 seconds. Keep the BFF boundary longer
  // so the backend remains authoritative.
  timeoutMs: 35_000,
  unavailableCode:
    "payment_backend_unavailable",
} as const;

export const PAYMENT_RATE_LIMITS = {
  prepare: {
    limit: 30,
    windowMs: 10 * 60 * 1000,
  },

  initiate: {
    limit: 20,
    windowMs: 10 * 60 * 1000,
  },

  complete: {
    limit: 30,
    windowMs: 10 * 60 * 1000,
  },

  refresh: {
    limit: 60,
    windowMs: 5 * 60 * 1000,
  },
} satisfies Record<
  string,
  RateLimitPolicy
>;

export function isUuidPathValue(
  value: string,
): boolean {
  return UUID_PATTERN.test(value);
}

export function invalidPaymentPathResponse():
  Response {
  return new Response(
    JSON.stringify({
      detail: {
        code: "invalid_request",
      },
    }),
    {
      status: 400,
      headers: {
        "Content-Type":
          "application/json; charset=utf-8",
        "Cache-Control": "no-store",
        Pragma: "no-cache",
        "X-Content-Type-Options":
          "nosniff",
      },
    },
  );
}

export async function proxyPaymentMutation(
  request: NextRequest,
  path: string,
  bucket: string,
  policy: RateLimitPolicy,
): Promise<Response> {
  return proxyAuthenticatedJsonMutation(
    request,
    path,
    bucket,
    policy,
    PAYMENT_BACKEND_OPTIONS,
  );
}
