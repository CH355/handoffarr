import { request } from "./client";

/* Cleanup API per frontend-implementation-spec-v1.md §7.2.
   Only existing endpoints in app/main.py are exposed here. */

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

/* --- Review ---------------------------------------------------------- */

export type ReviewClass =
  | "Safe Review Candidate"
  | "Risky Review Candidate"
  | "Missing Library Candidate"
  | "Unknown Evidence Candidate"
  | "Already Cleaned";

export type MatchStrength =
  | "Exact Hash/DownloadId Match"
  | "Exact Library Path Match"
  | "Filename + Size Match"
  | "Multi-file Pack Partial Match"
  | "Title Only Match"
  | "No Match";

export interface CleanupReviewItem {
  cleanup_id?: string | null;
  media_id?: string | null;
  media_type?: string | null;
  media_title?: string | null;
  source_application?: string | null;
  torrent_hash?: string | null;
  qbit_hash?: string | null;
  review_class?: ReviewClass | string | null;
  reason?: string | null;
  risk_reasons?: string[];
  safe_reasons?: string[];
  match_strength?: MatchStrength | string | null;
  confidence_score?: number | null;
  evidence_strength?: "Strong" | "Moderate" | "Partial" | "Weak" | "Unknown" | string | null;
  recoverable_bytes?: number | null;
  retained_bytes?: number | null;
  retained_total_bytes?: number | null;
  retained_file_count?: number | null;
  retained_video_file_count?: number | null;
  matched_retained_files?: Array<{
    name?: string | null;
    size?: number | null;
    retained_path?: string | null;
    match_method?: string | null;
  }>;
  library_file_exists?: boolean | null;
  library_file_size?: number | null;
  cleanup_status?: string | null;
  library_status?: string | null;
  import_status?: string | null;
  torrent_state?: string | null;
  paths?: {
    import_source_path?: string | null;
    expected_library_path?: string | null;
    library_path?: string | null;
    download_path?: string | null;
    content_path?: string | null;
  };
  checks?: Record<string, unknown>;
  evidence?: Record<string, unknown>;
}

export interface CleanupReviewSummary {
  total: number;
  recoverable_bytes: number;
  safe_recoverable_bytes: number;
  deduped_excluded_count: number;
  safe_candidate_count: number;
  risky_candidate_count: number;
  missing_library_count: number;
  unknown_evidence_count: number;
  already_cleaned_count: number;
  by_review_class: Record<string, number>;
  by_match_strength: Record<string, number>;
}

export interface CleanupReviewResponse {
  summary: CleanupReviewSummary;
  filters: {
    review_class: string | null;
    match_strength: string | null;
    min_recoverable_bytes: number | null;
    source_application: string | null;
    media_type: string | null;
    limit: number;
    offset: number;
    sort: string;
  };
  pagination: {
    total: number;
    limit: number;
    offset: number;
    returned: number;
  };
  top_candidates: CleanupReviewItem[];
  candidates: CleanupReviewItem[];
}

export interface CleanupReviewFilters {
  review_class?: string | null;
  match_strength?: string | null;
  min_recoverable_bytes?: number | null;
  source_application?: string | null;
  media_type?: string | null;
  limit?: number | null;
  offset?: number | null;
  sort?: "recoverable_bytes desc" | "confidence_score desc" | "media_title asc" | null;
}

function toQuery(filters: CleanupReviewFilters): string {
  const entries: Array<[string, string]> = [];
  for (const [k, v] of Object.entries(filters)) {
    if (v === undefined || v === null || v === "") continue;
    entries.push([k, String(v)]);
  }
  if (!entries.length) return "";
  const search = new URLSearchParams(entries);
  return `?${search.toString()}`;
}

export function getCleanupReview(
  filters: CleanupReviewFilters = {},
): Promise<CleanupReviewResponse> {
  return request<CleanupReviewResponse>(
    `/api/cleanup/review${toQuery(filters)}`,
  );
}

export interface CleanupReviewMediaPacket extends CleanupReviewItem {
  candidates?: CleanupReviewItem[];
  manual_checklist_text?: string;
  reason?: string | null;
}

export function getCleanupReviewMedia(mediaId: string): Promise<CleanupReviewMediaPacket> {
  return request<CleanupReviewMediaPacket>(
    `/api/cleanup/review/${encodeURIComponent(mediaId)}`,
  );
}

export async function getCleanupReviewChecklist(mediaId: string): Promise<string> {
  const res = await fetch(`/api/cleanup/review/${encodeURIComponent(mediaId)}/checklist`, {
    headers: { Accept: "text/plain" },
  });
  if (!res.ok) throw new Error(`Checklist request failed (${res.status})`);
  return res.text();
}

/* --- Action plan ----------------------------------------------------- */

export interface CleanupActionPlanCandidate {
  media_id?: string | null;
  media_title?: string | null;
  media_type?: string | null;
  review_class?: string | null;
  match_strength?: string | null;
  confidence_score?: number | null;
  recoverable_bytes?: number | null;
  qbit_name?: string | null;
  qbit_hash?: string | null;
  torrent_hash?: string | null;
  retained_save_path?: string | null;
  library_path?: string | null;
  checklist_url?: string | null;
  manual_action?: string | null;
  reasons?: string[];
}

