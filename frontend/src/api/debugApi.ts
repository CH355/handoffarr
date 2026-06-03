import { request } from "./client";

/* /api/debug/states returns a qBittorrent state rollup. Used on Home for
   the Stat Tile activity context (R-B1: tile-level rollup remains a backend
   gap; the page degrades gracefully if the probe is unreachable). */
export interface DebugStatesResponse {
  ok?: boolean;
  error?: string;
  states?: Record<string, number>;
  total?: number;
}

export function getStates(): Promise<DebugStatesResponse> {
  return request<DebugStatesResponse>("/api/debug/states");
}
