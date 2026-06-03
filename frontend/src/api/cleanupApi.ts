import { request } from "./client";

export interface CleanupSummary {
  completed: number;
  pending: number;
  failed: number;
  intentional: number;
  unknown: number;
  total: number;
  total_recoverable_bytes: number;
}

export interface CleanupCandidate {
  media_id?: string | null;
  title?: string | null;
  recoverable_bytes?: number | null;
  retained_bytes?: number | null;
  cleanup_status?: string | null;
  cleanup_timestamp?: string | null;
}

export interface CleanupResponse {
  summary: CleanupSummary;
  completed: CleanupCandidate[];
  pending: CleanupCandidate[];
  failed: CleanupCandidate[];
  intentional: CleanupCandidate[];
  unknown: CleanupCandidate[];
  top_cleanup_candidates: CleanupCandidate[];
}

export function getCleanupSummary(): Promise<CleanupResponse> {
  return request<CleanupResponse>("/api/cleanup");
}
