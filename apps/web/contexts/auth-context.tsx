"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { clearGuestCart, getGuestCartItems, rememberCartMergeNotice } from "@/lib/guest-cart";
import type { AuthResponse, LoginPayload, RegisterPayload, UserPublic } from "@/lib/types";

type AuthStatus = "checking" | "guest" | "authenticated";

type AuthContextValue = {
  status: AuthStatus;
  user: UserPublic | null;
  accessToken: string | null;
  login: (payload: LoginPayload) => Promise<void>;
  signup: (payload: RegisterPayload) => Promise<void>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function applyAuthResponse(response: AuthResponse, setAccessToken: (token: string | null) => void, setUser: (user: UserPublic | null) => void, setStatus: (status: AuthStatus) => void) {
  setAccessToken(response.access_token);
  setUser(response.user);
  setStatus("authenticated");
}

async function mergeGuestCartAfterAuth(accessToken: string) {
  const items = getGuestCartItems();
  if (items.length === 0) {
    return;
  }
  try {
    const merged = await api.mergeGuestCart(accessToken, items);
    clearGuestCart();
    if (merged.skipped.length > 0) {
      rememberCartMergeNotice(`${merged.skipped.length} unavailable cart item${merged.skipped.length === 1 ? "" : "s"} could not be moved into your account cart.`);
    }
  } catch {
    rememberCartMergeNotice("Your guest cart could not be moved into your account yet. It is still saved on this device.");
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("checking");
  const [user, setUser] = useState<UserPublic | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);

  const refreshSession = useCallback(async () => {
    setStatus("checking");
    try {
      const response = await api.refresh();
      applyAuthResponse(response, setAccessToken, setUser, setStatus);
    } catch {
      setAccessToken(null);
      setUser(null);
      setStatus("guest");
    }
  }, []);

  useEffect(() => {
    void refreshSession();
  }, [refreshSession]);

  const login = useCallback(async (payload: LoginPayload) => {
    const response = await api.login(payload);
    applyAuthResponse(response, setAccessToken, setUser, setStatus);
    await mergeGuestCartAfterAuth(response.access_token);
  }, []);

  const signup = useCallback(async (payload: RegisterPayload) => {
    const response = await api.register(payload);
    applyAuthResponse(response, setAccessToken, setUser, setStatus);
    await mergeGuestCartAfterAuth(response.access_token);
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } finally {
      setAccessToken(null);
      setUser(null);
      setStatus("guest");
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ status, user, accessToken, login, signup, logout, refreshSession }),
    [accessToken, login, logout, refreshSession, signup, status, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }
  return value;
}
