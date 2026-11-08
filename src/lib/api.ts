const API_BASE = import.meta.env.VITE_API_URL ?? "";

const ACCESS_KEY = "terrai_access_token";
const REFRESH_KEY = "terrai_refresh_token";

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface AuthUser {
  id: number;
  email: string;
}

export interface TokenPair {
  access: string;
  refresh: string;
}

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens(tokens: TokenPair): void {
  localStorage.setItem(ACCESS_KEY, tokens.access);
  localStorage.setItem(REFRESH_KEY, tokens.refresh);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

async function refreshAccessToken(): Promise<string | null> {
  const refresh = getRefreshToken();
  if (!refresh) return null;

  const res = await fetch(`${API_BASE}/api/auth/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });

  if (!res.ok) {
    clearTokens();
    return null;
  }

  const data = (await res.json()) as { access: string };
  localStorage.setItem(ACCESS_KEY, data.access);
  return data.access;
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  retry = true,
): Promise<T> {
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  const token = getAccessToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401 && retry) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      headers.set("Authorization", `Bearer ${newToken}`);
      const retryRes = await fetch(`${API_BASE}${path}`, { ...options, headers });
      if (!retryRes.ok) {
        const err = await retryRes.text().catch(() => retryRes.statusText);
        throw new Error(err || `Request failed (${retryRes.status})`);
      }
      if (retryRes.status === 204) return undefined as T;
      return retryRes.json() as Promise<T>;
    }
  }

  if (!res.ok) {
    const err = await res.text().catch(() => res.statusText);
    throw new Error(err || `Request failed (${res.status})`);
  }

  if (res.status === 204) return undefined as T;

  const contentType = res.headers.get("Content-Type") ?? "";
  if (contentType.includes("application/json")) {
    return res.json() as Promise<T>;
  }

  return res as unknown as T;
}

export async function apiFetchBlob(path: string, options: RequestInit = {}): Promise<Blob> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");

  const token = getAccessToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.text().catch(() => res.statusText);
    throw new Error(err || `Request failed (${res.status})`);
  }
  return res.blob();
}

export async function login(email: string, password: string): Promise<TokenPair> {
  const res = await fetch(`${API_BASE}/api/auth/login/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.text().catch(() => res.statusText);
    throw new Error(err || "Login failed");
  }
  const tokens = (await res.json()) as TokenPair;
  setTokens(tokens);
  return tokens;
}

export async function register(
  email: string,
  password: string,
  fullName: string,
): Promise<AuthUser> {
  const res = await fetch(`${API_BASE}/api/auth/register/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, full_name: fullName }),
  });
  if (!res.ok) {
    const err = await res.text().catch(() => res.statusText);
    throw new Error(err || "Registration failed");
  }
  return res.json() as Promise<AuthUser>;
}

export async function fetchCurrentUser(): Promise<AuthUser> {
  const profile = await apiFetch<{
    id: number;
    email: string;
  }>("/api/auth/profile/me/");
  return { id: profile.id, email: profile.email };
}

export function unwrapList<T>(data: Paginated<T> | T[]): T[] {
  return Array.isArray(data) ? data : data.results;
}
