import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppShell } from "@/components/AppShell";
import { HomePage } from "@/features/home/HomePage";
import { RecoverSpacePage } from "@/features/recover/RecoverSpacePage";
import { LibraryPage } from "@/features/library/LibraryPage";
import { HealthPage } from "@/features/health/HealthPage";
import { SettingsPage } from "@/features/settings/SettingsPage";

/* Route skeletons — frontend-implementation-spec-v1.md §4.
   Sprint 1 wires only the five primary nav routes; sub-routes land in later sprints. */
export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: <HomePage /> },
      { path: "recover", element: <RecoverSpacePage /> },
      { path: "library", element: <LibraryPage /> },
      { path: "health", element: <HealthPage /> },
      { path: "settings", element: <SettingsPage /> },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);
