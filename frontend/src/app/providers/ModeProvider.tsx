import { useEffect, type ReactNode } from "react";
import { useModeStore } from "@/app/stores/useModeStore";
import { useDensityStore } from "@/app/stores/useDensityStore";

export function ModeProvider({ children }: { children: ReactNode }) {
  const mode = useModeStore((s) => s.mode);
  const density = useDensityStore((s) => s.density);

  useEffect(() => {
    document.documentElement.setAttribute("data-mode", mode);
    document.documentElement.setAttribute(
      "data-density",
      mode === "expert" ? density : "comfortable",
    );
  }, [mode, density]);

  return <>{children}</>;
}
