import { useQuery } from "@tanstack/react-query";
import {
  getCleanupReview,
  getCleanupSummary,
  getCleanupExecutions,
  getCleanupExecutionBatchDetail,
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
    refetchInterval: (query) => {
      const data = query.state.data;
      const hasActive =
        data?.executions.some((e) =>
          ["Queued", "Running"].includes(String(e.execution_status ?? "")),
        ) ||
        data?.batches.some((b) => ["Queued", "Running"].includes(String(b.status ?? "")));
      return hasActive ? 2_000 : false;
    },
  });
}

export function useCleanupBatchDetailQuery(batchId: string | undefined) {
  return useQuery({
    queryKey: ["cleanup", "execution-batches", batchId],
    queryFn: () => getCleanupExecutionBatchDetail(batchId ?? ""),
    enabled: Boolean(batchId),
    staleTime: 0,
    refetchInterval: (query) => {
      const status = String(query.state.data?.status ?? "");
      return ["Queued", "Running"].includes(status) ? 2_000 : false;
    },
  });
}
