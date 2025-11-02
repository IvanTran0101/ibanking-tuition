import { api } from "./client";

function setCookie(name: string, value: string, days = 7, sameSite: "Lax" | "Strict" | "None" = "Lax") {
  if (typeof document === "undefined") return;
  const expires = new Date(Date.now() + days * 864e5).toUTCString();
  const secure = location.protocol === "https:" ? "; Secure" : "";
  document.cookie = `${name}=${encodeURIComponent(value)}; Expires=${expires}; Path=/; SameSite=${sameSite}${secure}`;
}

function deleteCookie(name: string) {
  if (typeof document === "undefined") return;
  document.cookie = `${name}=; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=/; SameSite=Lax`;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
}

export async function login(req: LoginRequest): Promise<LoginResponse> {
  // Explicit endpoint: /auth/authentication/login
  const data = await api<LoginResponse>("/auth/authentication/login", {
    method: "POST",
    body: req,
    requireAuth: false,
  });
  // Store token in cookie only
  setCookie("access_token", data.access_token, 7, "Lax");
  return data;
}

export function logout(): void {
  deleteCookie("access_token");
}

export function getToken(): string | null {
  // Read token from cookie
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|; )access_token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}
