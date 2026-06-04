import { useQuery } from "@tanstack/react-query";
import { getAppHealth } from "@/api/settingsApi";
import { getQbitProbe, getRadarrProbe, getSeerrProbe } from "@/api/healthApi";
import { getStorage } from "@/api/storageApi";
import { getCleanupExecutions } from "@/api/cleanupApi";

/* Settings page server-state composition. Each query owns its own loading
   and error state so cards degrade independently (no full-page spinner). */
export function useSettingsData() {
  const health = useQuery({
    queryKey: ["settings", "health"],
    queryFn: getAppHealth,
    staleTime: 30_000,
    retry: 0,
  });
  const qbit = useQuery({
    queryKey: ["health", "qbit"],
    queryFn: getQbitProbe,
    staleTime: 30_000,
    retry: 0,
  });
  const radarr = useQuery({
    queryKey: ["health", "radarr"],
    queryFn: getRadarrProbe,
    staleTime: 30_000,
    retry: 0,
  });
  const seerr = useQuery({
    queryKey: ["health", "seerr"],
    queryFn: getSeerrProbe,
    staleTime: 30_000,
    retry: 0,
  });
  const storage = useQuery({
    queryKey: ["storage"],
    queryFn: getStorage,
    staleTime: 60_000,
  });
  const executions = useQuery({
    queryKey: ["cleanup", "executions"],
    queryFn: () => getCleanupExecutions(500),
    staleTime: 15_000,
  });
  return { health, qbit, radarr, seerr, storage, executions };
}
