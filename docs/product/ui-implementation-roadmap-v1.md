# Handoffarr UI Implementation Roadmap — v1
## Frontend Program Plan for the Approved UX Package

> **Status.** This is a planning artifact. It does not redesign, re-architect, re-flow, or rename anything. The locked authority order remains: UX Audit → UX Blueprint v1.1 → Visual Design Foundation v1.1 → UI Reference Mockups v1.1 → DESIGN_AUTHORITY. If this document contradicts any locked artifact, the locked artifact wins.

> **Stack assumption.** React + Tailwind + shadcn/ui, against the existing FastAPI backend (`app/main.py`). No backend changes are assumed; where a screen needs data the backend already exposes, that is noted in §5. Where a screen needs data the backend does *not* yet expose, that is called out as a Risk in §6 (not invented here).

---

## 0. DOCUMENT MAP

1. Implementation Strategy
2. Screen Implementation Order
3. Component Implementation Plan
4. Sprint Plan (Sprints 1–8)
5. Design System Implementation Order
6. API Integration Matrix
7. Risk Assessment
8. Definition of Done

---

## 1. IMPLEMENTATION STRATEGY

### Recommendation: **Incremental, screen-by-screen, behind a route-level flag.**

Not Big Bang. Not parallel-tracks. One screen at a time, in the order specified by §2, with the new frontend living alongside the existing `dashboard.html` / `timeline.html` Jinja surfaces until each screen is replaced.

### Why incremental

1. **The UX package itself is layered.** Blueprint §12 already sequences the work as Phase 1 (Nav + IA) → Phase 2 (Dashboard) → Phase 3 (Recover Space) → Phase 4 (Expert) → Phase 5 (Polish). Foundation §15 mirrors that sequence. A Big Bang would discard the staging the design authority deliberately specified.

2. **Recover Space is the flagship and the riskiest screen.** It owns inline confirmation, live totals, dry-run, execution progress, success-with-Undo, partial-failure, and history. Shipping it inside a Big Bang denies us the ability to ship a calm Home first and let users feel the new product before we ask them to trust it with deletions.

3. **The backend is stable but not all endpoints map cleanly to the new screens.** A screen-at-a-time rollout lets us validate the API matrix (§5) one surface at a time and surface gaps as Risks rather than as launch blockers.

4. **Expert Mode is purely additive.** Per Blueprint §8, Expert never removes or rearranges Normal Mode. That makes Expert a natural late-phase add-on rather than a feature that has to be designed in from day one.

5. **The visual system is designed to look right with very little built.** Foundation §1 ("Quiet by default") means even a navigation shell + a single banner reads as the final product. Big Bang would defer that calm baseline for months; incremental delivers it in Sprint 1.

### Rollout mechanic

