import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, tokenStore } from "./api";
import type { Me, UserRole } from "./types";

interface AuthContextValue {
  user: Me | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  hasRole: (minimum: UserRole) => boolean;
}

const ROLE_RANK: Record<UserRole, number> = { viewer: 0, analyst: 1, admin: 2 };

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!tokenStore.getAccess()) {
      setLoading(false);
      return;
    }
    api
      .get<Me>("/auth/me")
      .then(setUser)
      .catch(() => tokenStore.clear())
      .finally(() => setLoading(false));
  }, []);

  async function login(email: string, password: string) {
    const data = await api.post<{ access_token: string; refresh_token: string }>("/auth/login", {
      email,
      password,
    });
    tokenStore.set(data.access_token, data.refresh_token);
    const me = await api.get<Me>("/auth/me");
    setUser(me);
  }

  function logout() {
    tokenStore.clear();
    setUser(null);
  }

  function hasRole(minimum: UserRole): boolean {
    if (!user) return false;
    return ROLE_RANK[user.role] >= ROLE_RANK[minimum];
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, hasRole }}>{children}</AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