export interface CleanupActionPlanResponse {
  summary: {
    total_candidates: number;
    included_candidates: number;
    total_recoverable_bytes: number;
    included_recoverable_bytes: number;
    filters_applied: Record<string, unknown>;
    warning_read_only: string;
  };
  candidates: CleanupActionPlanCandidate[];
}

export function getCleanupActionPlan(
  filters: CleanupReviewFilters = {},
): Promise<CleanupActionPlanResponse> {
  return request<CleanupActionPlanResponse>(
    `/api/cleanup/action-plan${toQuery(filters)}`,
  );
}

/* --- Executions ------------------------------------------------------ */

export interface CleanupExecutionRow {
  execution_id: string;
  batch_id?: string | null;
  media_id?: string | null;
  media_title?: string | null;
  qbit_hash?: string | null;
  review_class?: string | null;
  match_strength?: string | null;
  requested_action?: string | null;
  execution_status?: string | null;
  recoverable_bytes?: number | null;
  confirmation_phrase?: string | null;
  blocking_reasons?: string[];
  created_at?: string | null;
  completed_at?: string | null;
  evidence?: Record<string, unknown>;
}

export interface CleanupExecutionBatchRow {
  batch_id: string;
  status?: string | null;
  item_count?: number | null;
  completed_count?: number | null;
  failed_count?: number | null;
  planned_recoverable_bytes?: number | null;
  actual_recovered_bytes?: number | null;
  created_at?: string | null;
  completed_at?: string | null;
  evidence?: Record<string, unknown>;
}

export interface CleanupExecutionsResponse {
  config: Record<string, unknown>;
  executions: CleanupExecutionRow[];
  batches: CleanupExecutionBatchRow[];
}

export function getCleanupExecutions(limit = 100): Promise<CleanupExecutionsResponse> {
  return request<CleanupExecutionsResponse>(`/api/cleanup/executions?limit=${limit}`);
}

/* --- Dry-run / execute ----------------------------------------------- */

export interface CleanupExecutePayload {
  media_id: string;
  qbit_hash: string;
  confirmation: string;
}

export interface CleanupExecuteResult {
  execution_id: string;
  execution_status: string;
  precheck_evidence?: Record<string, unknown>;
  qbittorrent_api_result?: unknown;
  postcheck_evidence?: Record<string, unknown>;
  qbittorrent_item_disappeared?: boolean;
  library_file_still_exists?: boolean | null;
  estimated_recoverable_bytes?: number | null;
  actual_verification_status?: string;
}

export function postCleanupExecuteDryRun(
  payload: CleanupExecutePayload,
): Promise<CleanupExecuteResult> {
  return request<CleanupExecuteResult>("/api/cleanup/execute/dry-run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function postCleanupExecute(
  payload: CleanupExecutePayload,
): Promise<CleanupExecuteResult> {
  return request<CleanupExecuteResult>("/api/cleanup/execute", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export interface CleanupBatchItem {
  media_id: string;
  qbit_hash: string;
}

export interface CleanupBatchDryRunPayload {
  items: CleanupBatchItem[];
  confirmation: string;
}

export interface CleanupBatchDryRunPerItem {
  media_id: string;
  media_title?: string | null;
  qbit_hash: string;
  review_class?: string | null;
  match_strength?: string | null;
  recoverable_bytes?: number | null;
  allowed: boolean;
  reasons?: string[];
  blocking_reasons?: string[];
}

export interface CleanupBatchDryRunResult {
  allowed: boolean;
  plan_id: string | null;
  item_count: number;
  total_recoverable_bytes: number;
  per_item: CleanupBatchDryRunPerItem[];
  blocking_reasons: string[];
  warning: string;
}

export function postCleanupBatchDryRun(
  payload: CleanupBatchDryRunPayload,
): Promise<CleanupBatchDryRunResult> {
  return request<CleanupBatchDryRunResult>("/api/cleanup/execute/batch-dry-run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export interface CleanupBatchExecutePayload {
  plan_id: string;
  confirmation: string;
}

export interface CleanupBatchExecuteResult {
  batch_id?: string;
  batch_status?: string;
  status?: string;
  item_count?: number;
  completed_count?: number;
  failed_count?: number;
  planned_recoverable_bytes?: number;
  actual_recovered_bytes?: number;
  total_recovered_bytes?: number;
  per_item?: Array<Record<string, unknown>>;
  blocking_reasons?: string[];
  [key: string]: unknown;
}

export function postCleanupBatchExecute(
  payload: CleanupBatchExecutePayload,
): Promise<CleanupBatchExecuteResult> {
  return request<CleanupBatchExecuteResult>("/api/cleanup/execute/batch", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

/* --- Confirmation phrase helpers (mirror app/cleanup_execution.py) --- */

export const CONFIRMATION = {
  dryRun: (mediaId: string) => `DRY RUN CLEANUP ${mediaId}`,
  execute: (mediaId: string) => `DELETE SAFE CANDIDATE ${mediaId}`,
  batchDryRun: "DRY RUN BATCH CLEANUP",
  batchExecute: "EXECUTE BATCH CLEANUP",
} as const;
