import {
  type NextRequest,
  NextResponse,
} from "next/server";


function buildContentSecurityPolicy(
  nonce: string,
  isDevelopment: boolean,
): string {
  const directives = [
    "default-src 'self'",

    [
      "script-src 'self'",
      `'nonce-${nonce}'`,
      "'strict-dynamic'",
      isDevelopment ? "'unsafe-eval'" : "",
    ]
      .filter(Boolean)
      .join(" "),

    [
      "style-src 'self'",
      `'nonce-${nonce}'`,
      isDevelopment ? "'unsafe-inline'" : "",
    ]
      .filter(Boolean)
      .join(" "),

    "img-src 'self' blob: data:",
    "font-src 'self'",

    [
      "connect-src 'self'",
      isDevelopment ? "ws: wss:" : "",
    ]
      .filter(Boolean)
      .join(" "),

    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    "worker-src 'self' blob:",
    "manifest-src 'self'",
  ];

  return `${directives.join("; ")};`;
}


export function proxy(
  request: NextRequest,
) {
  const nonce = Buffer.from(
    crypto.randomUUID(),
  ).toString("base64");

  const contentSecurityPolicy =
    buildContentSecurityPolicy(
      nonce,
      process.env.NODE_ENV === "development",
    );

  const requestHeaders = new Headers(
    request.headers,
  );

  requestHeaders.set(
    "x-nonce",
    nonce,
  );

  requestHeaders.set(
    "Content-Security-Policy",
    contentSecurityPolicy,
  );

  const response = NextResponse.next({
    request: {
      headers: requestHeaders,
    },
  });

  response.headers.set(
    "Content-Security-Policy",
    contentSecurityPolicy,
  );

  response.headers.set(
    "X-Content-Type-Options",
    "nosniff",
  );

  response.headers.set(
    "X-Frame-Options",
    "DENY",
  );

  response.headers.set(
    "Referrer-Policy",
    "strict-origin-when-cross-origin",
  );

  response.headers.set(
    "Permissions-Policy",
    "camera=(), microphone=(), geolocation=()",
  );

  response.headers.set(
    "Cross-Origin-Opener-Policy",
    "same-origin",
  );

  response.headers.set(
    "Cross-Origin-Resource-Policy",
    "same-origin",
  );

  response.headers.set(
    "X-Permitted-Cross-Domain-Policies",
    "none",
  );

  return response;
}


export const config = {
  matcher: [
    {
      source:
        "/((?!api|_next/static|_next/image|favicon.ico).*)",
      missing: [
        {
          type: "header",
          key: "next-router-prefetch",
        },
        {
          type: "header",
          key: "purpose",
          value: "prefetch",
        },
      ],
    },
  ],
};
