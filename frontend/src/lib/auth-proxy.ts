import "server-only";

import type { NextRequest } from "next/server";

const backendApiUrl =
  process.env.BACKEND_API_URL;

if (!backendApiUrl) {
  throw new Error(
    "BACKEND_API_URL is not configured",
  );
}

const configuredPublicOrigin =
  process.env.PUBLIC_APP_ORIGIN?.trim();

const SESSION_COOKIE_NAME =
  "bynet_session";

const MAX_AUTH_BODY_BYTES = 16_384;

type RateLimitPolicy = Readonly<{
  limit: number;
  windowMs: number;
}>;

type RateLimitState = {
  count: number;
  resetAt: number;
};

const globalRateLimitState =
  globalThis as typeof globalThis & {
    __bynetAuthRateLimits?: Map<
      string,
      RateLimitState
    >;
  };

const rateLimitStore =
  globalRateLimitState.__bynetAuthRateLimits ??
  new Map<string, RateLimitState>();

globalRateLimitState.__bynetAuthRateLimits =
  rateLimitStore;

export const AUTH_RATE_LIMITS = {
  register: {
    limit: 5,
    windowMs: 15 * 60 * 1000,
  },

  login: {
    limit: 20,
    windowMs: 15 * 60 * 1000,
  },

  logout: {
    limit: 30,
    windowMs: 5 * 60 * 1000,
  },

  me: {
    limit: 120,
    windowMs: 60 * 1000,
  },
} satisfies Record<
  string,
  RateLimitPolicy
>;

function firstHeaderValue(
  value: string | null,
): string | null {
  if (!value) {
    return null;
  }

  return (
    value
      .split(",")
      .map((item) => item.trim())
      .find(Boolean) ?? null
  );
}

function expectedOrigin(
  request: NextRequest,
): string {
  if (configuredPublicOrigin) {
    try {
      return new URL(
        configuredPublicOrigin,
      ).origin;
    } catch {
      throw new Error(
        "PUBLIC_APP_ORIGIN is invalid",
      );
    }
  }

  const protocol =
    firstHeaderValue(
      request.headers.get(
        "x-forwarded-proto",
      ),
    ) ??
    request.nextUrl.protocol.replace(
      ":",
      "",
    );

  const host =
    firstHeaderValue(
      request.headers.get(
        "x-forwarded-host",
      ),
    ) ??
    firstHeaderValue(
      request.headers.get("host"),
    ) ??
    request.nextUrl.host;

  return `${protocol}://${host}`;
}

function jsonError(
  status: number,
  code: string,
  extraHeaders?: HeadersInit,
): Response {
  const headers = new Headers(
    extraHeaders,
  );

  headers.set(
    "Content-Type",
    "application/json; charset=utf-8",
  );

  headers.set(
    "Cache-Control",
    "no-store",
  );

  headers.set(
    "Pragma",
    "no-cache",
  );

  headers.set(
    "X-Content-Type-Options",
    "nosniff",
  );

  return new Response(
    JSON.stringify({
      detail: {
        code,
      },
    }),
    {
      status,
      headers,
    },
  );
}

function validateMutationOrigin(
  request: NextRequest,
): Response | null {
  const origin =
    request.headers.get("origin");

  if (!origin) {
    return jsonError(
      403,
      "csrf_rejected",
    );
  }

  const fetchSite =
    request.headers.get(
      "sec-fetch-site",
    );

  if (
    fetchSite &&
    fetchSite !== "same-origin" &&
    fetchSite !== "none"
  ) {
    return jsonError(
      403,
      "csrf_rejected",
    );
  }

  let actualOrigin: string;

  try {
    actualOrigin = new URL(
      origin,
    ).origin;
  } catch {
    return jsonError(
      403,
      "csrf_rejected",
    );
  }

  if (
    actualOrigin !==
    expectedOrigin(request)
  ) {
    return jsonError(
      403,
      "csrf_rejected",
    );
  }

  return null;
}

function clientAddress(
  request: NextRequest,
): string {
  return (
    firstHeaderValue(
      request.headers.get(
        "x-forwarded-for",
      ),
    ) ??
    firstHeaderValue(
      request.headers.get(
        "x-real-ip",
      ),
    ) ??
    "local"
  );
}

function cleanupRateLimits(
  now: number,
): void {
  if (rateLimitStore.size < 1_000) {
    return;
  }

  for (
    const [key, state]
    of rateLimitStore
  ) {
    if (state.resetAt <= now) {
      rateLimitStore.delete(key);
    }
  }
}

function enforceRateLimit(
  request: NextRequest,
  bucket: string,
  policy: RateLimitPolicy,
): Response | null {
  const now = Date.now();

  cleanupRateLimits(now);

  const key =
    `${bucket}:${clientAddress(request)}`;

  const existing =
    rateLimitStore.get(key);

  if (
    !existing ||
    existing.resetAt <= now
  ) {
    rateLimitStore.set(key, {
      count: 1,
      resetAt:
        now + policy.windowMs,
    });

    return null;
  }

  if (
    existing.count >= policy.limit
  ) {
    const retryAfter = Math.max(
      1,
      Math.ceil(
        (
          existing.resetAt - now
        ) / 1000,
      ),
    );

    return jsonError(
      429,
      "rate_limited",
      {
        "Retry-After":
          String(retryAfter),
      },
    );
  }

  existing.count += 1;

  return null;
}

