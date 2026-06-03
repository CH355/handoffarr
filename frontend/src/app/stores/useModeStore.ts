import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Mode = "normal" | "expert";

interface ModeState {
  mode: Mode;
  setMode: (mode: Mode) => void;
}

export const useModeStore = create<ModeState>()(
  persist(
    (set) => ({
      mode: "normal",
      setMode: (mode) => set({ mode }),
    }),
    { name: "handoffarr.mode" },
  ),
);
