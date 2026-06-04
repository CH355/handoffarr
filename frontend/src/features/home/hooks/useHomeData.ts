import { useQuery } from "@tanstack/react-query";
import { getCleanupSummary } from "@/api/cleanupApi";
import { getValidation } from "@/api/validationApi";
import { getStorage } from "@/api/storageApi";
import { listImports } from "@/api/importsApi";
import { getStates } from "@/api/debugApi";

/* Home server-state composition per frontend-implementation-spec-v1.md §7.2.
   Each query owns its own loading/error so the page can degrade per-card. */
export function useHomeData() {
  const cleanup = useQuery({
    queryKey: ["cleanup"],
    queryFn: getCleanupSummary,
    staleTime: 30_000,
  });
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
  // R-B1: tile-level rollup is a backend gap; probe used as best-effort context.
  const states = useQuery({
    queryKey: ["debug", "states"],
    queryFn: getStates,
    staleTime: 30_000,
    retry: 0,
  });

  return { cleanup, validation, storage, imports, states };
}
