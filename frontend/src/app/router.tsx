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
import { TorrentDetailPage } from "@/features/torrents/TorrentDetailPage";
import { TorrentsPage } from "@/features/torrents/TorrentsPage";
import { RecoveryAgentPage } from "@/features/recoveryAgent/RecoveryAgentPage";
import { AuditProfiler } from "@/perf/audit";

/* Route skeletons — frontend-implementation-spec-v1.md §4.
   Sprint 3 adds the Recover Space sub-routes (§4.2). */
export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: <AuditProfiler id="route:Home"><HomePage /></AuditProfiler> },
      { path: "recover", element: <AuditProfiler id="route:Recover"><RecoverSpacePage /></AuditProfiler> },
      { path: "recover/safe", element: <SafeCandidateReviewPage /> },
      { path: "recover/judgment", element: <ItemJudgmentPage /> },
      { path: "recover/preview", element: <PreviewPage /> },
      { path: "recover/history", element: <CleanupHistoryPage /> },
      { path: "recover/history/:batchId", element: <CleanupBatchDetailPage /> },
      {
        path: "library",
        element: <AuditProfiler id="route:Library"><LibraryPage /></AuditProfiler>,
        children: [{ path: ":mediaId", element: <AuditProfiler id="route:ItemDetail"><ItemDetailSurface /></AuditProfiler> }],
      },
      {
        path: "torrents",
        element: <AuditProfiler id="route:Torrents"><TorrentsPage /></AuditProfiler>,
        children: [{ path: ":torrentHash", element: <TorrentDetailPage /> }],
      },
      { path: "recovery-agent", element: <RecoveryAgentPage /> },
      { path: "health", element: <AuditProfiler id="route:Health"><HealthPage /></AuditProfiler> },
      {
        path: "health/integrations/:integrationId",
        element: <IntegrationDetailPage />,
      },
      { path: "settings", element: <AuditProfiler id="route:Settings"><SettingsPage /></AuditProfiler> },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);