- The new frontend mounts at a route prefix (e.g. `/v2`) served alongside the existing Jinja UI.
- Each completed screen flips its route in a single switch (no per-component toggling — that path is forbidden by DESIGN_AUTHORITY's "implementation may not create workflows").
- The legacy UI is retired only when **Sprint 6 (Settings)** lands, because Settings is the last screen any user has reason to visit in the old UI.

### What is explicitly out of scope for this roadmap

- Redesigning anything.
- Adding screens, nav entries, components, or workflows.
- Modifying the backend schema or endpoints.
- Choosing a state library, a router, or a data-fetching library — those are engineering picks below the planning altitude. The roadmap assumes whatever the team picks is compatible with the contract above.

---

## 2. SCREEN IMPLEMENTATION ORDER

The order below is derived from Blueprint §12 + Foundation §15, then expanded to cover every screen and sub-screen in the approved Screen Inventory (Blueprint §4).

| # | Screen | Tier | Sprint | Rationale |
|---|---|---|---|---|
| 1 | **Navigation shell + global header + Mode chip slot** | Foundation | 1 | Every screen mounts inside it. Tokens, header, nav, focus ring, dark/light parity, button/input primitives all live here. |
| 2 | **Home** | Primary | 2 | Highest-leverage screen — every user sees it. Validates the calm-by-default visual language before we touch destructive surfaces. |
| 3 | **Recover Space — Summary** | Primary | 3 | The flagship. Three-section pattern, inline confirmation, success-with-Undo. |
| 4 | **Safe Candidate Review** | Sub | 3 | Path 2 of Flow A. Required to ship Recover Space honestly. |
| 5 | **Preview (dry-run)** | Sub | 3 | Required by Recover Space's inline confirmation strip and by Flow A. |
| 6 | **Risky Candidate Review (Item Judgment)** | Sub | 3 | Flow E. Distinct one-item-at-a-time pattern. |
| 7 | **Cleanup History** | Sub | 3 | Flow F entry point. Reverse-chron list. |
| 8 | **Cleanup Batch Detail** | Sub | 3 | Drill-down from History. Owns Undo-all / Restore-item. |
| 9 | **Library — Recent activity / Search / Browse / Filters** | Primary | 4 | Flow B and Flow C destination. Depends on Item Row primitives finalized in Sprint 3. |
| 10 | **Item Detail (Normal Mode)** | Sub | 4 | Drawer on desktop/tablet, full-screen on mobile. Reached from Library and from Health stuck-items inline list. |
| 11 | **Health — Status summary, Integration list, inline Stuck items, Recent issues** | Primary | 5 | Flow D entry. Depends on Health Tile component (built in Sprint 5). |
| 12 | **Integration Detail** | Sub | 5 | Flow D destination. Test / Reconnect / Edit settings. |
| 13 | **Settings — Integrations, Cleanup rules, Notifications, Appearance, Mode** | Primary | 6 | Lowest user-frequency but unblocks Expert toggle. Retires the legacy UI when done. |
| 14 | **Expert Mode enrichments** (Item Detail tabs, Library bulk-select / §5A, Recover Space confidence + apply-to-similar, Item Judgment §S2 additions, Health per-integration history, density toggle) | Layered | 7 | Additive across already-shipped screens. Cannot start until the Normal Mode surfaces it enriches are stable. |
| 15 | **Diagnostics (Expert sub-screen of Settings)** | Sub | 7 | Only appears when Expert is on. Read-only. |
| 16 | **First Run Experience** | Pre-auth | 8 | Pre-auth, low-traffic, and the only surface where Expert is intentionally absent — perfect Polish-sprint work. |
| 17 | **Polish pass** (empty/idle states, mobile bottom nav + bottom sheets, full-screen drawers, reduced-motion, a11y audit, microcopy review, skeletons, notifications) | Cross-cutting | 8 | Foundation §15 Phase 5 work. Cannot be front-loaded — it tunes what exists. |

### Why this order and not another

- **Home before Recover Space:** Foundation §15 Phase 2 explicitly says "this is the screen the whole visual language is judged by — get it right or redo it." Validating the language on a non-destructive screen is the cheapest way to find tuning issues.
- **Recover Space before Library:** Recover Space depends on no other screen. Library depends on the Item Row primitive that crystallizes during Safe Candidate Review work.
- **Health after Library:** Health's stuck-items inline list per-row `Inspect` navigates to Item Detail (Blueprint §4 Health, v1.1 M4). Item Detail must exist first.
- **Settings last among primaries:** Settings has the lowest visit frequency and the smallest visual surface area. Deferring it lets Sprints 2–5 spend their budget on screens users live in.
- **Expert before First Run:** Expert touches every existing screen; doing it after Polish would invalidate Polish. First Run is genuinely isolated (no header, no nav, no Expert) and is the only screen that can wait until the end.

---

## 3. COMPONENT IMPLEMENTATION PLAN

Every component below is approved by Blueprint §9 + Foundation §9. **No new components.** Grouping is implementation tier, not visual tier.

### 3.1 Foundation tier (Sprint 1)

These ship before any screen and underpin everything.

| Component | Source | Depends on |
|---|---|---|
| Color tokens (neutrals, accent, semantic, light + dark) | Foundation §2 | — |
| Typography tokens (Display / Title / Subtitle / Body / Meta, tabular-nums) | Foundation §3 | — |
| Spacing tokens (`--space-0..8`) | Foundation §4.1 | — |
| Radius + Elevation tokens | Foundation §5 | colors |
| Motion tokens + reduced-motion handling | Foundation §7 | — |
| Global header (56px, wordmark + nav + `[SP]`) | Mockups §1, Foundation §4.2 | tokens |
| Primary nav (5 entries, active state via accent) | Blueprint §2, Foundation §9.1 | header |
| Mobile bottom tab bar (5 entries) | Blueprint §11, Foundation §4.2 | tokens |
| Mode chip slot (`[EXPERT]` placeholder, hidden until Sprint 7) | Foundation §9.15 | header |
| Button — Primary / Secondary / Ghost + size variants (large, default, small) + destructive | Foundation §9.1 | tokens |
| Input | Foundation §9.13 | tokens |
| Status Badge (Imported / Downloading / Stuck / Not found / Queued) | Foundation §9.14 | tokens, icons |
| Icon set (Lucide allowlist per Foundation §6.3) | Foundation §6 | — |
| Focus ring system (`:focus-visible` 2px accent, 2px offset) | Foundation §8 | tokens |
| Skeleton primitive (pulse opacity 0.5→1→0.5) | Foundation §10.2 | tokens |
| Inline spinner + Top progress strip | Foundation §10.2 | tokens |
| Dark/light theme switch wiring (Settings → Appearance hook, but live in Sprint 1) | Foundation §12 | tokens |

### 3.2 Core tier (Sprints 2–4)

Built as their first consuming screen lands.

| Component | First consumer | Sprint |
|---|---|---|
| Primary Banner (Home variant + critical variant + idle variant) | Home | 2 |
| Stat Tile (non-interactive) | Home | 2 |
| Recently added list row (lightweight, non-actionable) | Home | 2 |
| Recommendation Card (Safe / Judgment) | Recover Space Summary | 3 |
| Inline Confirmation Strip | Recover Space Summary | 3 |
| Success State Banner (with Undo + View) | Recover Space Summary | 3 |
| Item Row — Safe Candidate (checkbox, "Why safe?" link, left bar on select) | Safe Candidate Review | 3 |
| Sticky bottom action bar (live total) | Safe Candidate Review | 3 |
| Preview surface (dry-run) | Preview sub-screen | 3 |
| Item Row — Risky (large poster, bulleted reasons, three-equal-weight buttons) | Item Judgment | 3 |
| Item-of-N progress indicator | Item Judgment | 3 |
| Cleanup History list row | Cleanup History | 3 |
| Cleanup Batch Detail row | Cleanup Batch Detail | 3 |
| Filter Chip Row + Sort dropdown | Library | 4 |
| Item Row — Library | Library | 4 |
| Search input (40px Library variant) | Library | 4 |
| Item Detail surface (drawer desktop/tablet, full-screen mobile) | Item Detail | 4 |
| Evidence Drawer (with `Why safe?` / `Why risky?` / `Why?` labels) | Item Detail + Recover Space | 4 (used earlier in stub form by Sprint 3) |
| Activity Timeline — Compact | Item Detail | 4 |

### 3.3 Workflow tier (Sprints 5–6)

| Component | First consumer | Sprint |
|---|---|---|
| Health summary banner | Health | 5 |
| Health Tile (clickable — the documented exception per Foundation §8.1) | Health | 5 |
| Inline Stuck Items list (bounded, paginates in place) | Health | 5 |
| Integration Detail surface (test / reconnect / edit) | Integration Detail | 5 |
| Settings section card | Settings | 6 |
| Settings row patterns (toggle, text, manage-link, mode toggle) | Settings | 6 |
| Confirmation Modal (rare; reserved for catastrophic actions in Settings) | Settings (data reset, integration removal) | 6 |

### 3.4 Expert tier (Sprint 7)

All additive. Each one mounts inside an already-shipped surface.

| Component | Mounts in | Sprint |
|---|---|---|
| `[EXPERT]` chip (activates the existing slot from Sprint 1) | Header | 7 |
| Item Detail tab strip (Overview / History / Source trail / Inspect) | Item Detail | 7 |
| Activity Timeline — Full (Expert-only) | Item Detail History tab | 7 |
| Source Trail surface | Item Detail Source trail tab | 7 |
| Inspect surface (raw IDs, classification confidence, force re-verify, override) | Item Detail Inspect tab | 7 |
| Diagnostics — Engine status section (labels `Engine status` and `Reconciliation` permitted *only* here per Blueprint v1.1 C4) | Diagnostics | 7 |
| Diagnostics — Validation reports section | Diagnostics | 7 |
| Diagnostics — Logs section (mono font, filter, export) | Diagnostics | 7 |
| Bulk-select bar (Library Expert §5A) | Library | 7 |
| "Apply to similar items" action | Safe Candidate Review + Item Judgment | 7 |
| Classification confidence Meta (per-row) | Safe Candidate Review + Cleanup History | 7 |
| Per-integration sync history | Health | 7 |
| Keyboard shortcut hint (`R / K / L`) | Item Judgment | 7 |
| Density toggle (`data-density="compact"`) | Tokens — applied per surface | 7 |
| Dry-run-default toggle behavior (Expert flips destructive defaults to Preview) | Recover Space | 7 |

### 3.5 Dependency graph (read top-to-bottom)

```
Tokens + Header + Nav + Buttons + Inputs + Badges + Icons   (Sprint 1)
        │
        ├── Primary Banner ─ Stat Tile ─ Recently added       (Sprint 2 — Home)
        │
        ├── Recommendation Card ─ Inline Confirm ─ Success    (Sprint 3 — Recover)
        │      │
        │      ├── Item Row (Safe) ─ Sticky action bar         → Safe Candidate Review
        │      ├── Preview surface                             → Preview
        │      ├── Item Row (Risky) ─ Item-of-N                → Item Judgment
        │      └── Cleanup History row ─ Batch Detail row      → History + Batch Detail
        │
        ├── Filter chips ─ Item Row (Library) ─ Search        (Sprint 4 — Library)
        │      └── Item Detail surface ─ Evidence Drawer ─
        │          Activity Timeline (Compact)                 → Item Detail
        │
        ├── Health banner ─ Health Tile ─ Inline Stuck list   (Sprint 5 — Health)
        │      └── Integration Detail surface                  → Integration Detail
        │
        ├── Settings section card ─ Settings rows ─ Modal     (Sprint 6 — Settings)
        │
        ├── [EXPERT] chip ─ Item Detail tabs ─ Timeline (Full)─
        │   Source Trail ─ Inspect ─ Diagnostics sections ─
        │   Bulk-select bar ─ Confidence Meta ─ Density       (Sprint 7 — Expert)
        │
        └── First Run shell ─ Polish across all surfaces      (Sprint 8 — Polish)
```

---

## 4. SPRINT PLAN

Eight sprints, fixed by the prompt. Sprint length is left to the team; the plan is content-based, not calendar-based.

### Sprint 1 — Navigation Shell

**Goal.** Stand up the calm visual baseline and the global chrome so every subsequent sprint mounts inside it.

**Deliverables.**
- Color, typography, spacing, radius, elevation, motion tokens, both modes.
- Global header (56px), primary nav (5 entries), mobile bottom tab bar.
- `[SP]` slot in header (no-op placeholder).
- `[EXPERT]` chip slot in header (hidden — Sprint 7 turns it on).
- Button / Input / Status Badge / Icon / Focus ring / Skeleton / Spinner / Top progress strip primitives.
- Dark/light theme wiring driven by `prefers-color-scheme` with manual override stored locally.
- Route shell with placeholder routes for all five primary screens.

**Dependencies.** None — this is the floor.

**Acceptance criteria.**
- All five primary nav entries reachable, each rendering a Foundation-compliant empty Title placeholder.
- Tab key traverses header → nav → main in reading order; focus ring renders in both modes.
- Dark mode is the default on a fresh install; the override persists across reloads.
- Tokens documented and consumed via CSS custom properties; no hardcoded colors anywhere in app code.
- WCAG AA verified for `--text` on `--bg` in both modes.
- A keyboard-only and screen-reader smoke test passes on the empty shell.

---

### Sprint 2 — Home

**Goal.** Deliver the screen Foundation §15 calls "the screen the whole visual language is judged by."

**Deliverables.**
- Primary Banner with the four states from Blueprint §6: critical / recover / stuck / idle.
- Stat Tile row (Storage / Activity / Health) — three tiles, non-interactive, no cursor change, no hover state.
- Recently added list (5 rows, lightweight, `View →` link in section header).
- Banner state machine driven by the existing backend (see §5).
- Idle/empty state per Foundation §10.1.

**Dependencies.** Sprint 1.

**Acceptance criteria.**
- The single primary CTA on the page is the banner button — no other primary button on screen.
- Stat Tiles have `cursor: default`, do not respond to click, and have no hover affordance (Blueprint v1.1 C1).
- `View →` in the Recently added header is the only Home affordance that navigates to Library; the Storage tile does not.
- Banner state transitions crossfade at `--motion-slow`; banner slot height stays fixed across transitions.
- Idle state renders with no button when nothing requires the user.
- Skeletons cover banner + tiles + list on first load; no full-page spinner.
- Display-headline numeral renders in `--accent` (recover state) or `--critical` (health-critical state); units stay neutral.

---

### Sprint 3 — Recover Space

**Goal.** Ship the flagship workflow end-to-end: Summary → (Safe Review | Preview | Item Judgment) → Execution → Success-with-Undo → History → Batch Detail.

**Deliverables.**
- Recover Space Summary: three-section pattern (Safe / Judgment / Not recommended), Foundation-compliant Recommendation Cards.
- Inline Confirmation Strip on the Safe section's primary button.
- Preview sub-screen (dry-run; full-screen, not modal).
- Safe Candidate Review sub-screen with live total in the sticky action bar.
- Item Judgment sub-screen (one-at-a-time, three equal-weight buttons, `Why risky?` link).
- Evidence Drawer (stub — full body content can defer to Sprint 4 polish; trigger labels must be correct now: `Why safe?` / `Why risky?` / `Why?`).
- Top progress strip during execution; Success Banner with `[Undo (24h)]` + `[View what was removed]`.
- Cleanup History sub-screen and Cleanup Batch Detail sub-screen with per-batch and per-item Undo.
- Partial-failure and total-failure execution sub-states per Blueprint §7 "Execution sub-states."

**Dependencies.** Sprint 1, Sprint 2 (Recommendation Card pattern leans on the banner's visual rhythm).

**Acceptance criteria.**
- The user can complete Flow A Path 1 (trust the system) and Flow A Path 2 (Review / Preview) without leaving the Recover Space surface, except where the flow itself navigates.
- Live total updates the primary button text in real time as items are checked/unchecked.
- Inline confirmation is a flush strip, not a modal.
- Risky items are *never* presented as bulk-selectable in the same surface as safe items (Blueprint §7 Rule 7).
- Success Banner replaces — not stacks below — the section it acted on.
- After the configured Undo window expires (default 24h), the Success Banner converts to a Meta-level inline note with no buttons.
- Empty state renders as the idle success message specified in Blueprint §7 Rule 8.
- Cleanup Batch Detail supports both `Undo all` and per-row `Restore item` while in window; both grey out when out of window.

---

### Sprint 4 — Library

**Goal.** Ship the find-and-inspect surface and the Item Detail it leads to. Promote the Evidence Drawer from stub to full implementation.

**Deliverables.**
- Library screen: search bar, Filter Chip Row, sort dropdown, list of Library Item Rows with Status Badges.
- Pagination ("Load more" pattern from Mockups §5).
- Item Detail surface — drawer on desktop/tablet, full-screen route on mobile.
- Activity Timeline (Compact) in Item Detail.
- Evidence Drawer full implementation (`Why?` generic label in this context).
- Item Detail contextual primary action wiring (Verify / Remove / View in Health / Open in *arr).

**Dependencies.** Sprint 3 (Item Row pattern crystallized during Safe Candidate work).

**Acceptance criteria.**
- Search filters instantly without a submit step.
- Filter chips are single-select; sort dropdown is on the far right.
- Library is a list of cards on mobile, never a table (Blueprint §11).
- Item Detail opens as a side drawer at ≥ tablet width and as a full-screen route on mobile, with focus moved to the drawer/route title and Esc returning focus to the trigger.
- Stuck items in Library link to Health (per Flow C).
- All Status Badges include both icon and label (no color-only badges).
- Hover state on Library rows is `--surface-raised`; entire row is the click target.

---

### Sprint 5 — Health

**Goal.** Ship the "surface problems" surface and the one place users go to fix an integration.

**Deliverables.**
- Health screen: status summary banner, Integration Tile group (Health Tile component), inline Stuck Items list (no separate screen — v1.1 M4), Recent issues.
- Integration Detail sub-screen with `Test connection`, `Reconnect`, `Edit settings` (and `View logs` slot for Expert in Sprint 7).
- Per-row `Inspect` on stuck items navigates to Item Detail with the stuck-state variant (Mockups §6).
- Health Tile is the documented exception to "Cards summarize. Buttons navigate." — clickable, cursor `pointer`, visible hover state.

**Dependencies.** Sprint 4 (Item Detail).

**Acceptance criteria.**
- Broken integrations dominate visually; healthy integrations recede via `--text-muted` in the right column.
- The Stuck Items section header has **no** `View →` link (v1.1 M4).
- If the stuck-items list exceeds ~10, the list paginates *within Health* — it does not promote to a dedicated screen.
- Integration Detail's `Test connection` reports success/failure with plain-language hints, not raw stack traces (raw goes to Diagnostics).
- The health-critical Home banner state (Sprint 2) links to Health with the correct integration row in view.

---

### Sprint 6 — Settings

**Goal.** Ship the configuration surface and retire the legacy UI.

**Deliverables.**
- Settings screen sections: Integrations, Cleanup rules, Notifications, Appearance (theme, density), Mode (Normal / Expert toggle).
- Per-section save model.
- Manage-list pattern for Excluded items.
- Confirmation Modal pattern available for catastrophic actions (data reset, integration removal with data loss). Reserved use only.
- Mode toggle wiring — flipping it sets the per-user preference but Expert surfaces are still hidden (Sprint 7 lights them up).
- Legacy `/` (dashboard.html) and `/timeline` (timeline.html) routes redirected to their v2 equivalents; legacy templates kept in the repo until Sprint 7 ships but no longer linked.

**Dependencies.** Sprints 1–5 (all primary surfaces must exist before retiring the legacy UI).

**Acceptance criteria.**
- Every section saves independently; abandoning a section does not lose other sections' edits.
- Mode toggle's supporting copy matches Mockups §8 ("Shows diagnostics, lifecycle history, and source trails.").
- Confirmation Modal is used only where Foundation §9.11 permits.
- All forbidden Level-4 terminology stays out of Normal-Mode Settings; the narrow Expert-only labels `Engine status` and `Reconciliation` do not appear here (they live only in Diagnostics, per v1.1 C4).

---

### Sprint 7 — Expert Mode

**Goal.** Light up Expert across already-shipped surfaces. Additive only — no Normal-Mode regressions.

**Deliverables.**
- `[EXPERT]` chip becomes visible when Mode is on.
- Item Detail tab strip: Overview / History / Source trail / Inspect.
- Activity Timeline (Full); Source Trail surface; Inspect surface with raw IDs, classification confidence, force re-verify, override classification.
- Diagnostics sub-screen of Settings: Engine status, Validation reports, Logs (mono font, filter, export).
- Recover Space Expert enrichments: classification confidence Meta on safe rows; "Apply to similar items" bulk action on Safe Candidate Review (when ≥3 items share rule attribution); Item Judgment lifecycle timeline visible by default and "Apply to similar items" action; `R / K / L` keyboard shortcut hint at bottom of Item Judgment.
- Library Expert variant (Mockups §5A): bulk select with checkboxes, sticky bulk-action bar (`Flag for cleanup`, `Remove from library` — both gated by inline confirmation), additional sort options.
- Health Expert enrichments: per-integration sync history, validation summary inline, link to Diagnostics filtered to integration.
- Density toggle wired via `data-density="compact"` on Expert-active surfaces.
- Recover Space dry-run-default behavior (Expert flips destructive defaults to Preview per Blueprint §8.4).
- Timestamps switch from relative to absolute in Item Detail History under Expert.

**Dependencies.** Sprints 2–6 (each enrichment mounts inside an existing surface).

**Acceptance criteria.**
- Toggling Expert off must restore the exact Normal-Mode behavior of every screen — no residual chips, tabs, or bulk bars.
- The labels `Correlation Engine`, `Responsibility Attribution`, `Lifecycle Engine`, `Attribution`, etc., do not appear on any Expert surface (Blueprint §1 Level 4 rule).
- The labels `Engine status` and `Reconciliation` appear **only** in Settings → Diagnostics — nowhere else, including under Expert (v1.1 C4).
- `R / K / L` shortcuts only fire when Expert is on and Item Judgment is the focused surface.
- Bulk-select on Library is gated behind inline confirmation for destructive operations.
- No new design tokens were added; Expert reuses everything from Sprints 1–6.

---

### Sprint 8 — Polish

**Goal.** Convert "working redesign" into "product people recommend" (Foundation §15 Phase 5).

**Deliverables.**
- First Run Experience (Flow G, Mockups §10): 3-step pre-auth flow, no global header, no nav, no Expert.
- Empty/idle state pass across every screen (Foundation §10.1).
- Mobile pass across every screen: bottom nav active state, bottom sheets replace inline confirmation strips, full-screen Item Detail, single-column risky judgment with stacked buttons.
- Accessibility audit against Foundation §11: focus order, contrast, ARIA on banner / progress / `[EXPERT]` chip / status badges, drawer focus trap + restore, Esc handling.
- Reduced-motion audit (Foundation §7.4).
- Microcopy review against Audit terminology rewrite + Foundation §13.
- Skeleton coverage on every async surface; no full-page spinners anywhere.
- In-app notification surface for cleanup recommendations and integration failures (per Settings → Notifications).
- Performance: optimistic UI on Recover actions where Undo backs out failures.

**Dependencies.** All prior sprints.

**Acceptance criteria.**
- First Run completes both the "configured" exit and the "skipped" exit and lands the user on Home in both cases; Health correctly surfaces any absent integrations after the skip path.
- Every empty state matches §10.1: centered, max 360px, `check-circle` in `--success`, calm copy, optional single Ghost button.
- Every async surface shows a skeleton — never a spinner taking over the page.
- All Foundation §11 contrast targets pass automated and manual audit.
- Bottom sheets on mobile respect safe-area inset; full-screen drawers on mobile have a clear back affordance.
- Sentence-case enforced site-wide; no trailing periods on buttons or labels; non-breaking space between numbers and units; tabular-nums on every numeric Meta surface.

---

## 5. DESIGN SYSTEM IMPLEMENTATION ORDER

Each row is built once and reused forever. Order chosen so later rows can lean on earlier rows without rework.

| Order | Layer | Concrete deliverables | Sprint |
|---|---|---|---|
| 1 | **Color tokens** | All neutrals, accent, success/caution/critical (strong + quiet) in light + dark, exported as CSS custom properties + `tokens.json` mirror | 1 |
| 2 | **Typography** | Inter Variable + JetBrains Mono fonts loaded; five-level scale (Display / Title / Subtitle / Body / Meta) wired as utility classes; `font-variant-numeric: tabular-nums` global default | 1 |
| 3 | **Spacing** | `--space-0..8` tokens, page max-width 960px, gutter 32/16, header 56px, bottom nav 64px | 1 |
| 4 | **Radius + elevation** | Four radii (sm / md / lg / pill), three elevations (1 / 2 / 3) with dark-mode top-highlight override | 1 |
| 5 | **Motion** | Three timings + ease tokens, `prefers-reduced-motion` collapse to 0.01ms, loader replacement | 1 |
| 6 | **Buttons** | Primary / Secondary / Ghost + size variants + destructive | 1 |
| 7 | **Inputs** | 36px default, 40px Library search variant, focus = 2px accent border (no offset) | 1 |
| 8 | **Status Badge** | All five variants (Imported / Downloading / Stuck / Not found / Queued), icon + label always | 1 |
| 9 | **Cards** | Cards land per-screen, not as a generic primitive — each card type (Primary Banner, Stat Tile, Recommendation Card, Health Tile, Settings section, Cleanup History row) has its own anatomy. Card *tokens* (padding 24/16, radius `--radius-lg`, elevation per type) are codified in Sprint 1; instances ship in their owning sprint | 2 → 6 |
| 10 | **Tables** | Handoffarr uses **lists, not tables**, in Normal Mode (Foundation §10 Table philosophy). Diagnostics → Logs is the only table-shaped surface and ships in Sprint 7. Sticky header / sortable column / row-menu pattern is built once, there. | 7 |

### Card landing schedule (item 9 expanded)

| Card | Sprint | Anatomy source |
|---|---|---|
| Primary Banner | 2 | Foundation §9.2 |
| Stat Tile | 2 | Foundation §9.3 |
| Recommendation Card | 3 | Foundation §9.4 |
| Success State Banner | 3 | Foundation §9.12 |
| Item Detail surface card | 4 | Mockups §6 |
| Health Tile | 5 | Foundation §9.8 |
| Settings section card | 6 | Mockups §8 |

### Button rollout

All three variants ship in Sprint 1. Size variants (large for banner, small for list rows) ship with their first consumer. Destructive Primary first appears in Sprint 3 (Recover Space) and again in Sprint 6 (Settings catastrophic-action modal).

---

## 6. API INTEGRATION MATRIX

Mapping every approved screen to existing backend endpoints in `app/main.py`. **No endpoints are invented.** Where the UX-required data is not currently exposed by an existing endpoint, the cell reads "(no current endpoint — see Risk R-Bx)" and is tracked in §7.

| Screen | Component | Endpoint | Purpose |
|---|---|---|---|
| Home | Primary Banner (recover state) | `GET /api/cleanup` | Recoverable total + safe-item count for the headline |
| Home | Primary Banner (critical state) | `GET /api/validation` | Surfaces system-wide validation issues |
| Home | Stat Tile — Storage | `GET /api/storage` | Free space / total |
| Home | Stat Tile — Activity | `GET /api/imports` | Imports-this-week count (filter client-side) |
| Home | Stat Tile — Health | `GET /api/validation` | Aggregate health roll-up; supplement with `GET /api/debug/states` for integration reachability if needed (Expert-only data path may require Risk R-B1) |
| Home | Recently added list | `GET /api/imports` | Latest 5 imports |
| Recover Space — Summary | Recommendation Card (Safe / Judgment / Not recommended) | `GET /api/cleanup`, `GET /api/cleanup/action-plan` | Section counts and totals; action plan structure |
| Recover Space — Summary | Inline Confirmation Strip → execution | `POST /api/cleanup/execute` | Live execution |
| Recover Space — Summary | Inline Confirmation Strip → preview | `POST /api/cleanup/execute/dry-run` | Dry-run |
| Recover Space — Summary | "Run a check now" (idle state) | `POST /api/poll-now` | Manual refresh |
| Safe Candidate Review | Item rows | `GET /api/cleanup/review` | Candidate list with safety metadata |
| Safe Candidate Review | "Why safe?" Evidence Drawer body | `GET /api/cleanup/review/{media_id}` + `GET /api/cleanup/review/{media_id}/checklist` | Per-item evidence |
| Safe Candidate Review | Sticky action bar `[Recover X GB]` | `POST /api/cleanup/execute/batch` | Selected-batch execution |
| Safe Candidate Review | Sticky action bar live-total preview | `POST /api/cleanup/execute/batch-dry-run` | Selection-aware total |
| Preview | Scope summary | `POST /api/cleanup/execute/dry-run` (or `batch-dry-run` if scoped) | Files / free-space delta / per-integration projection |
| Preview | `[Proceed and recover X GB]` | `POST /api/cleanup/execute` (or batch variant) | Live execution |
| Risky Candidate Review (Item Judgment) | Item card | `GET /api/cleanup/review?risky=true` (filtered consumer of `GET /api/cleanup/review`) | One-at-a-time iteration |
| Risky Candidate Review | "Why risky?" Evidence Drawer | `GET /api/cleanup/review/{media_id}` | Per-item evidence |
| Risky Candidate Review | Remove / Keep / Later | `POST /api/cleanup/execute` for Remove; (no current endpoint — see Risk R-B2 for Keep / Later state persistence) | Decision capture |
| Cleanup History | Per-batch list | `GET /api/cleanup/executions` | Reverse-chronological batches |
| Cleanup History | Per-batch action-plan link | `GET /api/cleanup/action-plan.txt` | Plain text export |
| Cleanup Batch Detail | Per-item rows | `GET /api/cleanup/executions` (filtered to one execution; per-item drill-down may need Risk R-B3) | Items in batch |
| Cleanup Batch Detail | `Undo all` / `Restore item` | (no current endpoint — see Risk R-B4) | Reversibility within Undo window |
| Library | Item list | `GET /api/library` | Browse list |
| Library | Filter chips | `GET /api/library` (client-side filter on type/status) | Quick filter |
| Library | Search | `GET /api/library` (client-side filter; server-side search would be Risk R-B5) | Title search |
| Item Detail | Header (poster, title, size, status) | `GET /api/library/{media_id}` | Item summary |
| Item Detail | Recent activity (Compact Timeline) | `GET /api/timeline/{media_id}` | Last N events |
| Item Detail | Status badge derivations | `GET /api/imports/{media_id}` | Import / download state |
| Item Detail | "Flag for cleanup" | `GET /api/cleanup/{media_id}` (current) → action would need write endpoint (Risk R-B6) | Manual flag |
| Item Detail | "Remove from library" | `POST /api/cleanup/execute` (single-item scope) | Removal |
| Health | Status summary banner | `GET /api/validation` + `GET /api/debug/states` | Aggregate state |
| Health | Integration Tiles | `GET /api/debug/states` + `GET /api/debug/radarr` / `GET /api/debug/qbit` / `GET /api/debug/seerr` | Per-integration reachability |
| Health | Inline Stuck Items | `GET /api/imports` (filter "stuck") or `GET /api/debug/queue` | Stuck-item surface |
| Health | Recent issues | `GET /api/validation` | Issue list |
| Integration Detail | Status / last contact | `GET /api/debug/radarr` / `GET /api/debug/qbit` / `GET /api/debug/seerr` | Integration probe |
| Integration Detail | `Test connection` | Re-call the relevant `GET /api/debug/*` endpoint | Live probe |
| Integration Detail | `Edit settings` save | (no current endpoint — see Risk R-B7) | Persist integration credentials |
| Integration Detail | `View logs` (Expert) | (no current endpoint — see Risk R-B8) | Per-integration logs |
| Settings — Integrations | Read | Existing config endpoints — (currently file-based per `config.example.yaml`; no current edit endpoint — see Risk R-B7) | Read/write integrations |
| Settings — Cleanup rules | Read / write | (no current endpoint — see Risk R-B9) | Rules persistence |
| Settings — Notifications | Read / write | (no current endpoint — see Risk R-B10) | Notification prefs |
| Settings — Appearance | Read / write | Client-side only (theme / density) | Local pref |
| Settings — Mode | Read / write | Client-side only initially; multi-device sync is Risk R-B11 | Expert toggle |
| Diagnostics — Engine status | Last-run + re-run | `GET /api/recommendations`, `GET /api/responsibility`, `GET /api/decisions`, `GET /api/correlation` (per `app/correlation.py`), `POST /api/poll-now` for re-run | Engine surfaces |
| Diagnostics — Validation reports | List | `GET /api/validation` | Reports |
| Diagnostics — Validation reports | Per-report drill-down | `GET /api/debug/library`, `GET /api/debug/imports`, `GET /api/debug/correlation` | Details |
| Diagnostics — Logs | Feed + filter + export | `GET /api/events`, `GET /api/traces`, `GET /api/debug/export` | Log surfaces |
| Item Detail — History (Expert) | Full timeline | `GET /api/timeline/{media_id}` | Full event history |
| Item Detail — Source trail (Expert) | Cross-ref state | `GET /api/responsibility/{assessment_id}`, `GET /api/debug/correlation`, `GET /api/debug/torrent/{torrent_hash}` | Cross-system trail |
| Item Detail — Inspect (Expert) | Raw IDs + override | `GET /api/decisions/{media_id}`, `GET /api/responsibility/{assessment_id}`; "force re-verify" via `POST /api/poll-now`; "override classification" is Risk R-B12 | Engine inspection |
| First Run — Step 2 Connect | Per-row Test | `GET /api/debug/radarr` / `GET /api/debug/qbit` / `GET /api/debug/seerr` | Live probe |
| First Run — Step 2 Connect | Per-row Connect (save) | (no current endpoint — see Risk R-B7) | Save credentials |

---

## 7. RISK ASSESSMENT

### 7.1 Implementation risks (the frontend's own work)

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-I1 | Drawer focus management (focus trap, return-on-close) is consistently the first accessibility regression in shadcn-based stacks. | Medium | High | Build the Evidence Drawer in Sprint 3 (stub) so the focus model is exercised early; full Sprint 8 a11y audit re-tests every drawer. |
| R-I2 | The Sticky bottom action bar on Safe Candidate Review will fight mobile keyboards on inputs (there are none today, but Search and Edit settings introduce them). | Low | Medium | The bar lives only on Safe Candidate Review, which has no inputs. Guard with explicit `inert` rules so it never coexists with a focused input on mobile. |
| R-I3 | Live total recomputation on every checkbox toggle can churn the DOM on large safe lists. | Medium | Low | Memoize selection state; only re-render the bar's number text, not the row list. |
| R-I4 | Dark-mode parity drift as components multiply. | Medium | Medium | Foundation §12.2 parity rule is encoded as a lint / Storybook check: every component renders both modes in CI snapshot. |
| R-I5 | Tabular-nums regressions (numbers shifting width during updates) — easy to miss in review. | Medium | Low | Set `font-variant-numeric: tabular-nums` at the body level, not per-component. |
| R-I6 | Inline confirmation strip is easy to mistake visually for a card; risks the strip being styled into a modal. | Low | High | Reference Mockups §2 explicitly; review the strip's first PR against Foundation §9.10 ("not a card — a flush horizontal strip"). |
| R-I7 | Skeletons drift from final layout (skeleton-real divergence is the most common cause of layout shift). | Medium | Medium | Skeletons are generated from the real component's bounding box, not hand-authored shapes. |
| R-I8 | Routing the legacy UI and v2 UI in parallel creates a window where session state can split. | Medium | Medium | Settings → Mode and Appearance live client-side until Sprint 6; nothing else is per-user state during the parallel window. |

### 7.2 UX drift risks (the design authority erodes)

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-U1 | Implementation engineer reaches for a fifth semantic color, fourth elevation, or sixth type size to "make this one screen work." | Medium | High | Foundation §2.5 and §3.2 are explicit. PR template includes a checkbox: "No new tokens introduced." Any new token requires a Foundation amendment. |
| R-U2 | Engine terminology leaks into Normal Mode through tooltip text, ARIA labels, or error copy ("Correlation engine returned…"). | High | High | Microcopy review (Sprint 8) is binding, but enforced earlier via grep CI for the forbidden vocabulary list (Blueprint §1 Level 4). |
| R-U3 | Stat Tiles or Health Tiles get clickable behavior added because "users will expect it." | High | Medium | The "Cards summarize. Buttons navigate." rule (Blueprint v1.1 C1, Foundation §8.1) is wired into the Stat Tile component as `cursor: default` with no `onClick` prop accepted. Health Tile is the explicit, documented exception. |
| R-U4 | Risky and safe items get bundled in a single "Remove all" action because a stakeholder asks. | Medium | High | Blueprint §7 Rule 7 is non-negotiable. Any such request is rejected with a pointer to that rule. |
| R-U5 | The `Why? Details` label resurfaces. | Low | Low | grep CI guard for the literal `Why? Details`. |
| R-U6 | Modal proliferation (modals used for routine destructive actions instead of inline strips). | Medium | High | Confirmation Modal ships only in Sprint 6 and only as a primitive reserved per Foundation §9.11. Code review checks every modal call site against that list. |
| R-U7 | Expert Mode bleeds into Normal Mode through ambient enrichments (a confidence number "just helps everyone"). | High | Medium | Expert surfaces are gated by a single Mode flag at render time. Snapshot tests assert Normal-Mode renders match the Mockups byte-for-DOM-tree. |
| R-U8 | Forbidden Level-4 labels (`Engine status`, `Reconciliation`) leak outside Diagnostics. | Low | High | grep CI scopes those literals to `app/<diagnostics path>` only. Failing match outside that scope fails CI. |

### 7.3 Scope creep risks (the work expands)

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-S1 | "While we're in here" additions during sprint work (new metrics on Home, new sort options on Library, a chart somewhere). | High | High | DESIGN_AUTHORITY rule: "Implementation may not create screens, navigation entries, or workflows." Adding a new component, metric, or affordance requires a Blueprint amendment, not a PR description. |
| R-S2 | Backend gaps (Risks R-B1..R-B12 in §5) get fixed inline with frontend work, expanding sprint scope. | High | High | Each backend gap is filed as a separate ticket and triaged outside the sprint. Frontend ships against the existing endpoints; gaps become Sprint 8 Polish work or are deferred. |
| R-S3 | First Run gets re-scoped from "3-step pre-auth" to "guided tour of everything." | Medium | Medium | Flow G is locked. First Run is exactly Steps 1–3 from Mockups §10. |
| R-S4 | Expert Mode expands to include surfaces the Blueprint did not approve (e.g., a "manual rule editor" beyond the Settings Cleanup rules section). | Medium | Medium | Sprint 7 deliverables list is exhaustive. Anything outside it goes to a Blueprint amendment request. |
| R-S5 | Polish sprint becomes a second redesign pass. | High | Medium | Sprint 8 deliverables are bound to Foundation §15 Phase 5. New behaviors require new Blueprint/Foundation entries first. |
| R-S6 | Stuck items get promoted to a dedicated screen "to make pagination easier." | Low | High | Blueprint v1.1 M4 is explicit. Stuck items stay inline on Health; pagination happens in place. |

### 7.4 Backend gaps surfaced by the API matrix

These are not new requirements — they are the existing-API gaps the matrix surfaced. None are in scope for this roadmap to *resolve*; all are tracked here so the frontend plan does not silently assume them.

| ID | Gap | Frontend impact | Triage owner |
|---|---|---|---|
| R-B1 | Aggregate health roll-up for Home Stat Tile | Stat Tile shows derived rollup from `/api/validation` until a dedicated endpoint exists | Backend |
| R-B2 | Persist Keep / Later decisions on risky items | Item Judgment writes intent client-side until endpoint exists; reverts on reload | Backend |
| R-B3 | Per-item drill into a single cleanup execution | Cleanup Batch Detail uses the full executions response and filters client-side | Backend |
| R-B4 | Undo / Restore endpoints | Undo button is shipped as visually-correct but disabled until endpoint lands; Success Banner copy adjusts accordingly | Backend |
| R-B5 | Server-side Library search | Client-side title filter only in Sprint 4; graceful behavior on large libraries | Backend |
| R-B6 | "Flag for cleanup" write | Action hidden in Normal Mode until endpoint exists | Backend |
| R-B7 | Integration credential save | First Run Step 2 `Connect` and Integration Detail `Edit settings` rendered read-only until endpoint exists | Backend |
| R-B8 | Per-integration log endpoint | `View logs` link (Expert) absent until endpoint exists | Backend |
| R-B9 | Cleanup rules persistence | Settings → Cleanup rules read-only until endpoint exists | Backend |
| R-B10 | Notification preferences persistence | Settings → Notifications read-only until endpoint exists | Backend |
| R-B11 | Server-side Mode preference | Mode flag is per-device until endpoint exists | Backend |
| R-B12 | Override classification | Inspect tab's `Override classification` button absent until endpoint exists | Backend |

---

## 8. DEFINITION OF DONE

Four altitudes. Each higher bar inherits every lower bar.

### 8.1 Screen Complete

A screen is Complete when **all** of the following hold:

- Matches its Mockup at the structural level (sections, ordering, primary action placement, presence of secondary affordances).
- Renders every state defined for it in the Blueprint and Foundation: default, loading (skeleton), empty/idle, error, success-after-action. Recover Space additionally renders confirming, executing, succeeded, partial-fail, and total-fail.
- Uses only Foundation tokens — no hardcoded colors, sizes, radii, or shadows.
- Uses only the components specified in §3 for its sprint.
- Renders identically in structure across light and dark modes (only color tokens swap).
- All five interaction states (Default / Hover / Focus-visible / Active / Disabled) defined per Foundation §8 on every interactive element.
- Focus ring is `:focus-visible`, 2px accent, 2px offset; never removed.
- Keyboard reachable end-to-end; tab order = reading order; Esc closes drawers/sheets/modals; focus restores to trigger on close.
- All status indicators carry both icon and label (no color-only signals).
- Tabular-nums on every numeric Meta surface.
- Microcopy obeys Foundation §13 (sentence case, no trailing periods on buttons, non-breaking space between number and unit, single decimal on sizes).
- Forbidden Level-4 vocabulary (`Correlation`, `Lifecycle`, `Attribution`, `Validation`, `Diagnostics`, `Reconciliation`, `Engine`) does not appear, with the narrow Diagnostics carve-out for `Engine status` and `Reconciliation`.
- No new components, no new tokens, no new navigation entries, no new workflows introduced.
- ARIA roles match Foundation §11.3 for the screen's component vocabulary.
- Skeletons match the real layout's bounding boxes — no layout shift on first paint.
- WCAG AA met for body text; AAA for `--text` on `--bg`.
- Sprint acceptance criteria for this screen all pass.

### 8.2 Sprint Complete

A sprint is Complete when **all** of the following hold:

- Every Screen Complete in the sprint passes its bar.
- Every sprint-level acceptance criterion in §4 passes.
- The sprint's components are exported from a single library entry point and consumed only through it.
- Storybook (or equivalent) entries exist for every component the sprint shipped, with both modes and every interaction state.
- CI lint passes: no new tokens, no forbidden vocabulary outside permitted scopes, no hardcoded colors, no `cursor: pointer` on non-actionable surfaces.
- Snapshot tests pass for every component in both modes.
- A keyboard-only smoke test and a screen-reader smoke test pass on the sprint's primary surface.
- Reduced-motion render verified.
- Mobile layout for the sprint's surface renders correctly (single-column, bottom sheet substitutions where applicable, full-screen Item Detail on mobile from Sprint 4).
- No regressions in earlier sprints' acceptance criteria.
- The API matrix entries for the sprint's screens are wired or explicitly disabled with the corresponding Risk-B reference visible in code comments.

### 8.3 Phase Complete

Phases map to Blueprint §12 / Foundation §15 phase boundaries:

- **Phase 1 (Sprint 1).** Navigation Shell shipped. Calm baseline visible.
- **Phase 2 (Sprint 2).** Home shipped. The whole product's visual language is now judged on a real screen.
- **Phase 3 (Sprints 3–6).** Every primary screen shipped. Legacy UI retired.
- **Phase 4 (Sprint 7).** Expert Mode lit up. No Normal-Mode regressions.
- **Phase 5 (Sprint 8).** First Run live. Polish bar met across every screen.

A phase is Complete when:

- Every sprint inside it is Sprint Complete.
- An end-to-end pass of the user flows the phase enables (Blueprint §3) runs successfully on desktop and mobile, in both light and dark modes, in both Normal and (for Phase 4+) Expert Mode.
- Foundation parity holds: every screen looks like it belongs to the same product.
- The DESIGN_AUTHORITY rules ("may not modify IA / create screens / add nav / create workflows") have not been violated. Any pressure to do so during the phase is logged for retro, not for action.

### 8.4 Product Complete

The frontend implementation is Product Complete when:

- All eight sprints are Sprint Complete and all five phases are Phase Complete.
- Every screen in Blueprint §4 Screen Inventory exists and renders per Mockups.
- Every flow in Blueprint §3 (A through G) runs end-to-end without falling back to the legacy UI.
- The legacy `dashboard.html` / `timeline.html` routes have been removed from the repo and the Jinja templates archived.
- A full audit pass against the four locked documents (Audit / Blueprint v1.1 / Foundation v1.1 / Mockups v1.1) finds no deviations.
- The Charter (Audit §10 terminology rewrite + Blueprint §1 Level rules) is upheld site-wide.
- The Risk Register (§7) has every Implementation and UX-drift risk closed; Scope-creep risks are accepted-and-monitored; Backend-gap risks (R-B*) are either resolved by backend or documented as known limitations with their user-visible behavior.
- The product passes a final accessibility audit against Foundation §11 with zero open Critical or Serious issues.
- A 24-hour cooling-off pass with a fresh reviewer finds nothing that contradicts the locked documents.

---

## Closing

This roadmap exists so the implementation team can move quickly without re-opening any of the questions the locked documents already answered. The discipline is the same as Foundation's closing line: **the absence of new design decisions is the feature.** Every sprint should feel like the team is *executing* the design package, not *interpreting* it. When in doubt, the document order in DESIGN_AUTHORITY decides — and this roadmap silently defers to all four of them.
