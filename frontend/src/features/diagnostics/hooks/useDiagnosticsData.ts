import { useQuery } from "@tanstack/react-query";
import { getCleanupExecutions } from "@/api/cleanupApi";
import { getStates } from "@/api/debugApi";
import { getQbitProbe, getRadarrProbe, getSeerrProbe } from "@/api/healthApi";
import { listImports } from "@/api/importsApi";
import { getStorage } from "@/api/storageApi";
import { getTimeline } from "@/api/timelineApi";
import { getValidation } from "@/api/validationApi";
import { getEvents, getTraces } from "@/api/operationsApi";
import { useRefreshQueryOptions } from "@/hooks/useRefreshQueryOptions";

export interface DiagnosticsLoadState {
  collectors: boolean;
  states: boolean;
  timeline: boolean;
  events: boolean;
  traces: boolean;
}

export function useDiagnosticsData(load: DiagnosticsLoadState) {
  const light = useRefreshQueryOptions("light");
  const medium = useRefreshQueryOptions("medium");
  const heavy = useRefreshQueryOptions("heavy");
  const query = <T,>(key: readonly string[], fn: () => Promise<T>, options: object) =>
    useQuery({ queryKey: key, queryFn: fn, retry: 0, ...options });

  return {
    validation: query(["validation"], getValidation, light),
    states: query(["debug", "states"], getStates, { ...heavy, enabled: load.states }),
    qbit: query(["health", "qbit"], getQbitProbe, { ...heavy, enabled: load.collectors }),
    radarr: query(["health", "radarr"], getRadarrProbe, { ...heavy, enabled: load.collectors }),
    seerr: query(["health", "seerr"], getSeerrProbe, { ...heavy, enabled: load.collectors }),
    storage: query(["storage"], getStorage, { ...medium, enabled: load.collectors }),
    imports: query(["imports"], listImports, { ...medium, enabled: load.collectors }),
    executions: query(["diagnostics", "executions"], () => getCleanupExecutions(20), medium),
    timeline: query(["timeline"], getTimeline, { ...heavy, enabled: load.timeline }),
    events: query(["events"], getEvents, { ...heavy, enabled: load.events }),
    traces: query(["traces"], getTraces, { ...heavy, enabled: load.traces }),
  };
}
