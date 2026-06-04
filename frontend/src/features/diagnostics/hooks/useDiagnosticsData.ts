import { useQuery } from "@tanstack/react-query";
import { getCleanupExecutions } from "@/api/cleanupApi";
import { getStates } from "@/api/debugApi";
import { getQbitProbe, getRadarrProbe, getSeerrProbe } from "@/api/healthApi";
import { listImports } from "@/api/importsApi";
import { getStorage } from "@/api/storageApi";
import { getTimeline } from "@/api/timelineApi";
import { getValidation } from "@/api/validationApi";

export function useDiagnosticsData() {
  const query = <T,>(key: string, fn: () => Promise<T>, staleTime = 30_000) =>
    useQuery({ queryKey: ["diagnostics", key], queryFn: fn, staleTime, retry: 0 });

  return {
    validation: query("validation", getValidation),
    states: query("states", getStates),
    qbit: query("qbit", getQbitProbe),
    radarr: query("radarr", getRadarrProbe),
    seerr: query("seerr", getSeerrProbe),
    storage: query("storage", getStorage, 60_000),
    imports: query("imports", listImports, 60_000),
    executions: query("executions", () => getCleanupExecutions(20)),
    timeline: query("timeline", getTimeline),
  };
}
