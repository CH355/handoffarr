import { request } from "./client";

export interface ExecutionJob {
  execution_id: string;
  plan_id: string;
  torrent_hash: string;
  status: string;
  mode: string;
  created_at: string;
  approved_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  current_step: number;
  total_steps: number;
  current_action: string | null;
  error: string | null;
  retry_count: number;
  max_retries: number;
  rollback_available: boolean;
  audit_log: ExecutionAuditEntry[];
  timeline: ExecutionTimelineEvent[];
  results: ExecutionActionResult[];
}

export interface ExecutionAuditEntry {
  audit_id: string;
  execution_id: string;
  action_type: string;
  step_number: number;
  who: string | null;
  when: string;
  what: string;
  duration_ms: number;
  result: string;
  verification: string | null;
  error: string | null;
}

export interface ExecutionTimelineEvent {
  event_type: string;
  label: string;
  timestamp: string;
  details: Record<string, unknown> | null;
}

export interface ExecutionActionResult {
  action_type: string;
  step_number: number;
  success: boolean;
  duration_ms: number;
  output: Record<string, unknown>;
  error: string | null;
  verification_passed: boolean;
  retry_count: number;
}

export interface ExecutionStatus {
  queue_counts: Record<string, number>;
  total_jobs: number;
  average_duration_seconds: number;
  recent_jobs: ExecutionJob[];
}

export interface Pagination {
  limit: number;
  offset: number;
  total: number;
  has_more: boolean;
}

export const getExecutionEngineStatus = () =>
  request<ExecutionStatus>("/api/execution-engine/status");

export function getExecutionJobs(
  query: { status?: string; limit?: number; offset?: number } = {},
  signal?: AbortSignal,
) {
  const params = new URLSearchParams({
    limit: String(query.limit ?? 50),
    offset: String(query.offset ?? 0),
  });
  if (query.status) params.set("status", query.status);
  return request<{ jobs: ExecutionJob[]; pagination: Pagination }>(
    `/api/execution-engine/jobs?${params}`,
    signal ? { signal } : undefined,
  );
}

export const getExecutionJob = (id: string) =>
  request<ExecutionJob>(`/api/execution-engine/jobs/${encodeURIComponent(id)}`);

export const getExecutionJobTimeline = (id: string) =>
  request<{ execution_id: string; timeline: ExecutionTimelineEvent[] }>(
    `/api/execution-engine/jobs/${encodeURIComponent(id)}/timeline`,
  );

export function submitExecutionJob(planId: string, torrentHash: string) {
  return request<{ job: ExecutionJob }>("/api/execution-engine/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ plan_id: planId, torrent_hash: torrentHash }),
  });
}

export const approveExecutionJob = (id: string) =>
  request<{ job: ExecutionJob }>(
    `/api/execution-engine/jobs/${encodeURIComponent(id)}/approve`,
    { method: "POST" },
  );

export const cancelExecutionJob = (id: string) =>
  request<{ job: ExecutionJob }>(
    `/api/execution-engine/jobs/${encodeURIComponent(id)}/cancel`,
    { method: "POST" },
  );

export const retryExecutionJob = (id: string) =>
  request<{ job: ExecutionJob }>(
    `/api/execution-engine/jobs/${encodeURIComponent(id)}/retry`,
    { method: "POST" },
  );

export const getExecutionLocks = () =>
  request<{ locks: Array<{ torrent_hash: string; execution_id: string; acquired_at: number }> }>(
    "/api/execution-engine/locks",
  );
