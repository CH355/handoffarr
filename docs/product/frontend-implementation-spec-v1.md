# Handoffarr Frontend Implementation Spec — v1
## How the Approved UX Package Will Be Built

> **Status.** This is an implementation artifact. It sits **below** the UI Implementation Roadmap and **above** actual code. It does not redesign, re-architect, re-flow, rename, or extend anything. The locked authority order remains: **UX Audit → UX Blueprint → Visual Design Foundation → UI Reference Mockups → UI Implementation Roadmap → DESIGN_AUTHORITY**. If this document appears to contradict any locked artifact, the locked artifact wins and this document is in error.

> **Document v1.1 note.** Where the locked authorities reference v1.1 sub-versions (Blueprint v1.1 C1/C4, Mockups v1.1 §5A, etc.), this spec treats the published v1 file in `docs/product/` as the carrier of those v1.1 reconciliations, since those files already incorporate the v1.1 change logs.

---

## 0. DOCUMENT MAP

1. Purpose
2. Frontend Technology Stack
3. Application Architecture
4. Route Architecture
5. Component Architecture
6. State Management Architecture
7. API Layer Specification
8. Type System Architecture
9. Folder Structure
10. Screen Ownership Matrix
11. Sprint Mapping
12. Testing Strategy
13. Risks
14. Definition of Done

---

## 1. PURPOSE

### 1.1 Why this document exists

The Roadmap answered the question *when* each screen ships and in what order. The Blueprint, Foundation, and Mockups answered *what* each screen is. Neither answered *how* the engineering team should structure the code that produces those screens.

Without that answer, six predictable failures occur during sprint work:

- Engineers reinvent state ownership conventions per screen.
- API calls scatter across components instead of consolidating in a typed client.
- Types fork between server response shapes and view models, producing the "two `Item` interfaces" problem.
- Routing decisions get made screen-by-screen and produce inconsistent URL hierarchies.
- Component ownership boundaries blur, so a "small change" in one feature edits files in three others.
- Sprint acceptance criteria become hard to verify because there is no agreed altitude for "feature complete."

This document fixes those questions in advance, once, in alignment with the locked UX package, so sprints can spend their budget on the screens themselves.

### 1.2 Relationship to the Roadmap

The Roadmap specifies sprint *content*: which screens, which components, which acceptance criteria. This spec specifies sprint *form*: which folder each component lives in, which hook fetches its data, which type the data conforms to. Every sprint in §11 here is a one-to-one mirror of the Roadmap's Sprints 1–8.

### 1.3 Relationship to the Blueprint

The Blueprint owns information architecture, flows, and the screen inventory. This spec owns route hierarchy and feature folders that *realize* that IA. No route, no feature, and no folder in this spec exists for a screen the Blueprint does not approve.

### 1.4 Relationship to the Mockups

The Mockups own visual structure and component anatomy. This spec owns the component *file* tree that realizes that anatomy. Every component named in §5 here corresponds to a Mockup-defined surface; no component is invented.

### 1.5 Relationship to actual implementation

This spec is the brief engineers open before writing the first file of a sprint. Once a sprint begins, the spec is no longer mutable for that sprint's scope. Mid-sprint deviations require either a Roadmap amendment (for scope) or a Spec amendment (for engineering form). UX-affecting deviations require a Blueprint / Foundation / Mockup amendment, which is outside engineering's authority.

> **This document defines HOW approved UX is implemented, not WHAT the UX is.**

---

## 2. FRONTEND TECHNOLOGY STACK

### 2.1 Required

- **React** (latest stable major) with function components and hooks only. No class components.
- **TypeScript** strict mode (`strict: true`, `noUncheckedIndexedAccess: true`, `exactOptionalPropertyTypes: true`).
- **Tailwind CSS** as the sole utility layer. All Foundation tokens are exposed through Tailwind's `theme.extend` so they can be referenced as `bg-surface`, `text-muted`, `rounded-lg`, etc. Hand-written CSS is permitted only for the Foundation token sheet itself and for the focus-visible global.
- **shadcn/ui** as the primitive layer (Button, Input, Dialog, Drawer, Tooltip, Tabs, Toast, Checkbox, RadioGroup, Switch, Popover, Command). Components are *copied* into the repo per shadcn convention and then themed to match Foundation §9 — they are not imported from a published package.

### 2.2 Preferred

- **Vite** as the build tool. Fast HMR keeps Foundation-token iteration cheap.
- **React Router** (data router API) for routing. Loaders are not used for data fetching (TanStack Query owns that); they are used only for code-splitting and route-level access gates.
- **TanStack Query** for server state. Keys, staleTime, and invalidation are spec'd in §6.
- **Zustand** for the small amount of cross-screen UI state that is not server state (Mode toggle, theme, density). One store per concern. Redux is **not** approved.
- **React Hook Form** + **Zod** for form state and validation (Settings, Integration Detail, First Run Step 2).
- **Lucide React** for the icon allowlist defined in Foundation §6.3.
- **clsx** + **tailwind-merge** for className composition.
- **date-fns** for date formatting. Day.js or Moment are not approved.
- **Vitest** + **React Testing Library** + **MSW** for tests. Storybook for component documentation and visual regression.
- **Playwright** for end-to-end and accessibility audits.
- **axe-core** integrated into both Storybook and Playwright for accessibility checks.

### 2.3 Forbidden architectural patterns

- **Redux / Redux Toolkit / MobX / Recoil / Jotai.** The server-state library plus a small Zustand surface covers every case described in §6.
- **Duplicated API clients.** There is one `src/api/` directory, one fetcher (§7.1), one error-shape adapter. Feature code does not call `fetch` directly.
- **UI frameworks outside the approved stack.** Material UI, Chakra, Mantine, Ant Design, Bootstrap, Tailwind UI Plus copy-pastes that are not Foundation-styled, or any other component library is forbidden.
- **Custom design systems outside Foundation.** No `theme.ts` overriding Foundation tokens, no parallel "branded" component layer, no `styled-components` or Emotion.
- **CSS-in-JS at runtime.** Tailwind utilities are the styling primitive; runtime CSS-in-JS conflicts with the dark-mode parity rule (Foundation §12.2).
- **Inline `style` props for design-token values.** Tokens flow through Tailwind. Inline styles are reserved for dynamic non-token values (progress widths, animated transforms).
- **Per-screen state libraries.** A screen using TanStack Query and a screen using SWR and a screen using a custom `useFetch` is the pattern this section forbids.
- **Global event buses.** Cross-component communication is by props, context, query invalidation, or a Zustand store. Never `window.dispatchEvent`.
- **`any`, `as unknown as`, `@ts-expect-error` outside of test files.** Use a Zod schema instead.

---

## 3. APPLICATION ARCHITECTURE

### 3.1 Layers

