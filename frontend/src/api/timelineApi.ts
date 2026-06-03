import { request } from "./client";

/* Timeline API per frontend-implementation-spec-v1.md §7.2.
   Backed by app/main.py GET /api/timeline/{media_id}. */

export interface TimelineStage {
  stage?: string | null;
  stage_status?: string | null;
  source?: string | null;
  timestamp?: string | null;
  evidence?: Record<string, unknown>;
}

export interface MediaTimeline {
  timeline_id?: string;
  media_id?: string | null;
  media_title?: string | null;
  stages: TimelineStage[];
  blocked_at?: string | null;
  responsible_domain?: string | null;
  recommendation?: string | null;
  outcome?: string | null;
  latest_timestamp?: string | null;
}

export interface MediaTimelineResponse {
  media_id: string;
  timeline: MediaTimeline | null;
  stages: TimelineStage[];
  blocked_at: string | null;
  outcome: string | null;
}

export function getMediaTimeline(mediaId: string): Promise<MediaTimelineResponse> {
  return request<MediaTimelineResponse>(
    `/api/timeline/${encodeURIComponent(mediaId)}`,
  );
}

export interface MediaImportEvent {
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

export interface MediaImportResponse {
  media_id: string;
  import_status: string | null;
  history: MediaImportEvent[];
  evidence: Record<string, unknown>;
}

export function getMediaImports(mediaId: string): Promise<MediaImportResponse> {
  return request<MediaImportResponse>(
    `/api/imports/${encodeURIComponent(mediaId)}`,
  );
}
