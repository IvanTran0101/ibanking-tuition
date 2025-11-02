// Lightweight fetch-based API client wired to Gateway

// In Vite, use import.meta.env; avoid process.env to prevent TS/node type issues
const API_BASE = (import.meta as any)?.env?.VITE_API_URL || "http://localhost:8000";

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export interface RequestOptions {
  method?: HttpMethod;
  headers?: Record<string, string>;
  query?: Record<string, string | number | boolean | undefined>;
  body?: any;
  requireAuth?: boolean;
}

function buildUrl(path: string, query?: RequestOptions["query"]): string {
  const url = new URL(path.replace(/^[\/]+/, "/"), API_BASE);
  if (query) {
    Object.entries(query).forEach(([k, v]) => {
      if (v !== undefined && v !== null) url.searchParams.set(k, String(v));
    });
  }
  return url.toString();
}

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp("(?:^|; )" + name.replace(/[.$?*|{}()\[\]\\/+^]/g, "\\$&") + "=([^;]*)"));
  return match ? decodeURIComponent(match[1]) : null;
}

function authHeader(requireAuth?: boolean): Record<string, string> {
  if (!requireAuth) return {};
  const token = getCookie("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function api<T = any>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = "GET", headers, query, body, requireAuth = true } = opts;
  const url = buildUrl(path, query);
  const h: Record<string, string> = {
    "Content-Type": "application/json",
    ...authHeader(requireAuth),
    ...(headers || {}),
  };
  const resp = await fetch(url, {
    method,
    headers: h,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!resp.ok) {
    let detail: any = undefined;
    try {
      detail = await resp.json();
    } catch {}
    throw new Error(`HTTP ${resp.status}: ${resp.statusText}${detail ? ` - ${JSON.stringify(detail)}` : ""}`);
  }
  const ct = resp.headers.get("content-type") || "";
  if (ct.includes("application/json")) return (await resp.json()) as T;
  return (await resp.text()) as unknown as T;
}

export const apiBase = API_BASE;
