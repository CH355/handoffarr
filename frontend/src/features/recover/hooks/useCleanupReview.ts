import { useQuery } from "@tanstack/react-query";
import {
  getCleanupReview,
  getCleanupSummary,
  getCleanupExecutions,
  type CleanupExecutionsResponse,
  type CleanupReviewFilters,
} from "@/api/cleanupApi";
import { useRefreshQueryOptions } from "@/hooks/useRefreshQueryOptions";

/* Per frontend-implementation-spec-v1.md §6.2/§6.3. */

export function useCleanupSummaryQuery() {
  const medium = useRefreshQueryOptions("medium");
  return useQuery({
    queryKey: ["cleanup"],
    queryFn: getCleanupSummary,
    ...medium,
  });
}

export function useCleanupReviewQuery(filters: CleanupReviewFilters = {}) {
  const medium = useRefreshQueryOptions("medium");
  return useQuery({
    queryKey: ["cleanup", "review", filters],
    queryFn: () => getCleanupReview(filters),
    ...medium,
  });
}

export function useCleanupExecutionsQuery() {
  const medium = useRefreshQueryOptions("medium");
  return useQuery({
    queryKey: ["cleanup", "executions"],
    queryFn: () => getCleanupExecutions(50),
    ...medium,
    refetchInterval: (query) => hasStartedExecution(query.state.data) ? 15_000 : false,
  });
}

function hasStartedExecution(data: CleanupExecutionsResponse | undefined) {
  return data?.executions.some((execution) => execution.execution_status === "Started") ?? false;
}
