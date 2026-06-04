import { create } from "zustand";
import { persist } from "zustand/middleware";

interface RefreshPreferencesState {
  autoRefreshEnabled: boolean;
  refreshOnWindowFocus: boolean;
  diagnosticsAutoLoad: boolean;
  heavyEndpointsManualOnly: boolean;
  setAutoRefreshEnabled: (enabled: boolean) => void;
  setRefreshOnWindowFocus: (enabled: boolean) => void;
  setDiagnosticsAutoLoad: (enabled: boolean) => void;
  setHeavyEndpointsManualOnly: (enabled: boolean) => void;
}

export const useRefreshPreferencesStore = create<RefreshPreferencesState>()(
  persist(
    (set) => ({
      autoRefreshEnabled: false,
      refreshOnWindowFocus: false,
      diagnosticsAutoLoad: false,
      heavyEndpointsManualOnly: true,
      setAutoRefreshEnabled: (enabled) => set({ autoRefreshEnabled: enabled }),
      setRefreshOnWindowFocus: (enabled) => set({ refreshOnWindowFocus: enabled }),
      setDiagnosticsAutoLoad: (enabled) => set({ diagnosticsAutoLoad: enabled }),
      setHeavyEndpointsManualOnly: (enabled) => set({ heavyEndpointsManualOnly: enabled }),
    }),
    { name: "handoffarr.refresh-preferences" },
  ),
);
