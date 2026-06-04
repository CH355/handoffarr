import { useQuery } from "@tanstack/react-query";
import { getCleanupExecutions } from "@/api/cleanupApi";
import { getStates } from "@/api/debugApi";
import { getQbitProbe, getRadarrProbe, getSeerrProbe } from "@/api/healthApi";
import { listImports } from "@/api/importsApi";
import { getStorage } from "@/api/storageApi";
import { getTimeline } from "@/api/timelineApi";
import { getValidation } from "@/api/validationApi";

export function useDiagnosticsData() {
  const query = <T,>(key: readonly string[], fn: () => Promise<T>, staleTime = 30_000) =>
    useQuery({ queryKey: key, queryFn: fn, staleTime, retry: 0 });

  return {
    validation: query(["validation"], getValidation),
    states: query(["debug", "states"], getStates),
    qbit: query(["health", "qbit"], getQbitProbe),
    radarr: query(["health", "radarr"], getRadarrProbe),
    seerr: query(["health", "seerr"], getSeerrProbe),
    storage: query(["storage"], getStorage, 60_000),
    imports: query(["imports"], listImports, 60_000),
    executions: query(["cleanup", "executions"], () => getCleanupExecutions(500), 15_000),
    timeline: query(["timeline"], getTimeline),
  };
}
