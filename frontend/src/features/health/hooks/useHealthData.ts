import { useQuery } from "@tanstack/react-query";
import { getValidation } from "@/api/validationApi";
import { getStorage } from "@/api/storageApi";
import { listImports } from "@/api/importsApi";
import { getQbitProbe, getRadarrProbe, getSeerrProbe } from "@/api/healthApi";
import { useRefreshQueryOptions } from "@/hooks/useRefreshQueryOptions";

/* Health server-state composition. Each probe owns its loading/error so the
   page degrades per-card per frontend-implementation-spec-v1.md §7.2. */
export function useHealthData() {
  const light = useRefreshQueryOptions("light");
  const medium = useRefreshQueryOptions("medium");
  const heavy = useRefreshQueryOptions("heavy");
  const validation = useQuery({
    queryKey: ["validation"],
    queryFn: getValidation,
    ...light,
  });
  const storage = useQuery({
    queryKey: ["storage"],
    queryFn: getStorage,
    ...medium,
  });
  const imports = useQuery({
    queryKey: ["imports"],
    queryFn: listImports,
    ...medium,
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

  return { validation, storage, imports, qbit, radarr, seerr };
}