async function readJsonBody(
  request: NextRequest,
): Promise<
  | {
      body: string;
      error: null;
    }
  | {
      body: null;
      error: Response;
    }
> {
  const contentType =
    request.headers.get(
      "content-type",
    );

  if (
    !contentType
      ?.toLowerCase()
      .includes(
        "application/json",
      )
  ) {
    return {
      body: null,
      error: jsonError(
        415,
        "json_required",
      ),
    };
  }

  const declaredLength =
    request.headers.get(
      "content-length",
    );

  if (declaredLength) {
    const parsed =
      Number(declaredLength);

    if (
      !Number.isSafeInteger(parsed) ||
      parsed < 0
    ) {
      return {
        body: null,
        error: jsonError(
          400,
          "invalid_request",
        ),
      };
    }

    if (
      parsed >
      MAX_AUTH_BODY_BYTES
    ) {
      return {
        body: null,
        error: jsonError(
          413,
          "request_too_large",
        ),
      };
    }
  }

  const body =
    await request.text();

  if (
    Buffer.byteLength(
      body,
      "utf8",
    ) > MAX_AUTH_BODY_BYTES
  ) {
    return {
      body: null,
      error: jsonError(
        413,
        "request_too_large",
      ),
    };
  }

  return {
    body,
    error: null,
  };
}

function backendHeaders(
  request: NextRequest,
  hasJsonBody: boolean,
  includeSession: boolean,
): Headers {
  const headers =
    new Headers();

  headers.set(
    "Accept",
    "application/json",
  );

  if (hasJsonBody) {
    headers.set(
      "Content-Type",
      "application/json",
    );
  }

  if (includeSession) {
    const session =
      request.cookies.get(
        SESSION_COOKIE_NAME,
      )?.value;

    if (session) {
      headers.set(
        "Cookie",
        `${SESSION_COOKIE_NAME}=${session}`,
      );
    }
  }

  return headers;
}

async function callBackend(
  request: NextRequest,
  path: string,
  method: "GET" | "POST",
  body: string | undefined,
  includeSession: boolean,
): Promise<Response> {
  const url = new URL(
    path,
    backendApiUrl,
  );

  let backendResponse: Response;

  try {
    backendResponse =
      await fetch(url, {
        method,
        cache: "no-store",
        headers: backendHeaders(
          request,
          body !== undefined,
          includeSession,
        ),
        body,
        signal:
          AbortSignal.timeout(
            5_000,
          ),
      });
  } catch {
    return jsonError(
      502,
      "auth_backend_unavailable",
    );
  }

  const responseHeaders =
    new Headers();

  responseHeaders.set(
    "Cache-Control",
    "no-store",
  );

  responseHeaders.set(
    "Pragma",
    "no-cache",
  );

  responseHeaders.set(
    "X-Content-Type-Options",
    "nosniff",
  );

  const contentType =
    backendResponse.headers.get(
      "content-type",
    );

  if (contentType) {
    responseHeaders.set(
      "Content-Type",
      contentType,
    );
  }

  const headerBag =
    backendResponse.headers as Headers & {
      getSetCookie?: () => string[];
    };

  const setCookies =
    headerBag.getSetCookie?.() ??
    [];

  if (setCookies.length > 0) {
    for (
      const cookie
      of setCookies
    ) {
      responseHeaders.append(
        "Set-Cookie",
        cookie,
      );
    }
  } else {
    const setCookie =
      backendResponse.headers.get(
        "set-cookie",
      );

    if (setCookie) {
      responseHeaders.append(
        "Set-Cookie",
        setCookie,
      );
    }
  }

  const responseBody =
    backendResponse.status === 204
      ? null
      : await backendResponse.text();

  return new Response(
    responseBody,
    {
      status:
        backendResponse.status,
      headers:
        responseHeaders,
    },
  );
}

export async function proxyJsonAuthMutation(
  request: NextRequest,
  path: string,
  bucket: string,
  policy: RateLimitPolicy,
): Promise<Response> {
  const originError =
    validateMutationOrigin(
      request,
    );

  if (originError) {
    return originError;
  }

  const rateLimitError =
    enforceRateLimit(
      request,
      bucket,
      policy,
    );

  if (rateLimitError) {
    return rateLimitError;
  }

  const bodyResult =
    await readJsonBody(
      request,
    );

  if (bodyResult.error) {
    return bodyResult.error;
  }

  return callBackend(
    request,
    path,
    "POST",
    bodyResult.body,
    false,
  );
}

export async function proxyAuthMutation(
  request: NextRequest,
  path: string,
  bucket: string,
  policy: RateLimitPolicy,
): Promise<Response> {
  const originError =
    validateMutationOrigin(
      request,
    );

  if (originError) {
    return originError;
  }

  const rateLimitError =
    enforceRateLimit(
      request,
      bucket,
      policy,
    );

  if (rateLimitError) {
    return rateLimitError;
  }

  return callBackend(
    request,
    path,
    "POST",
    undefined,
    true,
  );
}

export async function proxyAuthGet(
  request: NextRequest,
  path: string,
  bucket: string,
  policy: RateLimitPolicy,
): Promise<Response> {
  const rateLimitError =
    enforceRateLimit(
      request,
      bucket,
      policy,
    );

  if (rateLimitError) {
    return rateLimitError;
  }

  return callBackend(
    request,
    path,
    "GET",
    undefined,
    true,
  );
}
