import { useQuery } from "@tanstack/react-query";
import {
  getCleanupReview,
  getCleanupSummary,
  getCleanupExecutions,
  type CleanupReviewFilters,
} from "@/api/cleanupApi";

/* Per frontend-implementation-spec-v1.md §6.2/§6.3. */

export function useCleanupSummaryQuery() {
  return useQuery({
    queryKey: ["cleanup"],
    queryFn: getCleanupSummary,
    staleTime: 30_000,
  });
}

export function useCleanupReviewQuery(filters: CleanupReviewFilters = {}) {
  return useQuery({
    queryKey: ["cleanup", "review", filters],
    queryFn: () => getCleanupReview(filters),
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });
}

export function useCleanupExecutionsQuery(limit = 100) {
  return useQuery({
    queryKey: ["cleanup", "executions", limit],
    queryFn: () => getCleanupExecutions(limit),
    staleTime: 0,
    refetchOnWindowFocus: true,
  });
}
