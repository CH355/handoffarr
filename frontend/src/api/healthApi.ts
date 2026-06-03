import { request } from "./client";

/* Health probe shapes per app/main.py debug endpoints. Each probe describes
   a live integration check; `ok` is the current reachability bit, `error` is
   the last error string. Backend does NOT persist a "last successful contact"
   timestamp per integration — see Sprint 5 backend gaps list. */
export interface IntegrationProbe {
  service?: string;
  enabled?: boolean;
  url?: string;
  ok?: boolean;
  error?: string | null;
  warnings?: string[];
  torrent_count?: number;
  record_count?: number;
  [key: string]: unknown;
}

export function getQbitProbe(): Promise<IntegrationProbe> {
  return request<IntegrationProbe>("/api/debug/qbit");
}

export function getRadarrProbe(): Promise<IntegrationProbe> {
  return request<IntegrationProbe>("/api/debug/radarr");
}

export function getSeerrProbe(): Promise<IntegrationProbe> {
  return request<IntegrationProbe>("/api/debug/seerr");
}
