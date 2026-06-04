import { useQuery } from "@tanstack/react-query";
import { getLibraryMedia } from "@/api/libraryApi";
import { getMediaTimeline, getMediaImports } from "@/api/timelineApi";
import { useRefreshQueryOptions } from "@/hooks/useRefreshQueryOptions";

/* Item Detail server-state per frontend-implementation-spec-v1.md §7.2.
   30s staleTime per §6.4 — detail freshness matters. */
export function useItemDetailData(mediaId: string) {
  const medium = useRefreshQueryOptions("medium");
  const heavy = useRefreshQueryOptions("heavy");
  const library = useQuery({
    queryKey: ["library", mediaId],
    queryFn: () => getLibraryMedia(mediaId),
    ...medium,
    enabled: !!mediaId,
  });
  const timeline = useQuery({
    queryKey: ["library", mediaId, "timeline"],
    queryFn: () => getMediaTimeline(mediaId),
    ...heavy,
    enabled: false,
  });
  const imports = useQuery({
    queryKey: ["imports", mediaId],
    queryFn: () => getMediaImports(mediaId),
    ...medium,
    enabled: !!mediaId,
  });
  return { library, timeline, imports };
}
