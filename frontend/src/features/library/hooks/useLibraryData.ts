import { useQuery } from "@tanstack/react-query";
import { getLibrary } from "@/api/libraryApi";

/* Library list per frontend-implementation-spec-v1.md §6.2 / §7.2.
   60s staleTime per §6.4. Search/filter/sort are client-side (R-B5). */
export function useLibraryData() {
  return useQuery({
    queryKey: ["library"],
    queryFn: getLibrary,
    staleTime: 60_000,
  });
}
