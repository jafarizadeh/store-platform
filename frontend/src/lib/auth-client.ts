export type AuthUser = {
  id: string;
  email: string;
  is_active: boolean;
  created_at: string;
};

export class AuthRequestError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(
    status: number,
    code: string,
  ) {
    super(code);

    this.name = "AuthRequestError";
    this.status = status;
    this.code = code;
  }
}

function readErrorCode(
  value: unknown,
): string {
  if (
    typeof value !== "object" ||
    value === null
  ) {
    return "request_failed";
  }

  const detail = (
    value as {
      detail?: unknown;
    }
  ).detail;

  if (
    typeof detail !== "object" ||
    detail === null
  ) {
    return "request_failed";
  }

  const code = (
    detail as {
      code?: unknown;
    }
  ).code;

  return typeof code === "string"
    ? code
    : "request_failed";
}

async function responseError(
  response: Response,
): Promise<AuthRequestError> {
  let payload: unknown = null;

  try {
    payload = await response.json();
  } catch {
    // The status is still authoritative.
  }

  return new AuthRequestError(
    response.status,
    readErrorCode(payload),
  );
}

async function authJsonRequest(
  path: string,
  init: RequestInit,
): Promise<AuthUser> {
  const response = await fetch(
    path,
    {
      ...init,
      credentials: "same-origin",
      cache: "no-store",
      headers: {
        Accept: "application/json",
        ...(init.headers ?? {}),
      },
    },
  );

  if (!response.ok) {
    throw await responseError(
      response,
    );
  }

  return response.json() as Promise<AuthUser>;
}

export async function registerAccount(
  email: string,
  password: string,
): Promise<AuthUser> {
  return authJsonRequest(
    "/api/auth/register",
    {
      method: "POST",
      headers: {
        "Content-Type":
          "application/json",
      },
      body: JSON.stringify({
        email,
        password,
      }),
    },
  );
}

export async function loginAccount(
  email: string,
  password: string,
): Promise<AuthUser> {
  return authJsonRequest(
    "/api/auth/login",
    {
      method: "POST",
      headers: {
        "Content-Type":
          "application/json",
      },
      body: JSON.stringify({
        email,
        password,
      }),
    },
  );
}

export async function fetchCurrentUser(): Promise<
  AuthUser | null
> {
  const response = await fetch(
    "/api/auth/me",
    {
      method: "GET",
      credentials: "same-origin",
      cache: "no-store",
      headers: {
        Accept: "application/json",
      },
    },
  );

  if (response.status === 401) {
    return null;
  }

  if (!response.ok) {
    throw await responseError(
      response,
    );
  }

  return response.json() as Promise<AuthUser>;
}

export async function logoutAccount(): Promise<void> {
  const response = await fetch(
    "/api/auth/logout",
    {
      method: "POST",
      credentials: "same-origin",
      cache: "no-store",
      headers: {
        Accept: "application/json",
      },
    },
  );

  if (!response.ok) {
    throw await responseError(
      response,
    );
  }
}

export function safeNextPath(
  value: string | null,
): string {
  if (
    !value ||
    !value.startsWith("/") ||
    value.startsWith("//")
  ) {
    return "/account";
  }

  if (
    value.startsWith("/login") ||
    value.startsWith("/register")
  ) {
    return "/account";
  }

  return value;
}

export function authErrorMessage(
  error: unknown,
): string {
  if (
    !(error instanceof AuthRequestError)
  ) {
    return (
      "Something went wrong. "
      + "Please try again."
    );
  }

  switch (error.code) {
    case "invalid_credentials":
      return (
        "Email or password is incorrect."
      );

    case "email_unavailable":
      return (
        "Unable to create an account "
        + "with that email."
      );

    case "rate_limited":
      return (
        "Too many attempts. "
        + "Please wait and try again."
      );

    case "csrf_rejected":
      return (
        "This request could not be "
        + "verified. Refresh the page "
        + "and try again."
      );

    case "auth_backend_unavailable":
      return (
        "Authentication is temporarily "
        + "unavailable."
      );

    case "request_too_large":
    case "invalid_request":
    case "json_required":
      return "Invalid request.";

    default:
      if (error.status === 422) {
        return (
          "Check your email and password "
          + "and try again."
        );
      }

      return (
        "Something went wrong. "
        + "Please try again."
      );
  }
}
