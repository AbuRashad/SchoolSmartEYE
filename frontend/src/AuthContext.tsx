import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import {
  clearSession, hasRole, loadUser, loginRequest, saveSession, UNAUTHORIZED_EVENT,
  type AuthUser, type Role,
} from "./auth";

type AuthState = {
  user: AuthUser | null;
  sessionExpired: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  can: (minimum: Role) => boolean;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => loadUser());
  const [sessionExpired, setSessionExpired] = useState(false);

  useEffect(() => {
    const onUnauthorized = () => {
      setUser(null);
      setSessionExpired(true);
    };
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const { token, user: u } = await loginRequest(username, password);
    saveSession(token, u);
    setSessionExpired(false);
    setUser(u);
  }, []);

  const logout = useCallback(() => {
    clearSession();
    setSessionExpired(false);
    setUser(null);
  }, []);

  const value = useMemo<AuthState>(
    () => ({ user, sessionExpired, login, logout, can: (minimum) => hasRole(user, minimum) }),
    [user, sessionExpired, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
