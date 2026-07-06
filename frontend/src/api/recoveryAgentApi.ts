import { request } from "./client";

export interface RecoveryAgentStatus {
  enabled: boolean;
  interval_minutes: number;
  agent_status: "Running" | "Idle";
  last_evaluation_at: string | null;
  next_evaluation_at: string | null;
  jobs_evaluated: number;
  dead_torrents: number;
  plans_generated: number;
  average_confidence: number;
  evaluation_duration_ms: number;
  queue_counts: Record<"queued" | "running" | "completed" | "failed" | "cancelled", number>;
  recent_plans: RecoveryPlan[];
  recent_decisions: RecoveryHistoryEntry[];
  recent_errors: RecoveryJob[];
}

export interface TimelineEvent {
  type: string;
  label: string;
  timestamp: string;
  details?: Record<string, unknown>;
}

export interface RecoveryPlan {
  id: string; torrent_hash: string; media_id: string | null; media_title: string | null;
  media_type: string | null; current_release: string | null; created_at: string;
  status: string; current_health: Record<string, unknown>; recommendation: string;
  confidence: number; reasoning: string[]; replacement_candidates: Array<Record<string, unknown>>;
  planned_action: string; evaluation_duration_ms: number; signals: Record<string, unknown>;
  policy_matches: Array<{ policy: string; matched: boolean; reason: string }>;
  confidence_breakdown: Array<{ signal: string; weight: number; contribution: number }>;
  timeline: TimelineEvent[];
}

export interface RecoveryHistoryEntry {
  history_id: string; timestamp: string; torrent_hash: string;
  health: Record<string, unknown>; recommendation: string; confidence: number;
  selected_candidate: Record<string, unknown> | null; evaluation_duration_ms: number;
  candidate_count: number; decision: string; plan_id: string;
  media_title?: string | null; media_type?: string | null; plan_status?: string | null;
}

export interface RecoveryJob {
  job_id: string; torrent_hash: string; status: string; created_at: string;
  started_at: string | null; completed_at: string | null; error: string | null;
}
export interface Pagination {
  limit: number; offset: number; total: number; has_more: boolean;
}

export const getRecoveryAgentStatus = () =>
  request<RecoveryAgentStatus>("/api/recovery-agent/status");

export function updateRecoveryAgentSettings(enabled: boolean, interval: number) {
  return request<RecoveryAgentStatus>("/api/recovery-agent/settings", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled, interval_minutes: interval }),
  });
}

export interface PlanQuery {
  limit?: number; offset?: number; search?: string;
  recommendation?: string; sort?: string;
}
export function getRecoveryPlans(query: PlanQuery = {}, signal?: AbortSignal) {
  const params = new URLSearchParams({
    limit: String(query.limit ?? 50), offset: String(query.offset ?? 0),
  });
  if (query.search) params.set("search", query.search);
  if (query.recommendation) params.set("recommendation", query.recommendation);
  if (query.sort) params.set("sort", query.sort);
  return request<{ plans: RecoveryPlan[]; pagination: Pagination }>(
    `/api/recovery-agent/plans?${params}`, signal ? { signal } : undefined,
  );
}
export const getRecoveryPlan = (id: string) =>
  request<RecoveryPlan>(`/api/recovery-agent/plans/${encodeURIComponent(id)}`);
export const getPlanComparison = (id: string) =>
  request<{ previous: RecoveryPlan | null; current: RecoveryPlan; changes: Record<string, { previous: unknown; current: unknown }> }>(
    `/api/recovery-agent/plans/${encodeURIComponent(id)}/comparison`,
  );
export interface HistoryQuery {
  limit?: number; offset?: number; search?: string; media_type?: string;
  recommendation?: string; min_confidence?: string; health?: string;
  date?: string; status?: string;
}
export function getRecoveryHistory(query: HistoryQuery = {}, signal?: AbortSignal) {
  const params = new URLSearchParams({
    limit: String(query.limit ?? 50), offset: String(query.offset ?? 0),
  });
  Object.entries(query).forEach(([key, value]) => {
    if (value != null && value !== "" && key !== "limit" && key !== "offset")
      params.set(key, String(value));
  });
  return request<{ history: RecoveryHistoryEntry[]; pagination: Pagination }>(
    `/api/recovery-agent/history?${params}`, signal ? { signal } : undefined,
  );
}
export function getRecoveryQueue(query: { limit?: number; offset?: number; status?: string } = {}, signal?: AbortSignal) {
  const params = new URLSearchParams({
    limit: String(query.limit ?? 50), offset: String(query.offset ?? 0),
  });
  if (query.status) params.set("status", query.status);
  return request<{ jobs: RecoveryJob[]; pagination: Pagination }>(
    `/api/recovery-agent/queue?${params}`, signal ? { signal } : undefined,
  );
}
