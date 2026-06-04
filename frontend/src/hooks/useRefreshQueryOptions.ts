import { useRefreshPreferencesStore } from "@/app/stores/useRefreshPreferencesStore";

export type EndpointWeight = "light" | "medium" | "heavy";

export function useRefreshQueryOptions(weight: EndpointWeight) {
  const autoRefreshEnabled = useRefreshPreferencesStore((s) => s.autoRefreshEnabled);
  const refreshOnWindowFocus = useRefreshPreferencesStore((s) => s.refreshOnWindowFocus);
  const heavyEndpointsManualOnly = useRefreshPreferencesStore((s) => s.heavyEndpointsManualOnly);
  const refetchInterval: number | false =
    weight === "light" && autoRefreshEnabled ? 60_000 : false;

  return {
    staleTime: weight === "light" ? 60_000 : Number.POSITIVE_INFINITY,
    gcTime: 30 * 60_000,
    refetchOnMount: false as const,
    refetchOnWindowFocus:
      weight === "heavy" && heavyEndpointsManualOnly ? false : refreshOnWindowFocus,
    refetchInterval,
  };
}
