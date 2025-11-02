import { api } from "./client";

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
  localStorage.setItem("access_token", data.access_token);
  return data;
}

export function logout(): void {
  localStorage.removeItem("access_token");
}

export function getToken(): string | null {
  return localStorage.getItem("access_token");
}
