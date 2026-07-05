import { request } from "./client";

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
  observed_at?: string;
}

export interface TorrentSummary {
  dead_torrents: number;
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

export interface TorrentDetail extends Torrent {
  availability_percent: number;
  seeders: number;
  peers: number;
  health: string;
  recommendation?: string | null;
}

export function listTorrents(): Promise<TorrentsResponse> {
  return request<TorrentsResponse>("/api/torrents");
}

export function getTorrent(hash: string): Promise<TorrentDetail> {
  return request<TorrentDetail>(`/api/torrents/${encodeURIComponent(hash)}`);
}

export function removeDeadTorrents(hashes: string[]): Promise<{
  ok: boolean;
  removed: number;
  delete_files: false;
}> {
  return request("/api/torrents/remove-dead", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ hashes }),
  });
}
