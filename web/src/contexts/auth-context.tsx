"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, type AuthUser } from "@/lib/api";

interface AuthContextType {
  user: AuthUser | null;
  isLoading: boolean;
  authEnabled: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<string>;
  logout: () => Promise<void>;
  error: string | null;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [authEnabled, setAuthEnabled] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Check session on mount
  useEffect(() => {
    api.auth
      .me()
      .then((u) => {
        setUser(u);
        setAuthEnabled(u.user_id !== "local");
      })
      .catch(() => {
        setUser(null);
        setAuthEnabled(true); // If /me fails with 401, auth is enabled
      })
      .finally(() => setIsLoading(false));
  }, []);

  const login = async (email: string, password: string) => {
    setError(null);
    try {
      const u = await api.auth.login(email, password);
      setUser(u);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Login failed";
      // Extract detail from API error
      const match = msg.match(/API \d+: (.*)/);
      const detail = match ? JSON.parse(match[1])?.detail ?? msg : msg;
      setError(detail);
      throw err;
    }
  };

  const signup = async (email: string, password: string): Promise<string> => {
    setError(null);
    try {
      const res = await api.auth.signup(email, password);
      return res.message;
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Signup failed";
      const match = msg.match(/API \d+: (.*)/);
      const detail = match ? JSON.parse(match[1])?.detail ?? msg : msg;
      setError(detail);
      throw err;
    }
  };

  const logout = async () => {
    await api.auth.logout();
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        authEnabled,
        login,
        signup,
        logout,
        error,
        clearError: () => setError(null),
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
