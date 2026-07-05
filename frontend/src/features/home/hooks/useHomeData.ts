import { useQuery } from "@tanstack/react-query";
import { getCleanupSummary } from "@/api/cleanupApi";
import { getValidation } from "@/api/validationApi";
import { getStorage } from "@/api/storageApi";
import { listImports } from "@/api/importsApi";
import { listTorrents } from "@/api/torrentsApi";
import { useRefreshQueryOptions } from "@/hooks/useRefreshQueryOptions";

/* Home server-state composition per frontend-implementation-spec-v1.md §7.2.
   Each query owns its own loading/error so the page can degrade per-card. */
export function useHomeData() {
  const light = useRefreshQueryOptions("light");
  const medium = useRefreshQueryOptions("medium");
  const cleanup = useQuery({
    queryKey: ["cleanup"],
    queryFn: getCleanupSummary,
    ...medium,
  });
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
  const torrents = useQuery({
    queryKey: ["torrents"],
    queryFn: listTorrents,
    ...medium,
  });

  return { cleanup, validation, storage, imports, torrents };
}
