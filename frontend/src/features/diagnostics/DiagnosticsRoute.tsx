import { Navigate } from "react-router-dom";
import { useModeStore } from "@/app/stores/useModeStore";
import { DiagnosticsPage } from "./DiagnosticsPage";

export function DiagnosticsRoute() {
  const mode = useModeStore((s) => s.mode);
  return mode === "expert" ? <DiagnosticsPage /> : <Navigate to="/settings" replace />;
}
