import { useQuery } from "@tanstack/react-query";
import { getLibrary } from "@/api/libraryApi";
import { useRefreshQueryOptions } from "@/hooks/useRefreshQueryOptions";

/* Library list per frontend-implementation-spec-v1.md §6.2 / §7.2.
   60s staleTime per §6.4. Search/filter/sort are client-side (R-B5). */
export function useLibraryData() {
  const medium = useRefreshQueryOptions("medium");
  return useQuery({
    queryKey: ["library"],
    queryFn: getLibrary,
    ...medium,
  });
}
