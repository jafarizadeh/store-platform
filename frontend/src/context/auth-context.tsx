"use client";

import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

import {
  type AuthUser,
  fetchCurrentUser,
  loginAccount,
  logoutAccount,
  registerAccount,
} from "@/lib/auth-client";

type AuthContextValue = {
  user: AuthUser | null;
  isLoading: boolean;
  login: (
    email: string,
    password: string,
  ) => Promise<AuthUser>;
  register: (
    email: string,
    password: string,
  ) => Promise<AuthUser>;
  logout: () => Promise<void>;
  refresh: () => Promise<AuthUser | null>;
};

const AuthContext =
  createContext<AuthContextValue | null>(
    null,
  );

export function AuthProvider({
  children,
}: {
  children: ReactNode;
}) {
  const [user, setUser] =
    useState<AuthUser | null>(null);

  const [isLoading, setIsLoading] =
    useState(true);

  useEffect(() => {
    let cancelled = false;

    void fetchCurrentUser()
      .then((currentUser) => {
        if (!cancelled) {
          setUser(currentUser);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setUser(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const refresh = useCallback(
    async (): Promise<AuthUser | null> => {
      const currentUser =
        await fetchCurrentUser();

      setUser(currentUser);

      return currentUser;
    },
    [],
  );

  const login = useCallback(
    async (
      email: string,
      password: string,
    ): Promise<AuthUser> => {
      const currentUser =
        await loginAccount(
          email,
          password,
        );

      setUser(currentUser);

      return currentUser;
    },
    [],
  );

  const register = useCallback(
    async (
      email: string,
      password: string,
    ): Promise<AuthUser> => {
      const currentUser =
        await registerAccount(
          email,
          password,
        );

      setUser(currentUser);

      return currentUser;
    },
    [],
  );

  const logout = useCallback(
    async (): Promise<void> => {
      await logoutAccount();
      setUser(null);
    },
    [],
  );

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        login,
        register,
        logout,
        refresh,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context =
    useContext(AuthContext);

  if (!context) {
    throw new Error(
      "useAuth must be used inside AuthProvider",
    );
  }

  return context;
}
