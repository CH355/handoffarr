import { request } from "./client";

export type RecoveryStatus =
  | "dead"
  | "downloading"
  | "stalled"
  | "queued"
  | "healthy";

export interface ReplacementCandidate {
  release_name: string;
  quality: string | null;
  indexer: string | null;
  seeders: number;
  peers: number;
  age_days: number | null;
  size: number;
  protocol: string | null;
  custom_format_score: number;
  rejected: boolean;
  rejection_reason: string | null;
  score: number;
  recommended: boolean;
}

export interface RecoveryEvaluation {
  torrent_hash: string;
  provider: "radarr" | "sonarr";
  media_id: number;
  media_title: string | null;
  candidates: ReplacementCandidate[];
  recommended_candidate: ReplacementCandidate | null;
  recommendation_reasons: string[];
  recommendation_explanation: string;
  evaluated_at: string;
  cached: boolean;
}

export interface Torrent {
  hash: string;
  name?: string | null;
  state?: string | null;
  progress?: number | null;
  availability?: number | null;
  num_seeds?: number | null;
  num_leechs?: number | null;
  size?: number | null;
  total_size?: number | null;
  dlspeed?: number | null;
  dead_torrent: boolean;
  dead_reason: string;
  dead_since?: string | null;
  observed_at?: string;
  media_title: string;
  media_type: string;
  current_release: string;
  availability_percent: number | null;
  seeders: number;
  peers: number;
  recovery_status: RecoveryStatus;
  recommendation: "Recover" | "Replace soon" | "Monitor" | null;
  recommendation_reason: string;
  replacement_candidates: ReplacementCandidate[];
  best_replacement: string | null;
  replacement_health_score: number | null;
  replacement_recommendation: string | null;
  replacement_recommendation_reasons: string[];
  alternatives_evaluated_at: string | null;
  agent_evaluated_at: string | null;
  agent_confidence: number | null;
  agent_recommendation: string | null;
  agent_reasoning: string[];
}

export interface TorrentSummary {
  total_torrents: number;
  dead_torrents: number;
  stalled_torrents: number;
  downloading_torrents: number;
  queued_torrents: number;
  healthy_torrents: number;
  potentially_recoverable: number;
  dead_torrents_size: number;
  dead_torrents_today: number;
}

export interface TorrentHealth {
  name: string;
  count: number;
  message: string;
  description: string;
  severity: "healthy" | "warning" | "critical";
}

export interface TorrentsResponse extends TorrentSummary {
  summary: TorrentSummary;
  health: TorrentHealth;
  torrents: Torrent[];
}

export type TorrentDetail = Torrent;

export function listTorrents(): Promise<TorrentsResponse> {
  return request<TorrentsResponse>("/api/torrents");
}

export function getTorrent(hash: string): Promise<TorrentDetail> {
  return request<TorrentDetail>(`/api/torrents/${encodeURIComponent(hash)}`);
}

export function evaluateTorrentAlternatives(
  hash: string,
  force = false,
): Promise<RecoveryEvaluation> {
  return request<RecoveryEvaluation>(
    `/api/torrents/${encodeURIComponent(hash)}/alternatives`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ force }),
    },
  );
}

export function removeSelectedTorrents(
  hashes: string[],
  deleteFiles: boolean,
): Promise<{
  ok: boolean;
  removed: number;
  hashes: string[];
  delete_files: boolean;
}> {
  return request("/api/torrents/remove-dead", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ hashes, delete_files: deleteFiles }),
  });
}
