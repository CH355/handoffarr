import { useQuery } from "@tanstack/react-query";
import { getAppHealth } from "@/api/settingsApi";
import { getQbitProbe, getRadarrProbe, getSeerrProbe } from "@/api/healthApi";
import { getStorage } from "@/api/storageApi";
import { getCleanupExecutions } from "@/api/cleanupApi";
import { useRefreshQueryOptions } from "@/hooks/useRefreshQueryOptions";

/* Settings page server-state composition. Each query owns its own loading
   and error state so cards degrade independently (no full-page spinner). */
export function useSettingsData() {
  const light = useRefreshQueryOptions("light");
  const medium = useRefreshQueryOptions("medium");
  const heavy = useRefreshQueryOptions("heavy");
  const health = useQuery({
    queryKey: ["settings", "health"],
    queryFn: getAppHealth,
    ...light,
    retry: 0,
  });
  const qbit = useQuery({
    queryKey: ["health", "qbit"],
    queryFn: getQbitProbe,
    ...heavy,
    enabled: false,
    retry: 0,
  });
  const radarr = useQuery({
    queryKey: ["health", "radarr"],
    queryFn: getRadarrProbe,
    ...heavy,
    enabled: false,
    retry: 0,
  });
  const seerr = useQuery({
    queryKey: ["health", "seerr"],
    queryFn: getSeerrProbe,
    ...heavy,
    enabled: false,
    retry: 0,
  });
  const storage = useQuery({
    queryKey: ["storage"],
    queryFn: getStorage,
    ...medium,
  });
  const executions = useQuery({
    queryKey: ["settings", "cleanup-config"],
    queryFn: () => getCleanupExecutions(1),
    ...medium,
  });
  return { health, qbit, radarr, seerr, storage, executions };
}
