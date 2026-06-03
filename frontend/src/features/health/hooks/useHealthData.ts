import { useQuery } from "@tanstack/react-query";
import { getValidation } from "@/api/validationApi";
import { getStorage } from "@/api/storageApi";
import { listImports } from "@/api/importsApi";
import { getQbitProbe, getRadarrProbe, getSeerrProbe } from "@/api/healthApi";

/* Health server-state composition. Each probe owns its loading/error so the
   page degrades per-card per frontend-implementation-spec-v1.md §7.2. */
export function useHealthData() {
  const validation = useQuery({
    queryKey: ["validation"],
    queryFn: getValidation,
    staleTime: 30_000,
  });
  const storage = useQuery({
    queryKey: ["storage"],
    queryFn: getStorage,
    staleTime: 60_000,
  });
  const imports = useQuery({
    queryKey: ["imports"],
    queryFn: listImports,
    staleTime: 60_000,
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

  return { validation, storage, imports, qbit, radarr, seerr };
}
