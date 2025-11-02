import { api } from "./client";

export interface AccountMeResponse {
  ok: boolean;
  user_id: string;
  full_name: string;
  phone_number: string;
  balance: number;
  username: string;
  email: string;
}

export async function getAccountMe(): Promise<AccountMeResponse> {
  return api<AccountMeResponse>("/account/accounts/me", { method: "GET", requireAuth: true });
}

