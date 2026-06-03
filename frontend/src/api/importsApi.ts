import { request } from "./client";

export interface ImportsCounts {
  success: number;
  failed: number;
  pending: number;
  total: number;
}

export interface ImportEvent {
  media_id?: string | null;
  title?: string | null;
  media_type?: string | null;
  season?: number | null;
  episode?: number | null;
  release_year?: number | null;
  import_status?: string | null;
  import_timestamp?: string | null;
  source_application?: string | null;
}

export interface ImportsResponse {
  summary: ImportsCounts;
  counts: ImportsCounts;
  recent_imports: ImportEvent[];
  failures: ImportEvent[];
  pending_imports: ImportEvent[];
}

export function listImports(): Promise<ImportsResponse> {
  return request<ImportsResponse>("/api/imports");
}