```
┌─────────────────────────────────────────────────────────────┐
│  app/        Application root, providers, router setup       │
├─────────────────────────────────────────────────────────────┤
│  routes/     Route components — one file per URL             │
├─────────────────────────────────────────────────────────────┤
│  features/   Per-screen feature folders (Recover, Library,…) │
├─────────────────────────────────────────────────────────────┤
│  components/ Cross-feature shared components                 │
├─────────────────────────────────────────────────────────────┤
│  hooks/      Cross-feature shared hooks                      │
├─────────────────────────────────────────────────────────────┤
│  api/        Typed HTTP client + per-domain API modules      │
├─────────────────────────────────────────────────────────────┤
│  types/      Shared DTOs, domain models, view models         │
├─────────────────────────────────────────────────────────────┤
│  lib/        Pure utilities (formatters, predicates, guards) │
├─────────────────────────────────────────────────────────────┤
│  styles/     Foundation tokens, Tailwind config, globals     │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Responsibilities

- **`app/`** — Mounts providers (QueryClient, Router, ThemeProvider, ModeProvider, Toaster). Owns nothing visual.
- **`routes/`** — One file per URL. Each route file is *thin*: it composes a feature's exported page component with route-level concerns (params, redirects, code-split boundary). No business logic.
- **`features/`** — Each top-level screen owns a folder. A feature folder is the only place where its own components, hooks, and types live. Cross-feature imports go through `components/`, `hooks/`, or `api/` — never feature-to-feature.
- **`components/`** — Shared primitives (Button wrapping shadcn, Foundation-themed Drawer, StatusBadge, EvidenceDrawer). A component lives here only after it has at least two real consumers across different features, *or* it is named in Foundation §9 as a Foundation-tier component.
- **`hooks/`** — Cross-feature hooks (`useMode`, `useTheme`, `useMediaQuery`, `useFocusReturn`).
- **`api/`** — One module per backend domain (cleanup, library, health, settings, debug). All `fetch` calls live here. All endpoints return typed responses through Zod-validated parsers.
- **`types/`** — Shared types only. Feature-local types live in the feature folder. A type promotes to `types/` only when consumed by ≥2 features or by the API layer.
- **`lib/`** — Pure functions, no React, no I/O. `formatBytes`, `formatRelativeTime`, `isUndoWindowOpen`.
- **`styles/`** — Foundation tokens as CSS custom properties, the Tailwind config that maps them, `globals.css` for the focus-visible global, font face declarations.

### 3.3 Ownership boundaries

- A feature **never** imports from another feature folder. If two features need the same thing, it promotes to `components/`, `hooks/`, `api/`, `types/`, or `lib/`.
- `routes/` never imports from `api/`, `lib/`, or `types/` directly. Route files import a feature's exported page component and pass route params.
- `components/` never imports from `features/`. Shared means feature-agnostic.
- `api/` never imports from `features/`, `components/`, or `hooks/`. It is the lowest layer above `lib/`.
- `lib/` and `styles/` import from nothing in this app.

### 3.4 Layer dependency diagram

```
app/  →  routes/  →  features/  ⇄  components/  →  hooks/  →  api/  →  types/  →  lib/
                          │                            │         │
                          └──────────── hooks/ ────────┘         │
                                                                 ▼
                                                              styles/
```

Read left-to-right: a layer may import only from layers to its right. `components/` and `hooks/` may import from each other.

---

## 4. ROUTE ARCHITECTURE

Every URL below corresponds 1:1 to a screen in Blueprint §4 Screen Inventory + Roadmap §2 Screen Implementation Order. **No invented routes.** The legacy Jinja routes (`/`, `/timeline`) are not listed here; they are retired per Roadmap Sprint 6.

The new frontend mounts under `/v2` during incremental rollout (Roadmap §1) and graduates to `/` when Sprint 6 retires legacy. Paths below are written without the prefix.

### 4.1 Top-level routes

| URL | Parent | Children | Purpose (Blueprint reference) |
|---|---|---|---|
| `/` | — | — | Home (Blueprint §4 Home) |
| `/recover` | — | `/recover/safe`, `/recover/judgment`, `/recover/preview`, `/recover/history`, `/recover/history/:batchId` | Recover Space Summary (Blueprint §4 Recover Space) |
| `/library` | — | `/library/:mediaId` | Library list (Blueprint §4 Library) |
| `/library/:mediaId` | `/library` | — | Item Detail; drawer over `/library` at ≥tablet, full-screen route on mobile (Blueprint §4 Item Detail, Mockups §6) |
| `/health` | — | `/health/integrations/:integrationId` | Health summary (Blueprint §4 Health) |
| `/health/integrations/:integrationId` | `/health` | — | Integration Detail (Blueprint §4 Integration Detail, v1.1 M1) |
| `/settings` | — | `/settings/integrations`, `/settings/cleanup-rules`, `/settings/notifications`, `/settings/appearance`, `/settings/mode`, `/settings/diagnostics` | Settings root (Blueprint §4 Settings) |
| `/settings/diagnostics` | `/settings` | — | Diagnostics, Expert-gated (Blueprint §4 Diagnostics) |
| `/first-run` | — | `/first-run/step-1`, `/first-run/step-2`, `/first-run/step-3` | First Run shell (Blueprint §4 First Run, Mockups §10) |

### 4.2 Recover Space sub-routes

| URL | Parent | Purpose |
|---|---|---|
| `/recover` | — | Three-section summary (Mockups §2) |
| `/recover/safe` | `/recover` | Safe Candidate Review (Mockups §3, Blueprint §4 v1.1 C2) |
| `/recover/judgment` | `/recover` | Risky Candidate Review — Item Judgment one-at-a-time (Mockups §4) |
| `/recover/preview` | `/recover` | Preview / dry-run, full-screen not modal (Blueprint §4 v1.1 M3) |
| `/recover/history` | `/recover` | Cleanup History list (Blueprint §4 v1.1 M2) |
| `/recover/history/:batchId` | `/recover/history` | Cleanup Batch Detail (Blueprint §4 Cleanup Batch Detail) |

### 4.3 First Run sub-routes

| URL | Parent | Purpose |
|---|---|---|
| `/first-run/step-1` | `/first-run` | Welcome (Mockups §10) |
| `/first-run/step-2` | `/first-run` | Connect integrations |
| `/first-run/step-3` | `/first-run` | First scan / hand-off to Home |

### 4.4 Settings sub-routes

Settings is a sectioned page. Each section is a child route so deep links to a section work; navigating between sections does not unmount the section card layout.

| URL | Parent | Purpose |
|---|---|---|
| `/settings/integrations` | `/settings` | Integrations section |
| `/settings/cleanup-rules` | `/settings` | Cleanup rules section |
| `/settings/notifications` | `/settings` | Notifications section |
| `/settings/appearance` | `/settings` | Theme + density |
| `/settings/mode` | `/settings` | Normal / Expert toggle |
| `/settings/diagnostics` | `/settings` | Diagnostics (Expert-only render guard) |

`/settings` redirects to `/settings/integrations` on direct visit.

### 4.5 Expert Mode surfaces

Expert is not a route. It is a Mode flag (Zustand `useMode`) that surfaces:

- The `[EXPERT]` chip in the global header.
- Tabbed views inside `/library/:mediaId` (Overview / History / Source trail / Inspect — render-gated, not routed).
- Diagnostics section availability in `/settings/diagnostics` (route exists, contents render-gated).
- Library bulk-select bar on `/library` (render-gated).
- Item Judgment enrichments on `/recover/judgment` (render-gated).
- Health per-integration history on `/health/integrations/:integrationId` (render-gated).

No new URLs are added by Expert. Per Blueprint §8, Expert never removes or rearranges Normal Mode.

### 4.6 Route map summary

```
/                                       Home
/recover                                Recover Space Summary
  /recover/safe                         Safe Candidate Review
  /recover/judgment                     Item Judgment
  /recover/preview                      Preview (dry-run)
  /recover/history                      Cleanup History
    /recover/history/:batchId           Cleanup Batch Detail
