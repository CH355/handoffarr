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
