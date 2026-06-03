import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Density = "comfortable" | "compact";

interface DensityState {
  density: Density;
  setDensity: (density: Density) => void;
}

export const useDensityStore = create<DensityState>()(
  persist(
    (set) => ({
      density: "comfortable",
      setDensity: (density) => set({ density }),
    }),
    { name: "handoffarr.density" },
  ),
);
