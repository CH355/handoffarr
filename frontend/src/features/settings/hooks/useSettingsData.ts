import { useQuery } from "@tanstack/react-query";
import { getAppHealth, getSettings } from "@/api/settingsApi";
import { getQbitProbe, getRadarrProbe, getSeerrProbe } from "@/api/healthApi";

/* Settings page server-state composition. Each query owns its own loading
   and error state so cards degrade independently (no full-page spinner). */
export function useSettingsData() {
  const health = useQuery({
    queryKey: ["settings", "health"],
    queryFn: getAppHealth,
    staleTime: 30_000,
    retry: 0,
  });
  const settings = useQuery({
    queryKey: ["settings", "editable"],
    queryFn: getSettings,
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
  return { health, settings, qbit, radarr, seerr };
}
