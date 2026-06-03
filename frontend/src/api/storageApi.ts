import { request } from "./client";

export interface StorageSummary {
  health: "healthy" | "warning" | "critical" | "unknown";
  free_bytes: number | null;
  total_bytes: number | null;
  used_bytes: number | null;
  retained_bytes: number;
  completed_torrent_bytes: number;
  completed_torrent_count: number;
}

export interface StorageResponse {
  summary: StorageSummary;
  retained_torrents?: unknown[];
  volumes?: unknown[];
  artifacts?: unknown[];
}

export function getStorage(): Promise<StorageResponse> {
  return request<StorageResponse>("/api/storage");
}
