import { api } from "./client";

export interface InitPaymentRequest {
  tuition_id: string;
  amount: number;
  term_no?: string;
}

export interface InitPaymentResponse {
  payment_id: string;
  status: string;
}

export async function initPayment(body: InitPaymentRequest): Promise<InitPaymentResponse> {
  return api<InitPaymentResponse>("/payment/payments/init", {
    method: "POST",
    body,
    requireAuth: true,
  });
}

