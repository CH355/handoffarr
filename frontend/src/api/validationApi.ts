import { request } from "./client";

export type ValidationStatus = "OK" | "WARN" | "FAIL";

export interface ValidationCheck {
  name?: string;
  status: ValidationStatus;
  message?: string;
  reason?: string;
  evidence?: Record<string, unknown>;
}

export interface ValidationResponse {
  status: ValidationStatus;
  checks: ValidationCheck[];
}

export function getValidation(): Promise<ValidationResponse> {
  return request<ValidationResponse>("/api/validation");
}