/library                                Library
  /library/:mediaId                     Item Detail (drawer ≥tablet)
/health                                 Health
  /health/integrations/:integrationId   Integration Detail
/settings                               → redirects to /settings/integrations
  /settings/integrations
  /settings/cleanup-rules
  /settings/notifications
  /settings/appearance
  /settings/mode
  /settings/diagnostics                 Expert-gated
/first-run
  /first-run/step-1
  /first-run/step-2
  /first-run/step-3
```

---

## 5. COMPONENT ARCHITECTURE

The hierarchy below names every component approved by Blueprint §9 + Foundation §9 + Mockups + Roadmap §3. **No new components.**

### 5.1 Hierarchy

```
AppShell
├── Header (56px, Foundation §4.2)
│   ├── Wordmark
│   ├── PrimaryNavigation (5 entries)
│   ├── ModeChipSlot
│   │   └── ExpertChip (gated by useMode)
│   └── NotificationCenter (Sprint 8)
├── MobileBottomTabBar (≤sm, 5 entries)
└── <Outlet/>
    │
    ├── HomePage  (/)
    │   ├── PrimaryBanner (critical | recover | stuck | idle variants)
    │   ├── StatTileRow
    │   │   ├── StatTile — Storage
    │   │   ├── StatTile — Activity
    │   │   └── StatTile — Health
    │   └── RecentlyAddedSection
    │       ├── RecentlyAddedHeader (with View → link)
    │       └── RecentlyAddedRow × 5
    │
    ├── RecoverSpacePage  (/recover)
    │   ├── RecoverSpaceSection — Safe
    │   │   ├── RecommendationCard (Safe variant)
    │   │   └── InlineConfirmationStrip
    │   ├── RecoverSpaceSection — Judgment
    │   │   └── RecommendationCard (Judgment variant)
    │   ├── RecoverSpaceSection — NotRecommended
    │   │   └── RecommendationCard (NotRecommended variant)
    │   ├── ExecutionProgressStrip (top progress, during execute)
    │   └── SuccessStateBanner (with Undo + View)
    │
    ├── SafeCandidateReviewPage  (/recover/safe)
    │   ├── CandidateList
    │   │   └── ItemRow — Safe Candidate × N
    │   ├── StickyActionBar (live total)
    │   └── EvidenceDrawer (label: "Why safe?")
    │
    ├── PreviewPage  (/recover/preview)
    │   ├── PreviewScopeSummary
    │   ├── PreviewPerIntegrationProjection
    │   └── PreviewActionRow
    │
    ├── ItemJudgmentPage  (/recover/judgment)
    │   ├── ItemOfNProgress
    │   ├── ItemRow — Risky (large poster, bulleted reasons)
    │   ├── ThreeEqualButtons (Remove / Keep / Later)
    │   ├── EvidenceDrawer (label: "Why risky?")
    │   └── KeyboardShortcutHint  (Expert-gated: R / K / L)
    │
    ├── CleanupHistoryPage  (/recover/history)
    │   └── CleanupHistoryRow × N
    │
    ├── CleanupBatchDetailPage  (/recover/history/:batchId)
    │   ├── BatchHeader
    │   ├── BatchActionBar (Undo all)
    │   └── BatchItemRow × N (per-row Restore)
    │
    ├── LibraryPage  (/library)
    │   ├── LibrarySearchInput (40px Library variant)
    │   ├── FilterChipRow
    │   ├── SortDropdown
    │   ├── BulkSelectBar (Expert-gated)
    │   ├── LibraryItemRow × N
    │   └── LoadMoreButton
    │
    ├── ItemDetailSurface  (/library/:mediaId)
    │   ├── ItemDetailHeader (poster, title, size, status)
    │   ├── ItemDetailPrimaryAction (Verify / Remove / View in Health / Open in *arr)
    │   ├── ItemDetailTabStrip (Expert-gated)
    │   │   ├── OverviewTab
    │   │   ├── HistoryTab — ActivityTimeline Full
    │   │   ├── SourceTrailTab
    │   │   └── InspectTab
    │   ├── ActivityTimeline (Compact in Normal, Full in Expert)
    │   └── EvidenceDrawer (label: "Why?")
    │
    ├── HealthPage  (/health)
    │   ├── HealthSummaryBanner
    │   ├── IntegrationTileGroup
    │   │   └── HealthTile × N (clickable — documented exception)
    │   ├── InlineStuckItemsList (no separate screen — v1.1 M4)
    │   │   └── StuckItemRow × N (Inspect → /library/:mediaId)
    │   └── RecentIssuesSection
    │
    ├── IntegrationDetailPage  (/health/integrations/:integrationId)
    │   ├── IntegrationStatusHeader
    │   ├── IntegrationActionRow (Test connection / Reconnect / Edit settings)
    │   ├── IntegrationEditForm
    │   └── IntegrationLogsLink (Expert-gated, gated by R-B8)
    │
    ├── SettingsPage  (/settings/*)
    │   ├── SettingsSectionNav
    │   ├── SettingsSectionCard
    │   │   ├── SettingsRow — Toggle
    │   │   ├── SettingsRow — Text
    │   │   ├── SettingsRow — ManageLink
    │   │   ├── SettingsRow — ModeToggle
    │   │   └── SettingsRow — Save (per-section)
    │   └── ConfirmationModal (Foundation §9.11, rare)
    │
    ├── DiagnosticsPage  (/settings/diagnostics, Expert-gated)
    │   ├── EngineStatusSection (label permitted only here — v1.1 C4)
    │   ├── ReconciliationSection (label permitted only here — v1.1 C4)
    │   ├── ValidationReportsSection
    │   └── LogsSection (mono font, filter, export)
    │
    └── FirstRunShell  (/first-run/*)
        ├── FirstRunStep1
        ├── FirstRunStep2 (Connect form, per-row Test)
        └── FirstRunStep3 (First scan)
```

### 5.2 Per-component contract

For every component listed above:

| Field | Definition |
|---|---|
| **Responsibility** | Single, named in Mockups or Foundation §9. Components do exactly one thing. |
| **Parent** | The component that mounts it (from the hierarchy). Components do not self-mount. |
| **Children** | The components it owns. Not props it accepts. |
| **Reusability level** | One of: **Foundation** (Sprint 1, used everywhere), **Shared** (in `components/`, used across ≥2 features), **Feature** (in `features/<name>/components/`, used by one feature), **Page** (in `features/<name>/`, exported to a route). |

Reusability tiers determine folder placement (§9).

### 5.3 Reusability tier assignments

- **Foundation tier** → `components/foundation/`: Header, PrimaryNavigation, MobileBottomTabBar, ModeChipSlot, ExpertChip, Button, Input, StatusBadge, Icon, FocusRingGlobal, Skeleton, Spinner, TopProgressStrip.
- **Shared tier** → `components/`: EvidenceDrawer, ActivityTimeline, StickyActionBar, InlineConfirmationStrip, SuccessStateBanner, ConfirmationModal, ItemRow (base; variants are Feature tier).
- **Feature tier** → `features/<name>/components/`: HomePage's PrimaryBanner / StatTile / RecentlyAddedRow; RecoverSpacePage's RecommendationCard / RecoverSpaceSection; SafeCandidateReviewPage's CandidateList; ItemJudgmentPage's ItemOfNProgress / ThreeEqualButtons / KeyboardShortcutHint; LibraryPage's LibrarySearchInput / FilterChipRow / SortDropdown / BulkSelectBar / LibraryItemRow / LoadMoreButton; ItemDetailSurface's ItemDetailHeader / ItemDetailTabStrip / SourceTrailTab / InspectTab; HealthPage's HealthSummaryBanner / IntegrationTileGroup / HealthTile / InlineStuckItemsList / RecentIssuesSection; IntegrationDetailPage's IntegrationStatusHeader / IntegrationActionRow / IntegrationEditForm; SettingsPage's SettingsSectionCard / SettingsRow variants; DiagnosticsPage's EngineStatusSection / ReconciliationSection / ValidationReportsSection / LogsSection; FirstRunShell's three step components.
- **Page tier** → exported from `features/<name>/<Name>Page.tsx` and consumed by `routes/`.

---

## 6. STATE MANAGEMENT ARCHITECTURE

The exact ownership model. **No ambiguity.**

### 6.1 Five state categories

| Category | What it is | Where it lives | Library |
|---|---|---|---|
| **Server state** | Data fetched from the FastAPI backend (`app/main.py`) | TanStack Query cache | TanStack Query |
| **UI state (cross-screen)** | Mode (Normal/Expert), theme, density, mobile nav open | Zustand stores in `app/stores/` | Zustand |
| **UI state (local)** | Drawer open/closed, hover-revealed details, tab selection | `useState` in the owning component | React |
| **Form state** | Settings forms, Integration Edit form, First Run Step 2 | React Hook Form instances | RHF + Zod |
| **Execution state (transient)** | "Confirming → executing → succeeded/partial-fail/total-fail" on Recover Space | Local reducer in `RecoverSpacePage` driven by Query mutation lifecycle | React reducer + TanStack mutation |

### 6.2 TanStack Query keys

A flat, hierarchical key scheme. The first segment is the API domain; later segments are scoping params.

```
['cleanup']                                   GET /api/cleanup
['cleanup', 'review']                         GET /api/cleanup/review
['cleanup', 'review', mediaId]                GET /api/cleanup/review/:id
['cleanup', 'review', mediaId, 'checklist']   GET /api/cleanup/review/:id/checklist
['cleanup', 'action-plan']                    GET /api/cleanup/action-plan
['cleanup', 'executions']                     GET /api/cleanup/executions
['library']                                   GET /api/library
['library', mediaId]                          GET /api/library/:id
['library', mediaId, 'timeline']              GET /api/timeline/:id
['imports']                                   GET /api/imports
['imports', mediaId]                          GET /api/imports/:id
['storage']                                   GET /api/storage
['validation']                                GET /api/validation
['debug', 'states']                           GET /api/debug/states
['debug', 'radarr' | 'qbit' | 'seerr']        GET /api/debug/*
['debug', 'queue']                            GET /api/debug/queue
['responsibility', assessmentId]              GET /api/responsibility/:id
['decisions', mediaId]                        GET /api/decisions/:id
['events']                                    GET /api/events
['traces']                                    GET /api/traces
```

### 6.3 staleTime / refetch policy

| Key prefix | staleTime | refetchOnWindowFocus | Notes |
|---|---|---|---|
| `['cleanup']` (summary) | 30s | true | Drives Home banner and Recover Summary |
| `['cleanup', 'review', ...]` | 60s | false | Stable within a review session |
| `['cleanup', 'executions']` | 0 | true | History is timeline-sensitive |
| `['library']` | 60s | false | Large list, manual refresh acceptable |
| `['library', mediaId]` | 30s | true | Item Detail freshness matters |
| `['storage']` | 60s | true | Stat Tile background data |
| `['validation']` | 30s | true | Drives critical banner; Health |
| `['debug', ...]` | 0 | true | Probes are always live |
| `['events']` / `['traces']` | 0 | true | Diagnostics surfaces |

### 6.4 Invalidation rules

| After this mutation | Invalidate |
|---|---|
| `POST /api/cleanup/execute` (or batch) | `['cleanup']`, `['cleanup', 'executions']`, `['storage']`, `['library']` (lazy), `['validation']` |
| `POST /api/cleanup/execute/dry-run` | nothing (read-only) |
| `POST /api/poll-now` | `['cleanup']`, `['validation']`, `['debug', 'states']`, `['imports']` |
| Undo / Restore (when endpoint lands, R-B4) | `['cleanup', 'executions']`, `['storage']`, `['library']` |

### 6.5 Zustand stores

One store per concern. No combined "app store."

- `useModeStore` — `{ mode: 'normal' | 'expert', setMode }`. Persisted to `localStorage`.
- `useThemeStore` — `{ theme: 'light' | 'dark', setTheme }`. Default = `'dark'` (Foundation). Initial value resolves `prefers-color-scheme`; override persists.
- `useDensityStore` — `{ density: 'comfortable' | 'compact', setDensity }`. Expert-gated `compact`.
- `useNavStore` — `{ mobileNavOpen, openMobileNav, closeMobileNav }`. Non-persisted.

### 6.6 Form state

React Hook Form is the only form abstraction. Every form has a colocated Zod schema in `features/<name>/schemas/`. Schema-derived TypeScript types are the form's source of truth.

### 6.7 Execution state on Recover Space

The Recover flow is a small state machine because it has the most lifecycle stages. Modeled as a `useReducer` inside `RecoverSpacePage`:

```
'idle'
  → 'confirming'   (inline strip revealed)
    → 'executing'  (top progress strip + button disabled)
      → 'succeeded'      (SuccessStateBanner with Undo)
      | 'partial-fail'   (SuccessStateBanner, partial-fail variant)
      | 'total-fail'     (error banner, retry)
  → 'idle'  (after Undo window expires, banner converts to Meta note)
```

The reducer is driven entirely by the TanStack mutation lifecycle (`onMutate`, `onSuccess`, `onError`); it does not duplicate Query's loading flags.

---

## 7. API LAYER SPECIFICATION

### 7.1 Client architecture

```
src/api/
├── client.ts          # fetch wrapper: baseURL, JSON, error normalization
├── errors.ts          # ApiError + adapter from FastAPI error shape
├── schemas/           # Zod schemas mirroring backend responses
├── cleanupApi.ts
├── libraryApi.ts
├── timelineApi.ts
├── importsApi.ts
├── storageApi.ts
├── validationApi.ts
├── healthApi.ts       # composes debug/* probes per integration
├── debugApi.ts        # raw debug endpoints (Health, Diagnostics)
├── recommendationsApi.ts
├── responsibilityApi.ts
├── decisionsApi.ts
├── correlationApi.ts
├── eventsApi.ts
├── tracesApi.ts
└── settingsApi.ts     # client-only persistence + stubs for R-B7..R-B11
```

- `client.ts` exposes a single `request<T>(url, opts)` that returns a Zod-validated `T`. Every API module imports it.
- `errors.ts` adapts FastAPI's `{ detail }` envelope to a discriminated `ApiError` union the UI handles uniformly.
- Each domain module exports typed functions, **not** TanStack Query hooks. Hooks live in `hooks/` or `features/*/hooks/` and compose `useQuery` / `useMutation` with the API functions.

### 7.2 Screen → endpoint map

This is the Roadmap §6 matrix re-anchored at the API layer. Endpoints are existing only; backend gaps are tagged `R-B*` exactly as the Roadmap tagged them. **No invented endpoints.**

| Screen | API module | Endpoints used |
|---|---|---|
| Home | cleanupApi, validationApi, storageApi, importsApi, debugApi | `GET /api/cleanup`, `GET /api/validation`, `GET /api/storage`, `GET /api/imports`, `GET /api/debug/states` (Stat Tile rollup, R-B1) |
| Recover Space — Summary | cleanupApi | `GET /api/cleanup`, `GET /api/cleanup/action-plan`, `POST /api/cleanup/execute`, `POST /api/cleanup/execute/dry-run`, `POST /api/poll-now` |
| Safe Candidate Review | cleanupApi | `GET /api/cleanup/review`, `GET /api/cleanup/review/:id`, `GET /api/cleanup/review/:id/checklist`, `POST /api/cleanup/execute/batch`, `POST /api/cleanup/execute/batch-dry-run` |
| Preview | cleanupApi | `POST /api/cleanup/execute/dry-run` (or batch), `POST /api/cleanup/execute` (or batch) |
| Item Judgment | cleanupApi | `GET /api/cleanup/review?risky=true` (client-filtered), `GET /api/cleanup/review/:id`, `POST /api/cleanup/execute`; Keep/Later persistence absent (**R-B2**) |
| Cleanup History | cleanupApi | `GET /api/cleanup/executions`, `GET /api/cleanup/action-plan.txt` |
| Cleanup Batch Detail | cleanupApi | `GET /api/cleanup/executions` filtered client-side (drill-down absent, **R-B3**); Undo / Restore absent (**R-B4**) |
| Library | libraryApi | `GET /api/library`; client-side title search (**R-B5**) |
| Item Detail | libraryApi, timelineApi, importsApi, cleanupApi | `GET /api/library/:id`, `GET /api/timeline/:id`, `GET /api/imports/:id`, `GET /api/cleanup/:id`; "Flag for cleanup" absent (**R-B6**); "Remove from library" via `POST /api/cleanup/execute` |
| Health | validationApi, debugApi, healthApi | `GET /api/validation`, `GET /api/debug/states`, `GET /api/debug/radarr`, `GET /api/debug/qbit`, `GET /api/debug/seerr`, `GET /api/debug/queue` |
| Integration Detail | debugApi, settingsApi | `GET /api/debug/<integration>` for status + `Test connection`; `Edit settings` save absent (**R-B7**); `View logs` absent (**R-B8**) |
| Settings — Integrations | settingsApi | Read-only against existing config until **R-B7** |
| Settings — Cleanup rules | settingsApi | Read-only until **R-B9** |
| Settings — Notifications | settingsApi | Read-only until **R-B10** |
| Settings — Appearance | (client-only) | localStorage |
| Settings — Mode | (client-only initially) | localStorage; server sync deferred (**R-B11**) |
| Diagnostics — Engine status | recommendationsApi, responsibilityApi, decisionsApi, correlationApi, cleanupApi | `GET /api/recommendations`, `GET /api/responsibility`, `GET /api/decisions`, `GET /api/correlation`, `POST /api/poll-now` |
| Diagnostics — Validation reports | validationApi, debugApi | `GET /api/validation`, `GET /api/debug/library`, `GET /api/debug/imports`, `GET /api/debug/correlation` |
| Diagnostics — Logs | eventsApi, tracesApi, debugApi | `GET /api/events`, `GET /api/traces`, `GET /api/debug/export` |
| Item Detail — History (Expert) | timelineApi | `GET /api/timeline/:id` |
| Item Detail — Source trail (Expert) | responsibilityApi, debugApi | `GET /api/responsibility/:id`, `GET /api/debug/correlation`, `GET /api/debug/torrent/:hash` |
| Item Detail — Inspect (Expert) | decisionsApi, responsibilityApi, cleanupApi | `GET /api/decisions/:id`, `GET /api/responsibility/:id`, `POST /api/poll-now`; override classification absent (**R-B12**) |
| First Run — Step 2 | debugApi, settingsApi | `GET /api/debug/*` for Test; Connect save absent (**R-B7**) |

### 7.3 Backend dependencies

The R-B1..R-B12 gaps are not resolved here. They are restated as backend dependencies so frontend can ship the screen with graceful degradation (gap-visible, action-disabled, copy-adjusted) per Roadmap §7.4.

---

## 8. TYPE SYSTEM ARCHITECTURE

### 8.1 Three layers

```
DTO              (wire shape, Zod-derived from backend response)
   ▼
Domain model     (UI-agnostic, normalized, ID-keyed)
   ▼
View model       (screen-specific, derived per render)
```

- **DTOs** live in `src/api/schemas/`. They are the *only* place the wire shape is defined. They are derived from Zod schemas via `z.infer`. Examples: `CleanupSummaryDto`, `CleanupReviewItemDto`, `LibraryItemDto`, `ValidationReportDto`, `DebugStateDto`.
- **Domain models** live in `src/types/`. They are produced from DTOs by transformer functions colocated with each API module (e.g., `libraryApi.ts` exports `toLibraryItem(dto): LibraryItem`). Examples: `LibraryItem`, `CleanupCandidate`, `Integration`, `Execution`, `MediaTimelineEvent`.
- **View models** live in `features/<name>/viewModels/` (or inline in the consumer if used once). They are pure derivations from domain models — sort order, group-by, label resolution. They are never persisted.

### 8.2 Transformation boundaries

- Wire → Domain happens **exactly once per response**, inside the API module's typed function.
- Domain → View happens **per render**, in a memoized selector (`useMemo` or a colocated selector function).
- View → DTO does not exist. Mutations send Zod-validated input DTOs constructed from form state, never from view models.

### 8.3 Ownership rules

- A type appears in `types/` only when it is consumed by ≥2 features or by `api/`. Feature-local types live next to their consumer in `features/<name>/types.ts`.
- DTOs are **never** exported from `types/`. They are part of the API layer's contract and must not leak into UI code.
- No two files declare the same domain concept under different names. `LibraryItem` and `MediaItem` are the same thing or they are different things — never both.
- Discriminated unions over boolean flags for variant types (e.g., banner variants, candidate kinds).

### 8.4 Anti-duplication enforcement

- ESLint rule blocks `interface Item` and `type Item` declarations outside the canonical file.
- A Storybook story for each shared domain type renders a tagged example, so accidental forks are visible.

---

## 9. FOLDER STRUCTURE

```
src/
├── app/
│   ├── App.tsx                  # provider composition
│   ├── router.tsx               # React Router config
│   ├── providers/
│   │   ├── QueryProvider.tsx
│   │   ├── ThemeProvider.tsx
│   │   └── ModeProvider.tsx
│   └── stores/
│       ├── useModeStore.ts
│       ├── useThemeStore.ts
│       ├── useDensityStore.ts
│       └── useNavStore.ts
│
├── routes/
│   ├── index.tsx                # → HomePage
│   ├── recover/
│   │   ├── index.tsx            # → RecoverSpacePage
│   │   ├── safe.tsx
│   │   ├── judgment.tsx
│   │   ├── preview.tsx
│   │   ├── history.tsx
│   │   └── history.$batchId.tsx
│   ├── library/
│   │   ├── index.tsx
│   │   └── $mediaId.tsx
│   ├── health/
│   │   ├── index.tsx
│   │   └── integrations.$integrationId.tsx
│   ├── settings/
│   │   ├── index.tsx            # redirects to integrations
│   │   ├── integrations.tsx
│   │   ├── cleanup-rules.tsx
│   │   ├── notifications.tsx
│   │   ├── appearance.tsx
│   │   ├── mode.tsx
│   │   └── diagnostics.tsx
│   └── first-run/
│       ├── index.tsx
│       ├── step-1.tsx
│       ├── step-2.tsx
│       └── step-3.tsx
│
├── features/
│   ├── home/
│   │   ├── HomePage.tsx
│   │   ├── components/
│   │   │   ├── PrimaryBanner.tsx
│   │   │   ├── StatTileRow.tsx
│   │   │   ├── StatTile.tsx
│   │   │   └── RecentlyAddedSection.tsx
│   │   ├── hooks/
│   │   │   └── useHomeData.ts
│   │   └── types.ts
│   ├── recover/
│   │   ├── RecoverSpacePage.tsx
│   │   ├── SafeCandidateReviewPage.tsx
│   │   ├── PreviewPage.tsx
│   │   ├── ItemJudgmentPage.tsx
│   │   ├── CleanupHistoryPage.tsx
│   │   ├── CleanupBatchDetailPage.tsx
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── reducers/
│   │   │   └── executionReducer.ts
│   │   ├── schemas/
│   │   └── types.ts
│   ├── library/
│   ├── itemDetail/
│   ├── health/
│   ├── integrationDetail/
│   ├── settings/
│   ├── diagnostics/
│   └── firstRun/
│
├── components/
│   ├── foundation/
│   │   ├── Header.tsx
│   │   ├── PrimaryNavigation.tsx
│   │   ├── MobileBottomTabBar.tsx
│   │   ├── ModeChipSlot.tsx
│   │   ├── ExpertChip.tsx
│   │   ├── Button.tsx
│   │   ├── Input.tsx
│   │   ├── StatusBadge.tsx
│   │   ├── Icon.tsx
│   │   ├── Skeleton.tsx
│   │   ├── Spinner.tsx
│   │   └── TopProgressStrip.tsx
│   ├── EvidenceDrawer.tsx
│   ├── ActivityTimeline.tsx
│   ├── StickyActionBar.tsx
│   ├── InlineConfirmationStrip.tsx
│   ├── SuccessStateBanner.tsx
│   ├── ConfirmationModal.tsx
│   └── ItemRow/
│       ├── ItemRowBase.tsx
│       └── index.ts
│
├── hooks/
│   ├── useMode.ts
│   ├── useTheme.ts
│   ├── useMediaQuery.ts
│   ├── useFocusReturn.ts
│   └── useUndoWindow.ts
│
├── api/
│   ├── client.ts
│   ├── errors.ts
│   ├── schemas/
│   ├── cleanupApi.ts
│   ├── libraryApi.ts
│   ├── timelineApi.ts
│   ├── importsApi.ts
│   ├── storageApi.ts
│   ├── validationApi.ts
│   ├── healthApi.ts
│   ├── debugApi.ts
│   ├── recommendationsApi.ts
│   ├── responsibilityApi.ts
│   ├── decisionsApi.ts
│   ├── correlationApi.ts
│   ├── eventsApi.ts
│   ├── tracesApi.ts
│   └── settingsApi.ts
│
├── types/
│   ├── LibraryItem.ts
│   ├── CleanupCandidate.ts
│   ├── Execution.ts
│   ├── Integration.ts
│   ├── MediaTimelineEvent.ts
│   └── index.ts
│
├── lib/
│   ├── formatBytes.ts
│   ├── formatRelativeTime.ts
│   ├── formatAbsoluteTime.ts
│   ├── isUndoWindowOpen.ts
│   ├── cn.ts
│   └── predicates/
│
└── styles/
    ├── tokens.css               # Foundation §2..§7 tokens
    ├── globals.css              # focus-visible global, body defaults
    ├── fonts.css                # Inter Variable + JetBrains Mono
    └── tailwind.config.ts
```

### 9.1 Rationale

- Routes are file-routes for code-split clarity, not a router DSL.
- Features own everything that belongs to one screen. Sprint work touches one feature folder plus the API layer.
- Shared components have a `foundation/` subfolder so the Sprint-1 floor is visible at a glance.
- Schemas live next to their owning API module — wire-shape changes never sprawl.
- `lib/` has zero React imports so it can be unit-tested without DOM setup.

---

## 10. SCREEN OWNERSHIP MATRIX

| Screen | Route owner | Feature owner | API dependencies | Shared components used |
|---|---|---|---|---|
| Home | `routes/index.tsx` | `features/home/` | cleanupApi, validationApi, storageApi, importsApi, debugApi | Header, StatusBadge |
| Recover Space Summary | `routes/recover/index.tsx` | `features/recover/` | cleanupApi | InlineConfirmationStrip, SuccessStateBanner, TopProgressStrip, EvidenceDrawer |
| Safe Candidate Review | `routes/recover/safe.tsx` | `features/recover/` | cleanupApi | StickyActionBar, EvidenceDrawer, ItemRow (Safe variant) |
| Preview | `routes/recover/preview.tsx` | `features/recover/` | cleanupApi | Button (Primary destructive) |
| Item Judgment | `routes/recover/judgment.tsx` | `features/recover/` | cleanupApi | EvidenceDrawer, ItemRow (Risky variant) |
| Cleanup History | `routes/recover/history.tsx` | `features/recover/` | cleanupApi | ItemRow (History variant) |
| Cleanup Batch Detail | `routes/recover/history.$batchId.tsx` | `features/recover/` | cleanupApi | ConfirmationModal (rare) |
| Library | `routes/library/index.tsx` | `features/library/` | libraryApi | StatusBadge, ItemRow (Library variant) |
| Item Detail | `routes/library/$mediaId.tsx` | `features/itemDetail/` | libraryApi, timelineApi, importsApi, cleanupApi | EvidenceDrawer, ActivityTimeline, StatusBadge |
| Health | `routes/health/index.tsx` | `features/health/` | validationApi, debugApi, healthApi | StatusBadge |
| Integration Detail | `routes/health/integrations.$integrationId.tsx` | `features/integrationDetail/` | debugApi, settingsApi | Button, Input |
| Settings (per section) | `routes/settings/*.tsx` | `features/settings/` | settingsApi | ConfirmationModal |
| Diagnostics | `routes/settings/diagnostics.tsx` | `features/diagnostics/` | recommendationsApi, responsibilityApi, decisionsApi, correlationApi, validationApi, eventsApi, tracesApi, debugApi | StatusBadge |
| First Run | `routes/first-run/*.tsx` | `features/firstRun/` | debugApi, settingsApi | Button, Input |

---

## 11. SPRINT MAPPING

Each sprint mirrors the Roadmap §4 sprint. Below, every entry names files/folders the sprint produces — implementation altitude only.

### 11.1 Sprint 1 — Navigation Shell

- **Components built:** all `components/foundation/` entries; `styles/tokens.css`; Tailwind config; theme/mode/density stores; `app/providers/`; route shell with placeholder pages.
- **Routes built:** `/`, `/recover`, `/library`, `/health`, `/settings` (redirect) — each renders a Foundation-compliant empty title.
- **APIs connected:** none.
- **Acceptance criteria:** Roadmap §4 Sprint 1.

### 11.2 Sprint 2 — Home

- **Components built:** `features/home/` (HomePage, PrimaryBanner, StatTileRow, StatTile, RecentlyAddedSection, RecentlyAddedRow); `features/home/hooks/useHomeData.ts`.
- **Routes built:** `/` fully populated.
- **APIs connected:** cleanupApi.getSummary, validationApi.getValidation, storageApi.getStorage, importsApi.listImports, debugApi.getStates (Stat Tile rollup, R-B1).
- **Acceptance criteria:** Roadmap §4 Sprint 2.

### 11.3 Sprint 3 — Recover Space

- **Components built:** `features/recover/*` pages and components; `features/recover/reducers/executionReducer.ts`; `components/InlineConfirmationStrip.tsx`; `components/SuccessStateBanner.tsx`; `components/StickyActionBar.tsx`; `components/EvidenceDrawer.tsx` (stub); ItemRow Safe + Risky variants in `features/recover/components/`.
- **Routes built:** `/recover`, `/recover/safe`, `/recover/preview`, `/recover/judgment`, `/recover/history`, `/recover/history/:batchId`.
- **APIs connected:** cleanupApi (summary, review, review/:id, review/:id/checklist, execute, execute/dry-run, execute/batch, execute/batch-dry-run, executions, action-plan); poll-now.
- **Acceptance criteria:** Roadmap §4 Sprint 3.

### 11.4 Sprint 4 — Library

- **Components built:** `features/library/*`; `features/itemDetail/*`; `components/ActivityTimeline.tsx` (Compact); `components/EvidenceDrawer.tsx` (full body); ItemRow Library variant.
- **Routes built:** `/library`, `/library/:mediaId` (drawer ≥tablet, full-screen mobile).
- **APIs connected:** libraryApi, timelineApi, importsApi (item detail).
- **Acceptance criteria:** Roadmap §4 Sprint 4.

### 11.5 Sprint 5 — Health

- **Components built:** `features/health/*` (HealthSummaryBanner, IntegrationTileGroup, HealthTile, InlineStuckItemsList, RecentIssuesSection); `features/integrationDetail/*`.
- **Routes built:** `/health`, `/health/integrations/:integrationId`.
- **APIs connected:** healthApi (composes debugApi probes), validationApi, debugApi.
- **Acceptance criteria:** Roadmap §4 Sprint 5.

### 11.6 Sprint 6 — Settings

- **Components built:** `features/settings/*`; `components/ConfirmationModal.tsx`; SettingsRow variants (Toggle, Text, ManageLink, ModeToggle); SettingsSectionCard.
- **Routes built:** `/settings/integrations`, `/settings/cleanup-rules`, `/settings/notifications`, `/settings/appearance`, `/settings/mode`. (`/settings/diagnostics` route reserved, body in Sprint 7.) Legacy `/` and `/timeline` redirect to `/` and `/library` respectively.
- **APIs connected:** settingsApi (read-only against existing config; persistence gated by R-B7..R-B11).
- **Acceptance criteria:** Roadmap §4 Sprint 6.

### 11.7 Sprint 7 — Expert Mode

- **Components built:** ExpertChip activation; `features/itemDetail/components/ItemDetailTabStrip.tsx` + Overview/History/SourceTrail/Inspect tab bodies; `components/ActivityTimeline.tsx` Full variant; `features/diagnostics/*` (EngineStatusSection, ReconciliationSection, ValidationReportsSection, LogsSection); `features/library/components/BulkSelectBar.tsx`; KeyboardShortcutHint; confidence Meta on Safe + History rows; Health per-integration history; density-toggle wiring via `data-density="compact"`; dry-run-default behavior toggle.
- **Routes built:** `/settings/diagnostics` populated.
- **APIs connected:** recommendationsApi, responsibilityApi, decisionsApi, correlationApi, eventsApi, tracesApi, additional debugApi endpoints.
- **Acceptance criteria:** Roadmap §4 Sprint 7. No Normal-Mode regressions.

### 11.8 Sprint 8 — Polish

- **Components built:** `features/firstRun/*`; in-app NotificationCenter slot in Header; bottom-sheet variants of InlineConfirmationStrip and EvidenceDrawer for mobile; skeleton coverage on every async surface.
- **Routes built:** `/first-run/step-1`, `/first-run/step-2`, `/first-run/step-3`.
- **APIs connected:** debugApi for Step 2 Test rows; settingsApi stubs for Step 2 Connect (gated by R-B7).
- **Acceptance criteria:** Roadmap §4 Sprint 8.

> No sprint introduces a route, component, or workflow not listed in the locked authorities.

---

## 12. TESTING STRATEGY

### 12.1 Unit testing — Vitest

- Pure functions in `lib/` and Zustand store reducers/selectors.
- Coverage target: 100% for `lib/`, 90% for store logic.
- No DOM, no React, no MSW at this layer.

### 12.2 Component testing — Vitest + React Testing Library

- Every shared component in `components/` ships with a test file.
- Foundation components verify: all five interaction states, focus-visible ring, both modes, ARIA roles per Foundation §11.3.
- Feature components verify: variant rendering (e.g., banner state matrix), event handlers, accessible name/role.
- Tests assert visible text and roles, not implementation details.

### 12.3 Integration testing — Vitest + RTL + MSW

- One integration test per page, covering its happy path against MSW handlers that mirror the backend's existing response shapes.
- Recover Space integration tests cover the execution reducer state machine end-to-end (idle → confirming → executing → succeeded / partial-fail / total-fail).
- Library + Item Detail integration test covers drawer focus return on close.

### 12.4 Accessibility testing — axe-core

- Storybook story-level axe run on every component (Storybook a11y addon).
- Playwright `@axe-core/playwright` run on every page in light + dark + Normal + Expert (where Expert applies).
- Manual screen-reader smoke (NVDA on Windows, VoiceOver on macOS) at Sprint Complete bar per primary surface.

### 12.5 Visual regression testing — Storybook + Chromatic-style

- Snapshot every component variant in both modes.
- Page-level snapshots for each route's default and key states (loading skeleton, idle, error).
- Sprint CI blocks on uncategorized snapshot diffs.

### 12.6 Route testing — Playwright

- One Playwright spec per flow in Blueprint §3 (Flows A–G), executed against the running Vite dev server with MSW mocking the backend.
- Mobile viewport runs assert bottom-tab nav, full-screen Item Detail, bottom-sheet substitutions.

### 12.7 API contract testing

- Zod schemas in `api/schemas/` are the contract. CI runs them against fixture responses captured from the live FastAPI dev server.
- A drift detector fails CI when a captured fixture stops parsing under its schema. Drift is treated as a backend coordination issue, not a frontend bug.

### 12.8 No invented tooling

The above is React ecosystem standard: Vitest, RTL, MSW, Playwright, Storybook, axe-core, Zod. No custom test framework, no novel snapshot system.

---

## 13. RISKS

Implementation risks only. UX / product / scope risks are owned by Roadmap §7.

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| F-1 | Route hierarchy under `/v2` vs eventual `/` graduates inconsistently — bookmarks and inbound links break at Sprint 6. | Medium | Medium | Implement `/v2/*` as a router basename, not as a literal path prefix in components. At graduation, the basename flips to `/` in one config change. |
| F-2 | Drawer focus management regression on Item Detail and Evidence Drawer (most common a11y bug in shadcn stacks). | High | High | `useFocusReturn` hook in Sprint 1; build EvidenceDrawer stub in Sprint 3 to exercise the model early; axe + manual SR test gate every sprint. |
| F-3 | TanStack Query cache staleness on Recover Space after execution — Storage Stat Tile reads stale until next focus. | Medium | Medium | Explicit invalidation rules (§6.4); reducer dispatches `invalidate` on mutation `onSettled`. |
| F-4 | Mobile bottom-tab bar overlaps the StickyActionBar on Safe Candidate Review. | Medium | High | Sticky bar respects safe-area inset and adds the tab-bar height as bottom padding; integration test verifies. |
| F-5 | Large Library list (≥5,000 items) DOM-thrashes on render and on search filter. | Medium | Medium | Virtualization via `@tanstack/react-virtual` on LibraryPage only. Item Detail surface preloads on hover. |
| F-6 | Execution state reducer + TanStack mutation lifecycle duplicate or contradict each other ("am I executing or just loading?"). | Medium | High | Reducer is *driven* by mutation lifecycle, never by independent timers; one source of truth (Query's `isPending`) flows into the reducer. |
| F-7 | Dark/light mode parity drifts as components multiply (a component renders identically in both modes only by accident). | High | Medium | Storybook stories render every component in both modes in CI. Foundation §12.2 parity rule encoded as a snapshot check. |
| F-8 | Tabular-nums regressions in updating numbers (live total on Safe Candidate Review). | Medium | Low | Body-level `font-variant-numeric: tabular-nums`; spot-check in Storybook. |
| F-9 | Inline Confirmation Strip styled like a card (most common UX-fidelity regression). | Low | High | Storybook story explicitly compares strip vs card; PR template checkbox; first PR reviewed against Foundation §9.10 by spec author. |
| F-10 | Skeleton-real divergence causes layout shift on first paint. | Medium | Medium | Skeletons generated from the real component's bounding boxes via a Storybook tool, not hand-authored. |
| F-11 | Settings per-section save state collisions (saving section A blows away unsaved section B). | Low | Medium | One RHF instance per section, no shared form context; integration test covers the cross-section abandonment case. |
| F-12 | Backend gap mitigations (R-B*) silently mature into "feature gaps the frontend forgot about." | High | High | Every gap-disabled action is annotated with a `// R-Bx` comment that grep-CI tracks; a dashboard renders the open gap list at every sprint review. |
| F-13 | Expert Mode bleeds into Normal Mode through ambient enrichments (a confidence number shows up where it shouldn't). | High | High | All Expert surfaces wrapped in `<ExpertOnly>`; component snapshot tests assert Normal-Mode renders contain no Expert-only literals. |
| F-14 | Code-split boundaries set wrong (Diagnostics ships in the Home bundle). | Medium | Low | Route-level lazy imports; bundle analyzer in CI; Diagnostics + Item Detail tabs split out by default. |
| F-15 | Form schema duplication — Zod schema and TypeScript type drift. | Medium | Medium | Types are always `z.infer<typeof schema>`; ESLint blocks parallel interface declarations for form types. |

---

## 14. DEFINITION OF DONE

This DoD inherits every requirement of Roadmap §8 and adds implementation-altitude items the Roadmap explicitly deferred to engineering.

### 14.1 Component Complete

A component is Complete when **all** of the following hold (in addition to Roadmap §8.1 inherited where applicable):

- Lives in the folder its reusability tier demands (§5.3, §9).
- Exposes a single named export plus, where appropriate, named subcomponents — no default exports.
- Props are typed; no `any`, no `unknown` without a runtime guard, no `as` casts.
- Renders identically in light and dark modes (only color tokens swap); verified by Storybook snapshot in both modes.
- All five interaction states (Default / Hover / Focus-visible / Active / Disabled) implemented per Foundation §8.
- Uses only Foundation tokens via Tailwind utilities; no hardcoded colors, sizes, radii, shadows, or motion timings.
- Has a Storybook story per variant.
- Has a component test exercising every variant and every interactive handler.
- axe-core reports zero violations on the story.
- Forbidden Level-4 vocabulary absent (Blueprint §1).
- No new tokens, no new components, no new icons introduced.

### 14.2 Route Complete

A route is Complete when **all** of the following hold:

- Renders the feature's exported page component and only that.
- Is a lazy import boundary unless explicitly listed in the eager-load allowlist (Home, Header).
- Handles its loading state through TanStack Query / Suspense — never a full-page spinner.
- Handles its error boundary with the Foundation §10.1 error state.
- URL params validated through a Zod schema at the route boundary.
- Access gates (e.g., `/settings/diagnostics` Expert-gating) implemented at the route, not deep inside the page.

### 14.3 Feature Complete

A feature is Complete when **all** of the following hold:

- Every page in the feature is Route Complete.
- Every component in the feature is Component Complete.
- Every API hook is implemented in `features/<name>/hooks/` and composes the typed `api/` functions; no `fetch` calls inside the feature.
- View models are colocated and pure; no React state inside transformations.
- Forms (if any) use one RHF instance per save scope with a colocated Zod schema.
- Cross-feature imports are zero (verified by an ESLint boundary rule).
- The screen acceptance criteria from Roadmap §4 for the feature's sprint all pass.
- The feature's Playwright flow (the Blueprint §3 flow it owns) passes in desktop + mobile, light + dark, Normal + Expert (where applicable).

### 14.4 Sprint Complete

A sprint is Complete when **all** of the following hold (inheriting Roadmap §8.2):

- Every Feature in the sprint is Feature Complete.
- Every sprint-level acceptance criterion in Roadmap §4 passes.
- CI passes: type-check, lint, unit, component, integration, route (Playwright), axe, visual regression.
- Bundle analyzer shows the sprint's code lazy-loaded under its route boundary.
- All R-B* backend gaps the sprint touched are annotated in code with `// R-Bx` references.
- No regression in any prior sprint's acceptance criteria.
- Storybook published for every component the sprint shipped.
- The legacy Jinja UI remains functional for surfaces this sprint did not replace (except Sprint 6, which retires it).

### 14.5 Frontend Complete

The frontend is Complete when **all** of the following hold (inheriting Roadmap §8.4):

- All eight sprints are Sprint Complete and all five phases (Roadmap §8.3) are Phase Complete.
- Every Blueprint §4 screen has a route in §4 and a feature folder in §9.
- Every Blueprint §3 flow (A–G) passes Playwright on desktop + mobile, light + dark, Normal + Expert.
- The `/v2` basename has graduated to `/`; legacy `dashboard.html` / `timeline.html` are removed from the repo.
- A grep audit confirms zero Level-4 vocabulary outside `features/diagnostics/` (and only `Engine status` / `Reconciliation` permitted there, per Blueprint v1.1 C4).
- A grep audit confirms zero forbidden patterns: no `cursor-pointer` on non-actionable surfaces, no hardcoded hex colors, no inline `style` props for token-able values.
- The Risk Register (§13) has every F-* risk closed or accepted-with-monitoring.
- R-B* backend gaps are either resolved upstream or documented as known limitations with their user-visible behavior.
- A final accessibility audit against Foundation §11 reports zero open Critical or Serious issues.
- A 24-hour cooling-off pass with a fresh reviewer finds no deviations from the locked UX package.

---

## Closing

This spec exists so engineering can start writing files immediately after Roadmap approval without re-opening any question the locked documents already answered. The discipline mirrors the Roadmap's: **the absence of new engineering decisions during sprints is the feature.** Every sprint should feel like the team is *executing* this spec, not *interpreting* it. When in doubt, the document order in DESIGN_AUTHORITY decides; the Roadmap orders the work; this spec shapes the code. None of them are mutable inside a sprint.
