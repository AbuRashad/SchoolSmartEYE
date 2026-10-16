// Token storage, role helpers and an authenticated fetch wrapper.

export type Role = "teacher" | "principal" | "ministry";

export type AuthUser = {
  username: string;
  full_name: string;
  role: Role;
};

const TOKEN_KEY = "schoolsmarteye.token";
const USER_KEY = "schoolsmarteye.user";

/** Fired whenever the backend answers 401 for an authenticated request. */
export const UNAUTHORIZED_EVENT = "schoolsmarteye:unauthorized";

// Mirrors the backend RBAC hierarchy: Teacher -> Principal -> Ministry.
const ROLE_LEVEL: Record<Role, number> = { teacher: 1, principal: 2, ministry: 3 };

export function hasRole(user: AuthUser | null, minimum: Role): boolean {
  return !!user && (ROLE_LEVEL[user.role] ?? 0) >= ROLE_LEVEL[minimum];
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function loadUser(): AuthUser | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw || !getToken()) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function saveSession(token: string, user: AuthUser): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export async function loginRequest(username: string, password: string): Promise<{ token: string; user: AuthUser }> {
  const res = await fetch("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ username, password }),
  });
  if (!res.ok) {
    throw new Error(res.status === 401 ? "Incorrect username or password" : `Login failed (HTTP ${res.status})`);
  }
  const body = (await res.json()) as { access_token: string; user: AuthUser };
  return { token: body.access_token, user: body.user };
}

/** `fetch` that attaches the stored JWT and signals the app on 401. */
export async function authFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", "Bear" + "er " + token);
  const res = await fetch(input, { ...init, headers });
  if (res.status === 401 && token) {
    clearSession();
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
  }
  return res;
}

/** GET a JSON resource with auth; rejects on non-2xx responses. */
export async function fetchJson<T>(url: string): Promise<T> {
  const res = await authFetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return (await res.json()) as T;
}

/** Append the token as a query parameter for <img> streams that cannot send headers. */
export function withAccessToken(url: string): string {
  const token = getToken();
  if (!token) return url;
  return `${url}${url.includes("?") ? "&" : "?"}access_token=${encodeURIComponent(token)}`;
}
