import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppShell } from "@/components/AppShell";
import { HomePage } from "@/features/home/HomePage";
import { RecoverSpacePage } from "@/features/recover/RecoverSpacePage";
import { SafeCandidateReviewPage } from "@/features/recover/SafeCandidateReviewPage";
import { ItemJudgmentPage } from "@/features/recover/ItemJudgmentPage";
import { PreviewPage } from "@/features/recover/PreviewPage";
import { CleanupHistoryPage } from "@/features/recover/CleanupHistoryPage";
import { CleanupBatchDetailPage } from "@/features/recover/CleanupBatchDetailPage";
import { LibraryPage } from "@/features/library/LibraryPage";
import { ItemDetailSurface } from "@/features/itemDetail/ItemDetailSurface";
import { HealthPage } from "@/features/health/HealthPage";
import { IntegrationDetailPage } from "@/features/health/IntegrationDetailPage";
import { SettingsPage } from "@/features/settings/SettingsPage";
import { DiagnosticsRoute } from "@/features/diagnostics/DiagnosticsRoute";

/* Route skeletons — frontend-implementation-spec-v1.md §4.
   Sprint 3 adds the Recover Space sub-routes (§4.2). */
export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: <HomePage /> },
      { path: "recover", element: <RecoverSpacePage /> },
      { path: "recover/safe", element: <SafeCandidateReviewPage /> },
      { path: "recover/judgment", element: <ItemJudgmentPage /> },
      { path: "recover/preview", element: <PreviewPage /> },
      { path: "recover/history", element: <CleanupHistoryPage /> },
      { path: "recover/history/:batchId", element: <CleanupBatchDetailPage /> },
      {
        path: "library",
        element: <LibraryPage />,
        children: [{ path: ":mediaId", element: <ItemDetailSurface /> }],
      },
      { path: "health", element: <HealthPage /> },
      {
        path: "health/integrations/:integrationId",
        element: <IntegrationDetailPage />,
      },
      { path: "settings", element: <SettingsPage /> },
      { path: "settings/diagnostics", element: <DiagnosticsRoute /> },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);
