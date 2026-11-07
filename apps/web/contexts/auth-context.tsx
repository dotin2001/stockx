"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { api, setAuthSessionAdapter } from "@/lib/api";
import { createAuthSessionCoordinator } from "@/lib/auth-session";
import { clearGuestCart, getGuestCartItems, rememberCartMergeNotice } from "@/lib/guest-cart";
import { currentProtectedReturnUrl } from "@/lib/return-url";
import type { AuthResponse, LoginPayload, RegisterPayload, UserPublic } from "@/lib/types";

type AuthStatus = "checking" | "guest" | "authenticated";

type AuthContextValue = {
  status: AuthStatus;
  user: UserPublic | null;
  accessToken: string | null;
  login: (payload: LoginPayload) => Promise<void>;
  signup: (payload: RegisterPayload) => Promise<void>;
  logout: () => Promise<void>;
  logoutAll: () => Promise<void>;
  refreshSession: () => Promise<void>;
  updateUserIfMatches: (updatedUser: UserPublic) => boolean;
};

const AuthContext = createContext<AuthContextValue | null>(null);

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
  const sessionRef = useRef({ accessToken: null as string | null, user: null as UserPublic | null, generation: 0 });
  const initializedRef = useRef(false);

  const applyAuthResponse = useCallback((response: AuthResponse, expectedGeneration?: number) => {
    if (expectedGeneration !== undefined && sessionRef.current.generation !== expectedGeneration) return false;
    sessionRef.current = {
      accessToken: response.access_token,
      user: response.user,
      generation: sessionRef.current.generation + 1
    };
    setAccessToken(response.access_token);
    setUser(response.user);
    setStatus("authenticated");
    return true;
  }, []);

  const clearSession = useCallback((expectedGeneration?: number, recoverProtectedJourney = false) => {
    if (expectedGeneration !== undefined && sessionRef.current.generation !== expectedGeneration) return false;
    sessionRef.current = {
      accessToken: null,
      user: null,
      generation: sessionRef.current.generation + 1
    };
    setAccessToken(null);
    setUser(null);
    setStatus("guest");

    if (recoverProtectedJourney && typeof window !== "undefined") {
      const returnUrl = currentProtectedReturnUrl();
      if (returnUrl) {
        window.location.assign(`/login?redirect=${encodeURIComponent(returnUrl)}&session=expired`);
      }
    }
    return true;
  }, []);

  const sessionAdapter = useMemo(() => createAuthSessionCoordinator({
    snapshot: () => ({
      accessToken: sessionRef.current.accessToken,
      generation: sessionRef.current.generation
    }),
    requestRefresh: () => api.refresh(),
    apply: (response, expectedGeneration) => applyAuthResponse(response, expectedGeneration),
    terminate: (expectedGeneration) => {
      clearSession(expectedGeneration, true);
    }
  }), [applyAuthResponse, clearSession]);

  useEffect(() => {
    setAuthSessionAdapter(sessionAdapter);
    return () => setAuthSessionAdapter(null);
  }, [sessionAdapter]);

  const refreshSession = useCallback(async () => {
    setStatus("checking");
    const expectedGeneration = sessionRef.current.generation;
    try {
      await sessionAdapter.refresh(expectedGeneration);
    } catch {
      // The coordinator clears current state and redirects only for protected journeys.
    }
  }, [sessionAdapter]);

  useEffect(() => {
    if (initializedRef.current) return;
    initializedRef.current = true;
    void refreshSession();
  }, [refreshSession]);

  const login = useCallback(async (payload: LoginPayload) => {
    const response = await api.login(payload);
    applyAuthResponse(response);
    await mergeGuestCartAfterAuth(response.access_token);
  }, [applyAuthResponse]);

  const signup = useCallback(async (payload: RegisterPayload) => {
    const response = await api.register(payload);
    applyAuthResponse(response);
    await mergeGuestCartAfterAuth(response.access_token);
  }, [applyAuthResponse]);

  const logout = useCallback(async () => {
    sessionRef.current = { ...sessionRef.current, generation: sessionRef.current.generation + 1 };
    try {
      await api.logout();
    } finally {
      clearSession();
    }
  }, [clearSession]);

  const logoutAll = useCallback(async () => {
    const token = sessionRef.current.accessToken;
    if (!token) throw new Error("An authenticated session is required.");
    await api.logoutAll(token);
    clearSession();
    if (typeof window !== "undefined") window.location.assign("/login?loggedOut=all");
  }, [clearSession]);

  const updateUserIfMatches = useCallback((updatedUser: UserPublic) => {
    if (!sessionRef.current.user || sessionRef.current.user.id !== updatedUser.id) return false;
    sessionRef.current = { ...sessionRef.current, user: updatedUser };
    setUser(updatedUser);
    return true;
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ status, user, accessToken, login, signup, logout, logoutAll, refreshSession, updateUserIfMatches }),
    [accessToken, login, logout, logoutAll, refreshSession, signup, status, updateUserIfMatches, user]
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
