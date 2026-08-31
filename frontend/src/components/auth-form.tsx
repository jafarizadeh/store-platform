"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  type FormEvent,
  useState,
} from "react";

import { useAuth } from "@/context/auth-context";
import {
  authErrorMessage,
  safeNextPath,
} from "@/lib/auth-client";

type AuthFormProps = {
  mode: "login" | "register";
};

export default function AuthForm({
  mode,
}: AuthFormProps) {
  const router = useRouter();

  const {
    user,
    isLoading,
    login,
    register,
  } = useAuth();

  const [email, setEmail] =
    useState("");

  const [password, setPassword] =
    useState("");

  const [
    confirmPassword,
    setConfirmPassword,
  ] = useState("");

  const [
    showPassword,
    setShowPassword,
  ] = useState(false);

  const [
    showConfirmPassword,
    setShowConfirmPassword,
  ] = useState(false);

  const [error, setError] =
    useState<string | null>(null);

  const [isSubmitting, setIsSubmitting] =
    useState(false);

  const isRegister =
    mode === "register";

  const passwordMeetsLength =
    password.length >= 12;

  const hasConfirmation =
    confirmPassword.length > 0;

  const passwordsMatch =
    hasConfirmation &&
    password === confirmPassword;

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();

    if (isSubmitting) {
      return;
    }

    setError(null);

    if (
      isRegister &&
      password !== confirmPassword
    ) {
      setError(
        "Passwords do not match.",
      );

      return;
    }

    setIsSubmitting(true);

    try {
      if (isRegister) {
        await register(
          email,
          password,
        );
      } else {
        await login(
          email,
          password,
        );
      }

      const next = safeNextPath(
        new URLSearchParams(
          window.location.search,
        ).get("next"),
      );

      router.replace(next);
      router.refresh();
    } catch (requestError) {
      setError(
        authErrorMessage(
          requestError,
        ),
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  if (
    !isLoading &&
    user
  ) {
    return (
      <div className="rounded-[2rem] border border-neutral-200 bg-white p-8 shadow-[0_24px_80px_rgba(0,0,0,0.06)] sm:p-10">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-neutral-500">
          Signed in
        </p>

        <h2 className="mt-4 text-3xl font-semibold tracking-[-0.045em]">
          You&apos;re already signed in.
        </h2>

        <p className="mt-4 break-all text-sm leading-6 text-neutral-600">
          {user.email}
        </p>

        <Link
          href="/account"
          className="mt-7 inline-flex rounded-full bg-neutral-950 px-6 py-3 text-sm font-semibold text-white transition hover:bg-neutral-700"
        >
          Go to account
        </Link>
      </div>
    );
  }

  return (
    <div className="rounded-[2rem] border border-neutral-200 bg-white p-8 shadow-[0_24px_80px_rgba(0,0,0,0.06)] sm:p-10">
      <p className="text-xs font-semibold uppercase tracking-[0.24em] text-neutral-500">
        {isRegister
          ? "Create account"
          : "Welcome back"}
      </p>

      <h2 className="mt-4 text-3xl font-semibold tracking-[-0.045em] sm:text-4xl">
        {isRegister
          ? "Join ByNET."
          : "Sign in."}
      </h2>

      <p className="mt-4 text-sm leading-6 text-neutral-600">
        {isRegister
          ? "Create an account to manage orders and future Raspberry Pi projects."
          : "Access your ByNET account and orders."}
      </p>

      <form
        onSubmit={handleSubmit}
        className="mt-8 space-y-5"
      >
        <div>
          <label
            htmlFor={`${mode}-email`}
            className="text-sm font-medium"
          >
            Email
          </label>

          <input
            id={`${mode}-email`}
            name="email"
            type="email"
            inputMode="email"
            autoComplete="email"
            required
            maxLength={320}
            value={email}
            onChange={(event) => {
              setEmail(
                event.target.value,
              );
            }}
            className="mt-2 w-full rounded-2xl border border-neutral-300 bg-white px-4 py-3.5 text-base outline-none transition focus:border-neutral-950"
            placeholder="you@example.com"
          />
        </div>

        <div>
          <label
            htmlFor={`${mode}-password`}
            className="text-sm font-medium"
          >
            Password
          </label>

          <div className="relative mt-2">
            <input
              id={`${mode}-password`}
              name="password"
              type={
                showPassword
                  ? "text"
                  : "password"
              }
              autoComplete={
                isRegister
                  ? "new-password"
                  : "current-password"
              }
              required
              minLength={
                isRegister
                  ? 12
                  : 1
              }
              maxLength={128}
              value={password}
              onChange={(event) => {
                setPassword(
                  event.target.value,
                );
              }}
              aria-describedby={
                isRegister
                  ? "password-requirements"
                  : undefined
              }
              className="w-full rounded-2xl border border-neutral-300 bg-white px-4 py-3.5 pr-20 text-base outline-none transition focus:border-neutral-950"
            />

            <button
              type="button"
              onClick={() => {
                setShowPassword(
                  (current) => !current,
                );
              }}
              className="absolute inset-y-0 right-4 text-xs font-semibold text-neutral-600 hover:text-neutral-950"
              aria-label={
                showPassword
                  ? "Hide password"
                  : "Show password"
              }
            >
              {showPassword
                ? "Hide"
                : "Show"}
            </button>
          </div>

          {isRegister && (
            <p
              id="password-requirements"
              className={`mt-2 text-xs leading-5 ${
                password.length === 0
                  ? "text-neutral-500"
                  : passwordMeetsLength
                    ? "text-emerald-700"
                    : "text-red-700"
              }`}
            >
              {password.length === 0
                ? "Use at least 12 characters."
                : passwordMeetsLength
                  ? "Password length is valid."
                  : "Use at least 12 characters."}
            </p>
          )}
        </div>

        {isRegister && (
          <div>
            <label
              htmlFor="register-confirm-password"
              className="text-sm font-medium"
            >
              Confirm password
            </label>

            <div className="relative mt-2">
              <input
                id="register-confirm-password"
                name="confirm-password"
                type={
                  showConfirmPassword
                    ? "text"
                    : "password"
                }
                autoComplete="new-password"
                required
                minLength={12}
                maxLength={128}
                value={confirmPassword}
                onChange={(event) => {
                  setConfirmPassword(
                    event.target.value,
                  );
                }}
                aria-invalid={
                  hasConfirmation &&
                  !passwordsMatch
                }
                aria-describedby="confirm-password-status"
                className={`w-full rounded-2xl border bg-white px-4 py-3.5 pr-20 text-base outline-none transition ${
                  hasConfirmation &&
                  !passwordsMatch
                    ? "border-red-300 focus:border-red-600"
                    : "border-neutral-300 focus:border-neutral-950"
                }`}
              />

              <button
                type="button"
                onClick={() => {
                  setShowConfirmPassword(
                    (current) => !current,
                  );
                }}
                className="absolute inset-y-0 right-4 text-xs font-semibold text-neutral-600 hover:text-neutral-950"
                aria-label={
                  showConfirmPassword
                    ? "Hide confirmation password"
                    : "Show confirmation password"
                }
              >
                {showConfirmPassword
                  ? "Hide"
                  : "Show"}
              </button>
            </div>

            <p
              id="confirm-password-status"
              aria-live="polite"
              className={`mt-2 text-xs leading-5 ${
                !hasConfirmation
                  ? "text-neutral-500"
                  : passwordsMatch
                    ? "text-emerald-700"
                    : "text-red-700"
              }`}
            >
              {!hasConfirmation
                ? "Re-enter your password."
                : passwordsMatch
                  ? "Passwords match."
                  : "Passwords do not match."}
            </p>
          </div>
        )}

        {error && (
          <div
            role="alert"
            className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm leading-6 text-red-800"
          >
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={
            isSubmitting ||
            isLoading
          }
          className="w-full rounded-full bg-neutral-950 px-6 py-3.5 text-sm font-semibold text-white transition hover:bg-neutral-700 disabled:cursor-not-allowed disabled:bg-neutral-400"
        >
          {isSubmitting
            ? "Please wait..."
            : isRegister
              ? "Create account"
              : "Sign in"}
        </button>
      </form>

      <div className="mt-7 border-t border-neutral-200 pt-6 text-sm text-neutral-600">
        {isRegister ? (
          <>
            Already have an account?{" "}
            <Link
              href="/login"
              className="font-semibold text-neutral-950 hover:underline"
            >
              Sign in
            </Link>
          </>
        ) : (
          <>
            New to ByNET?{" "}
            <Link
              href="/register"
              className="font-semibold text-neutral-950 hover:underline"
            >
              Create account
            </Link>
          </>
        )}
      </div>
    </div>
  );
}
