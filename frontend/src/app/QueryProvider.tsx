import { useState, type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { auditMark } from "@/perf/audit";

/* Server-state owner per frontend-implementation-spec-v1.md §6.1.
   Defaults align with §6.3; per-query overrides set in feature hooks. */
export function QueryProvider({ children }: { children: ReactNode }) {
  const [client] = useState(
    () => {
      const queryClient = new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            refetchOnWindowFocus: true,
            retry: 1,
          },
        },
      });
      queryClient.getQueryCache().subscribe((event) => {
        auditMark("query_cache_update", JSON.stringify(event.query.queryKey), {
          event_type: event.type,
          fetch_status: event.query.state.fetchStatus,
          status: event.query.state.status,
          data_updated_at: event.query.state.dataUpdatedAt,
        });
      });
      return queryClient;
    },
  );
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
