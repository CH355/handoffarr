import { request } from "./client";

/* Settings API surface.

   Settings is read-only: there is no backend endpoint that accepts
   configuration writes. We compose the page out of existing read endpoints
   already exposed by app/main.py:

     - GET /api/health             — config presence
     - GET /api/cleanup/executions — cleanup_execution.* gates (config sub-doc)
     - GET /api/storage            — runtime thresholds (warning/critical/etc)
     - GET /api/debug/{qbit,radarr,seerr} — integration probes (reused)

   No write endpoints exist, so no mutation calls live here. */

export interface AppHealth {
  status: string;
  config_present: boolean;
}

export function getAppHealth(): Promise<AppHealth> {
  return request<AppHealth>("/api/health");
}
