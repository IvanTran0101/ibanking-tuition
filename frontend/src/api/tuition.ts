import { api } from "./client";

export interface TuitionResponse {
  ok: boolean;
  tuition_id: string;
  student_id: string;
  full_name: string;
  term_no: number;
  amount_due: number;
  status: string;
}

export async function getTuitionByStudentId(studentId: string): Promise<TuitionResponse> {
  return api<TuitionResponse>(`/tuition/tuition/${encodeURIComponent(studentId)}`, { method: "GET", requireAuth: true });
}
