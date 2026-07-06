import { lazy, Suspense, type ReactNode } from "react";
import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppShell } from "@/components/AppShell";
import { HomePage } from "@/features/home/HomePage";
import { AuditProfiler } from "@/perf/audit";

const RecoverSpacePage = lazy(() => import("@/features/recover/RecoverSpacePage").then(module => ({ default: module.RecoverSpacePage })));
const SafeCandidateReviewPage = lazy(() => import("@/features/recover/SafeCandidateReviewPage").then(module => ({ default: module.SafeCandidateReviewPage })));
const ItemJudgmentPage = lazy(() => import("@/features/recover/ItemJudgmentPage").then(module => ({ default: module.ItemJudgmentPage })));
const PreviewPage = lazy(() => import("@/features/recover/PreviewPage").then(module => ({ default: module.PreviewPage })));
const CleanupHistoryPage = lazy(() => import("@/features/recover/CleanupHistoryPage").then(module => ({ default: module.CleanupHistoryPage })));
const CleanupBatchDetailPage = lazy(() => import("@/features/recover/CleanupBatchDetailPage").then(module => ({ default: module.CleanupBatchDetailPage })));
const LibraryPage = lazy(() => import("@/features/library/LibraryPage").then(module => ({ default: module.LibraryPage })));
const ItemDetailSurface = lazy(() => import("@/features/itemDetail/ItemDetailSurface").then(module => ({ default: module.ItemDetailSurface })));
const HealthPage = lazy(() => import("@/features/health/HealthPage").then(module => ({ default: module.HealthPage })));
const IntegrationDetailPage = lazy(() => import("@/features/health/IntegrationDetailPage").then(module => ({ default: module.IntegrationDetailPage })));
const SettingsPage = lazy(() => import("@/features/settings/SettingsPage").then(module => ({ default: module.SettingsPage })));
const TorrentDetailPage = lazy(() => import("@/features/torrents/TorrentDetailPage").then(module => ({ default: module.TorrentDetailPage })));
const TorrentsPage = lazy(() => import("@/features/torrents/TorrentsPage").then(module => ({ default: module.TorrentsPage })));
const RecoveryAgentPage = lazy(() => import("@/features/recoveryAgent/RecoveryAgentPage").then(module => ({ default: module.RecoveryAgentPage })));
const RecoveryPlansPage = lazy(() => import("@/features/recoveryAgent/RecoveryPlansPage").then(module => ({ default: module.RecoveryPlansPage })));
const RecoveryPlanDetailPage = lazy(() => import("@/features/recoveryAgent/RecoveryPlanDetailPage").then(module => ({ default: module.RecoveryPlanDetailPage })));
const RecoveryHistoryPage = lazy(() => import("@/features/recoveryAgent/RecoveryHistoryPage").then(module => ({ default: module.RecoveryHistoryPage })));
const RecoveryActivityPage = lazy(() => import("@/features/recoveryAgent/RecoveryActivityPage").then(module => ({ default: module.RecoveryActivityPage })));

function deferred(element: ReactNode) {
  return <Suspense fallback={<div className="m-6 h-64 animate-pulse rounded-lg bg-surface" aria-label="Loading page" />}>{element}</Suspense>;
}

/* Route skeletons — frontend-implementation-spec-v1.md §4.
   Sprint 3 adds the Recover Space sub-routes (§4.2). */
export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: <AuditProfiler id="route:Home"><HomePage /></AuditProfiler> },
      { path: "recover", element: deferred(<AuditProfiler id="route:Recover"><RecoverSpacePage /></AuditProfiler>) },
      { path: "recover/safe", element: deferred(<SafeCandidateReviewPage />) },
      { path: "recover/judgment", element: deferred(<ItemJudgmentPage />) },
      { path: "recover/preview", element: deferred(<PreviewPage />) },
      { path: "recover/history", element: deferred(<CleanupHistoryPage />) },
      { path: "recover/history/:batchId", element: deferred(<CleanupBatchDetailPage />) },
      {
        path: "library",
        element: deferred(<AuditProfiler id="route:Library"><LibraryPage /></AuditProfiler>),
        children: [{ path: ":mediaId", element: deferred(<AuditProfiler id="route:ItemDetail"><ItemDetailSurface /></AuditProfiler>) }],
      },
      {
        path: "torrents",
        element: deferred(<AuditProfiler id="route:Torrents"><TorrentsPage /></AuditProfiler>),
        children: [{ path: ":torrentHash", element: deferred(<TorrentDetailPage />) }],
      },
      { path: "recovery-agent", element: deferred(<RecoveryAgentPage />) },
      { path: "recovery-agent/plans", element: deferred(<RecoveryPlansPage />) },
      { path: "recovery-agent/plans/:planId", element: deferred(<RecoveryPlanDetailPage />) },
      { path: "recovery-agent/history", element: deferred(<RecoveryHistoryPage />) },
      { path: "recovery-agent/activity", element: deferred(<RecoveryActivityPage />) },
      { path: "health", element: deferred(<AuditProfiler id="route:Health"><HealthPage /></AuditProfiler>) },
      {
        path: "health/integrations/:integrationId",
        element: deferred(<IntegrationDetailPage />),
      },
      { path: "settings", element: deferred(<AuditProfiler id="route:Settings"><SettingsPage /></AuditProfiler>) },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);
