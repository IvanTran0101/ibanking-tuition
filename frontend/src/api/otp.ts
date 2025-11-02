import { api } from "./client";

export interface VerifyOtpRequest {
  payment_id: string;
  otp_code: string;
}

export async function verifyOtp(body: VerifyOtpRequest): Promise<{ ok: boolean }>{
  return api("/otp/otp/verify", {
    method: "POST",
    body,
    requireAuth: true,
  });
}

