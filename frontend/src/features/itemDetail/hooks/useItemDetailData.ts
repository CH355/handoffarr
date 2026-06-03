import { useQuery } from "@tanstack/react-query";
import { getLibraryMedia } from "@/api/libraryApi";
import { getMediaTimeline, getMediaImports } from "@/api/timelineApi";

/* Item Detail server-state per frontend-implementation-spec-v1.md §7.2.
   30s staleTime per §6.4 — detail freshness matters. */
export function useItemDetailData(mediaId: string) {
  const library = useQuery({
    queryKey: ["library", mediaId],
    queryFn: () => getLibraryMedia(mediaId),
    staleTime: 30_000,
    enabled: !!mediaId,
  });
  const timeline = useQuery({
    queryKey: ["library", mediaId, "timeline"],
    queryFn: () => getMediaTimeline(mediaId),
    staleTime: 30_000,
    enabled: !!mediaId,
  });
  const imports = useQuery({
    queryKey: ["imports", mediaId],
    queryFn: () => getMediaImports(mediaId),
    staleTime: 30_000,
    enabled: !!mediaId,
  });
  return { library, timeline, imports };
}
