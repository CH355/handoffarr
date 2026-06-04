import { useQuery } from "@tanstack/react-query";
import {
  getCleanupReview,
  getCleanupSummary,
  getCleanupExecutions,
  type CleanupExecutionsResponse,
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

export function useCleanupExecutionsQuery() {
  return useQuery({
    queryKey: ["cleanup", "executions"],
    queryFn: () => getCleanupExecutions(500),
    staleTime: 15_000,
    refetchOnWindowFocus: true,
    refetchInterval: (query) => hasStartedExecution(query.state.data) ? 5_000 : false,
  });
}

function hasStartedExecution(data: CleanupExecutionsResponse | undefined) {
  return data?.executions.some((execution) => execution.execution_status === "Started") ?? false;
}
