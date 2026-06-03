# Handoffarr Phase 2 Blueprint — v1.1
## Complete Product Architecture & Wireframe Package

> **v1.1 reconciliation note.** This revision resolves the consistency audit findings C1, C2, M1–M6, S1–S3, T1, and C4. No workflows were redesigned, no features added, no design tokens changed, no nav entries added. Changes are limited to: promoting in-flow surfaces to formally-named screens, adding missing screen entries to Site Map / Screen Inventory / Flows, standardizing the evidence-drawer link label, and narrowly carving out Expert-Diagnostics terminology. See §0 Change Log.

---

## 0. CHANGE LOG (v1 → v1.1)

| ID | Change | Sections touched |
|---|---|---|
| C1 | Flow B no longer treats Home Stat Tiles as clickable. Navigation occurs via an explicit `View Library` link in the Recently added header (already in mockups) and via the nav bar. Principle added to §10 Design System: *"Cards summarize. Buttons navigate."* | §3 Flow B, §10 |
| C2 | Safe Candidate Review promoted from inline expansion to a formal sub-screen of Recover Space. Added to Site Map, Screen Inventory, and Flow A (Path 2). Mockups §3 retained as the authoritative visual. | §2, §3 Flow A, §4 |
| M1 | Integration Detail added to Site Map and Screen Inventory; already referenced by Flow D. | §2, §4 |
| M2 | Cleanup History promoted to a formal sub-screen of Recover Space. Added to Site Map and Screen Inventory; already referenced by Flow F. | §2, §4 |
| M3 | Preview (dry-run) promoted to a formal sub-screen of Recover Space. Added to Site Map and Screen Inventory; already referenced by Flow A and §7. | §2, §4 |
| M4 | Stuck Items remain **inline within Health** — no dedicated screen. Health "Stuck items" section's `View →` link is removed; per-row `Inspect` navigates to Item Detail. Rationale and ruling captured in §4 Health screen entry. | §2, §4 |
| M5 | First Run Experience promoted to Site Map and Screen Inventory as a pre-auth flow. Flow G added. Authority alignment with Mockups §10 restored. | §2, §3 Flow G, §4 |
| M6 | Coordinated with Audit §8: "screen budget" clarified as **5 primary navigation destinations**, plus a bounded set of in-flow sub-screens. Captured in §4 preamble. | §4 |
| S1–S3 | Expert Mode variant notes added to the Screen Inventory entries for Safe Candidate Review, Item Judgment, and Library, surfacing what Blueprint already implied (bulk select, classification confidence, apply-to-similar). Mockups v1.1 backfills the visuals. | §4 |
| T1 | Evidence-drawer link label standardized to **`Why safe?`** in safe contexts, **`Why risky?`** in risky contexts, with **`Why?`** as the generic fallback (Item Detail, Diagnostics, etc.). The variant `Why? Details` is removed. | §4, §9 (Evidence Drawer entry) |
| C4 | Narrow Expert carve-out: the labels `Engine status` (section header) and `Reconciliation` (row label) are permitted **only** inside Settings → Diagnostics. Charter principle #7 still applies everywhere else. | §1 (Level 4 rule), §8 |

No other content is changed by v1.1.

---

---

## 1. PRODUCT HIERARCHY

Four layers, each with strict rules about what users see and when.

### LEVEL 1 — OUTCOMES *(always visible)*
What the user came here to achieve. Stated as user goals, not system functions.

- "Recover disk space"
- "See if my show downloaded"
- "Find out what's broken"
- "Configure the app"

**Surface:** Navigation labels, banner headlines, primary buttons.
**Rule:** Every screen must answer "what outcome does this serve?" in one sentence. If it can't, it doesn't ship.

### LEVEL 2 — DECISIONS *(visible, but earned)*
The concrete choices the user makes. Pre-decided by the system whenever possible.

- "Remove these 12 items (38 GB)"
- "Keep this risky item / Remove it / Decide later"
- "Reconnect qBittorrent"
- "Toggle Expert Mode"

**Surface:** Primary and secondary buttons, choice rows, batch actions.
**Rule:** Every decision presented to the user must come with a system recommendation. Never offer choice without guidance.

### LEVEL 3 — EVIDENCE *(hidden by default, one click away)*
The "why" behind a decision. Available on demand via drawer, expansion, or detail view.

- "Why was this flagged safe?" → watched 4 weeks ago, not seeding, replaced by 4K version
- "Why is this risky?" → still seeding, 0.4 ratio, added 6 days ago
- Item history, attribution chain, lifecycle timeline (compact form)

**Surface:** "Show details," "Why?" links, item detail drawers, inline expansion.
**Rule:** Evidence is always accessible but never demanded. The user opens it when they want to verify; otherwise the system speaks for itself.

### LEVEL 4 — ENGINES *(invisible in Normal Mode, dedicated panels in Expert Mode)*
The intelligence layer itself: correlation outputs, raw attribution chains, lifecycle event streams, validation reports, diagnostics.

**Surface (Normal):** Nowhere. Engines produce Decisions and Evidence; they are not surfaced as their own concept.
**Surface (Expert):** Settings → Diagnostics; per-item "Inspect" panel; Health detail pages.
**Rule:** No user, even in Expert Mode, ever sees the literal words "Correlation Engine" or "Responsibility Attribution." Those are codebase terms. Expert surfaces use plain names ("Inspect," "Timeline," "Source trail").

**Narrow exception (v1.1, per audit finding C4):** Two labels are permitted **only** inside Settings → Diagnostics: the section header `Engine status` and the row label `Reconciliation`. These are the lowest-cost labels for the operator audience that screen serves and do not appear on any Normal-Mode surface. Charter principle #7 ("speak the user's language, not the codebase's") still binds every other surface.

### What users see first

```
┌─────────────────────────────────────┐
│ OUTCOMES         (headline)         │
│   DECISIONS      (buttons)          │
│     EVIDENCE     (one click away)   │
│       ENGINES    (Expert only)      │
└─────────────────────────────────────┘
```

A new user should be able to use Handoffarr for months without ever encountering Level 4.

---

## 2. SITE MAP

```
(First Run Experience)              [pre-auth / first install only — see §3 Flow G]
│
Handoffarr
│
├── Home                            [all personas]
│
├── Recover Space                   [Sam, Pat]
│   ├── Summary (default)
│   ├── Safe Candidate Review       (sub-screen — formal, per v1.1 C2)
│   ├── Risky Candidate Review
│   │   └── Item Judgment view      (one item at a time)
│   ├── Preview                     (sub-screen — formal, per v1.1 M3)
│   └── Cleanup History             (sub-screen — formal, per v1.1 M2; Mockups §2B)
│       └── Cleanup Batch Detail    (per-batch view with Undo; Mockups §2C)
│
├── Library                         [Sam, Casey, Pat]
│   ├── Recent activity (default)
│   ├── Search / browse
│   ├── Filters (status, type, source)
│   └── Item Detail                 (drawer on desktop/tablet, full screen on mobile)
│       ├── Overview (Normal)
│       ├── History (Expert)
│       ├── Source trail (Expert)
│       ├── Inspect (Expert)
│       └── Actions (verify, flag, remove)
│
├── Health                          [Sam, Riley]
│   ├── Status summary (default)
│   ├── Integration list
│   │   └── Integration Detail      (sub-screen — formal, per v1.1 M1)
│   ├── Stuck items                 (inline only — per v1.1 M4; per-row Inspect → Item Detail)
│   └── Recent issues
│
└── Settings                        [Riley, Pat]
    ├── Integrations
    │   ├── qBittorrent
    │   ├── Sonarr / Radarr / Lidarr
    │   └── Overseerr
    ├── Cleanup rules
    │   ├── Auto-cleanup policies
    │   ├── Risk thresholds
    │   └── Excluded items
    ├── Notifications
    ├── Appearance              (theme, density)
    ├── Mode                    (Normal / Expert toggle)
    └── Diagnostics             (Expert only)
        ├── Engine status
        ├── Validation reports
        └── Logs
```

### Screen-by-screen summary

**Screen budget (v1.1 clarification, coordinated with Audit §8):** Handoffarr has **5 primary navigation destinations** (Home, Recover Space, Library, Health, Settings) plus a bounded set of **in-flow sub-screens** reached only from within a parent flow, plus a **pre-auth First Run flow** seen only on first install. Sub-screens are not nav entries and never appear in the global header.

| Tier | Screen | Purpose | Primary action | Secondary actions | Persona |
|---|---|---|---|---|---|
| Primary | Home | One screen that answers "what should I do, if anything?" | Resolve the top suggestion | Jump to any section | All |
| Primary | Recover Space | End-to-end cleanup workflow | "Recover X GB" | Review risky, preview, history | Sam, Pat |
| Primary | Library | Find and inspect items | Open item | Search, filter | All |
| Primary | Health | Surface broken/stuck things | Resolve top issue | Dismiss, inspect (per row) | Sam, Riley |
| Primary | Settings | Configure | Save | Toggle Expert | Riley, Pat |
| Sub | Safe Candidate Review | Verify and adjust safe-item selection | "Recover X GB" (live total) | Why safe?, Cancel | Sam, Pat |
| Sub | Risky Candidate Review (Item Judgment) | Decide on one risky item | Remove / Keep / Later | Why risky?, Skip | Sam, Pat |
| Sub | Preview | Show exactly what would happen — no execution | "Proceed and recover X GB" | Cancel | Sam, Pat |
| Sub | Cleanup History | Review past cleanup batches | Open a batch | (none at list level) | Sam, Pat |
| Sub | Cleanup Batch Detail | Inspect one batch, undo if in window | Undo all / Restore item | Close | Sam, Pat |
| Sub | Item Detail | Everything about one item | Contextual (Verify / Remove / View in Health) | Open in *arr, Inspect (Expert) | All |
| Sub | Integration Detail | Fix one integration | Test connection / Reconnect | Edit settings, View logs (Expert) | Riley |
| Sub | Diagnostics | Deep inspection (Expert only) | (none — read-only) | Re-run, Export logs | Riley, Pat |
| Pre-auth | First Run Experience | Guided 3-step onboarding | "Continue" / "Finish" | Skip for now | New users |

**Stuck Items (per v1.1 M4):** No dedicated screen. Stuck items render inline in the Health screen as a bounded list; per-row `Inspect` navigates to Item Detail (which surfaces the stuck-state variant per Mockups §6). If the list exceeds a small threshold (≥ ~10), the implementation paginates within the Health surface — it still does not promote to a separate screen.

---

## 3. USER FLOWS

### FLOW A — Recover Space (the golden path)

```
Entry: Home banner "42 GB ready to recover" → click [Review and recover]
   │
   ▼
Recover Space screen loads
   • System has already classified items into Safe / Judgment / Hidden
   • Summary shows total recoverable
   │
   ▼
User sees "Safe to remove: 12 items, 38 GB" with [Recover 38 GB] button
   │
   ├──► (Path 1: trust the system) Click [Recover 38 GB]
   │       │
   │       ▼
   │    Inline confirmation strip appears: "Remove 12 items (38 GB)?"
   │       Options: [Confirm]  [Preview first]  [Cancel]
   │       │
   │       ▼
   │    Click [Confirm]
   │       │
   │       ▼
   │    Progress indicator: "Recovering… 8 of 12"
   │       │
   │       ▼
   │    Success state: "✓ Recovered 38 GB · [Undo (24h)] · [View what was removed]"
   │       │
   │       ▼
   │    EXIT: User done. Background reconciliation happens silently.
   │
   └──► (Path 2: verify first) Click [Review items] → navigates to
                                 Safe Candidate Review (sub-screen, v1.1 C2)
        OR Click [Preview first] → navigates to Preview (sub-screen, v1.1 M3)
           │
           ▼
        Safe Candidate Review: list of 12 rows (poster, title, size, "Why safe?" link)
           Sticky bottom action bar with live total + Cancel
           │
           ├──► User unchecks 2 items they want to keep
           │       │
           │       ▼
           │    Updated total: "Recover 32 GB" — bottom button updates live
           │       │
           │       ▼
           │    Click [Recover 32 GB] → inline confirmation → execution → success
           │       (User returns to Recover Space on success)
           │
           └──► User clicks "Why safe?" on one item
                   │
                   ▼
                Evidence drawer: "Watched 28 days ago, no seeding obligation,
                                 replaced by 2160p version on 2026-05-12"
                   │
                   ▼
                User closes drawer, proceeds to confirm

Exit conditions:
  ✓ Items removed + success state shown
  ✓ User cancels (no state change)
  ✓ User navigates away (state preserved for return)
```

### FLOW B — Investigate Why Space Is Full

**v1.1 update (per audit finding C1):** Home Stat Tiles are summaries, not navigation. Entry to this flow is via the global nav `Library` entry or via the `View →` link in the Recently added section header on Home. The Storage tile communicates state only; it does not respond to clicks. Principle: *Cards summarize. Buttons navigate.*

```
Entry: User navigates to Library (global nav) or clicks "View →"
        in the Recently added section header on Home
   │
   ▼
Library screen loads; user sorts by "Largest items"
   • Sort: Size descending
   • Filter chips visible: [All] [Movies] [Shows] [Music]
   │
   ▼
User scans top items
   │
   ├──► Sees a single 80 GB item they don't recognize
   │       │
   │       ▼
   │    Click item → Item Detail drawer
   │       Shows: title, size, when added, source, last played
   │       Primary action contextually: [Remove] (because never played + large)
   │       │
   │       ▼
   │    User clicks [Remove] → inline confirm → removed → returns to list
   │
   └──► Sees a category dominating space (e.g., 4K movies)
           │
           ▼
        Clicks filter [Movies] → sees subset
           │
           ▼
        Considers a bulk action: "Remove all unwatched > 30 days" (Expert only)
           OR navigates back to Recover Space for system recommendations

Exit conditions:
  ✓ User identified the cause
  ✓ User removed offending items
  ✓ User decided no action needed
```

### FLOW C — Check If A Request Downloaded

```
Entry: Home OR direct navigation to Library
   │
   ▼
(If recently added) Home "Recently added" section shows the item with status
   │
   ├──► Item visible on Home → click → Item Detail → confirmation visible
   │
   └──► Not visible on Home → navigate to Library
           │
           ▼
        Library search bar (always present at top)
           │
           ▼
        User types title → instant filter
           │
           ▼
        Item appears with status badge:
           • ✓ "Imported · 2 days ago"
           • ⟳ "Downloading · 67%"
           • ⏸ "Stuck · last update 3 days ago"  → links to Health
           • ✗ "Not found"
           │
           ▼
        (Optional) Click for Item Detail with full timeline

Exit conditions:
  ✓ Status confirmed
  ✓ User redirected to Health if stuck
  ✓ User confirms item is missing and adds via Overseerr (external)
```

### FLOW D — Fix A Broken Integration

```
Entry: Home banner "⚠ qBittorrent unreachable" OR Health tile shows issue
   │
   ▼
Click → Health screen
   • Top of list: the broken integration with red badge
   │
   ▼
Click the integration → Integration Detail
   • Shows: status, last successful contact, error message in plain language
   • Primary action: [Test connection]
   • Secondary: [Edit settings] [View logs (Expert)]
   │
   ▼
User clicks [Test connection]
   │
   ├──► Success: status updates to green, banner clears
   │
   └──► Failure: error shown with suggested fix
           ("Connection refused — is qBittorrent running on port 8080?")
           │
           ▼
        User clicks [Edit settings] → updates URL/credentials
           │
           ▼
        [Test connection] → success → returns to Health

Exit conditions:
  ✓ Integration green
  ✓ User dismissed as known issue (Expert only)
```

### FLOW E — Review Risky Cleanup Candidates

```
Entry: Recover Space → "Needs your judgment: 3 items" section
   │
   ▼
Click [Review] → Item Judgment view loads first item
   • Full-width card: poster, title, size
   • Why risky (plain): "Still seeding · 0.4 ratio · added 6 days ago"
   • Three buttons of equal visual weight:
       [Remove]   [Keep]   [Remind me in 7 days]
   • Progress indicator: "1 of 3"
   │
   ▼
User makes a decision → next item loads automatically
   │
   ▼
(Optional) "Why was this flagged?" link expands evidence inline
   │
   ▼
After last item: summary
   "Reviewed 3 items: 1 removed, 1 kept, 1 deferred"
   Button: [Back to Recover Space]

Exit conditions:
  ✓ All items decided
  ✓ User exits mid-review (decisions made so far are saved)
```

### FLOW F — View Cleanup History

```
Entry: Recover Space → [History] link in header
   │
   ▼
History screen: reverse chronological list of cleanup batches
   Each entry:
     • Date
     • "Recovered X GB · N items"
     • Source (manual / scheduled / auto-rule)
     • [Undo] button if within reversibility window
     • [View items] link
   │
   ▼
Click a batch → Detail view
   • List of items in that batch
   • Per-item status (removed, still in trash, restored)
   • [Undo all] if within window
   • [Restore item] per row if within window
   │
   ▼
Click [Undo all] → confirmation → restoration progress → success

Exit conditions:
  ✓ User restored a batch
  ✓ User restored individual items
  ✓ User reviewed and exited
```

### FLOW G — First Run Experience (v1.1, per audit finding M5)

```
Entry: First install / no integrations configured
   │
   ▼
Step 1 — Welcome
   • Display headline, supporting body, [ Get started ] Primary
   │
   ▼
Step 2 — Connect integrations
   • Form rows for qBittorrent, Sonarr, Radarr (required)
   • Lidarr, Overseerr (optional, collapsed by default)
   • Per-row [ Test ] (Secondary) and [ Connect ] (Primary)
   │
   ├──► Test succeeds → row shows ✓ Connected
   │
   └──► Test fails → inline caution Meta with plain-language hint
            User can fix and retry, or Skip for now
   │
   ▼
[ Continue ] (or [ Skip for now ] Ghost) → Step 3
   │
   ▼
Step 3 — Ready
   • ✓ "You're ready." headline
   • Body explaining first-pass background work
   • [ Go to Home ] Primary
   │
   ▼
Home (Normal Mode default)

Exit conditions:
  ✓ User completes setup and lands on Home
  ✓ User skips integrations and lands on Home (Health will surface absent integrations)
```

Visual specification is locked by Mockups §10. No Expert-Mode variant: Expert is introduced post-onboarding via Settings.

---

## 4. SCREEN INVENTORY

**v1.1 preamble — screen tiering.** Five **primary** screens have global nav entries (Home, Recover Space, Library, Health, Settings). **Sub-screens** are reachable only via in-flow navigation from a parent; they never appear in the global nav. **First Run** is a pre-auth flow seen only on first install. This tiering reconciles Audit §8 ("six screens" — now reworded), Blueprint v1, and Mockups.

### Home

- **Purpose:** Answer "is anything important right now?"
- **Primary action:** Resolve the top suggestion (varies)
- **Secondary actions:** Navigate to any section
- **Visible:** Top suggestion banner, three at-a-glance tiles (Storage / Activity / Health), Recently added list
- **Hidden:** All analytics, all metrics not tied to decisions, anything from the engines
- **Expert additions:** Small "Last engine run" footer with link to Diagnostics

### Recover Space

- **Purpose:** Free up disk space
- **Primary action:** "Recover X GB" (safe items)
- **Secondary:** Review items needing judgment, preview, view history, expand safe item list
- **Visible:** Total recoverable headline, Safe section with primary button, Judgment section with count, collapsed "items not recommended" section
- **Hidden:** Per-item evidence (one click away), engine internals, classification thresholds
- **Expert additions:** Rule-based filters, "show classification confidence," bulk operations across all categories

### Safe Candidate Review (sub-screen of Recover Space, v1.1 C2)

- **Purpose:** Verify the system's safe-item classification and adjust selection before recovery
- **Primary action:** "Recover X GB" with live total
- **Secondary:** Select all / Deselect all, Cancel, per-row "Why safe?"
- **Visible:** Title with item count + total, selection meta row, list of Safe Candidate Item Rows, sticky bottom action bar
- **Hidden:** Per-item evidence (one click via "Why safe?" → Evidence Drawer)
- **Expert additions (S1):** Classification confidence shown per row as Meta; "Apply to similar items" bulk action available when ≥3 selected items share a rule attribution
- **Visual specification:** Mockups §3

### Risky Candidate Review — Item Judgment (sub-screen of Recover Space)

- **Purpose:** Decide one risky item at a time
- **Primary action:** Remove / Keep / Later (three-way decision, equal weight)
- **Secondary:** "Why risky?" link, Skip
- **Visible:** Single item card with plain-language risk explanation, item-of-N progress indicator
- **Hidden:** Full attribution chain, raw correlation data
- **Expert additions (S2):** Lifecycle timeline visible by default below the bulleted "Why risky?" reasons; source trail expanded; "Apply to similar items" action below the three decision buttons; `R / K / L` keyboard shortcuts active (Foundation §11.4)
- **Visual specification:** Mockups §4

### Preview (sub-screen of Recover Space, v1.1 M3)

- **Purpose:** Show exactly what would happen — full dry-run summary — without performing the action
- **Primary action:** "Proceed and recover X GB"
- **Secondary:** Cancel
- **Visible:** Headline, scope summary (files to delete, projected free-space delta, per-integration removals, files kept because already removed elsewhere)
- **Hidden:** Per-item detail beyond aggregate counts (return to Safe Candidate Review for per-item adjustments)
- **Expert additions:** Per-rule grouping of would-be-removed items; toggle to expand projected qBittorrent / *arr cross-reference impact
- **Visual specification:** Mockups §2A

### Cleanup History (sub-screen of Recover Space, v1.1 M2)

- **Purpose:** Reverse-chronological list of past cleanup batches with Undo where applicable
- **Primary action:** Open a batch
- **Secondary:** (none at list level)
- **Visible:** Per-batch row with date, "Recovered X GB · N items", source (manual / scheduled / auto-rule), `[Undo]` button if within reversibility window, `[View items]` link
- **Hidden:** Per-batch item list (one drill-down)
- **Expert additions:** Filter by source / rule; show per-batch classification confidence summary
- **Visual specification:** Mockups §2B

### Cleanup Batch Detail (sub-screen of Cleanup History)

- **Purpose:** Inspect items in one batch and restore individually if within Undo window
- **Primary action:** `Undo all` (if within window)
- **Secondary:** `Restore item` per row, Close
- **Visible:** Batch header (date, total, source), per-item rows with status (removed / still in trash / restored)
- **Hidden:** Raw event log for the batch (Expert Diagnostics covers this)
- **Visual specification:** Mockups §2C

### Library

- **Purpose:** Find and inspect any item
- **Primary action:** Open item (or search)
- **Secondary:** Filter, sort, change view
- **Visible:** Search bar, filter chips, item grid/list with status badges
- **Hidden:** Item details (in drawer on desktop/tablet, full-screen on mobile)
- **Expert additions (S3):** Bulk select with per-row checkboxes and a sticky bulk-action bar (`Flag for cleanup`, `Remove from library` — both gated by inline confirmation); additional sort options (by source, by lifecycle stage); saved filter views accessible from the Sort dropdown
- **Visual specification:** Mockups §5 (Normal) + Mockups §5A (Expert variant, v1.1)

### Item Detail

- **Purpose:** Everything about one item
- **Primary action:** Contextual (Verify, Remove, or none if healthy)
- **Secondary:** Open in *arr, view in qBittorrent
- **Visible:** Poster, title, size, status, last activity, recent events (compact)
- **Hidden:** Full timeline, raw attribution, engine evidence
- **Expert additions:** Full lifecycle timeline, source trail, raw cross-reference data, manual override controls

### Health

- **Purpose:** Surface problems
- **Primary action:** Resolve top issue
- **Secondary:** Dismiss, mark as known, per-row Inspect
- **Visible:** Status summary banner, integration tiles, **inline** stuck items list (no separate screen — v1.1 M4), recent issues
- **Hidden:** Validation report internals, raw diagnostics
- **Stuck Items rule (v1.1 M4):** Stuck items render inline as a bounded list directly on Health. No `View →` link to a separate screen. Per-row `Inspect` navigates to Item Detail with the stuck-state variant (Mockups §6 covers the visual). If the list grows beyond ~10 items, the implementation paginates within Health — it does not promote to a dedicated screen.
- **Expert additions:** Validation report summaries inline, link to Diagnostics, per-integration sync history

### Integration Detail (sub-screen of Health, v1.1 M1)

- **Purpose:** Fix one integration
- **Primary action:** `Test connection` (or `Reconnect` after settings change)
- **Secondary:** `Edit settings`, `View logs` (Expert only)
- **Visible:** Integration name + status, last-successful-contact meta, plain-language error description (if broken), inline editor for URL / credentials when `Edit settings` is engaged
- **Hidden:** Raw logs and stack traces (Expert Diagnostics surfaces these)
- **Expert additions:** Per-test request/response summary, link to Diagnostics filtered to this integration
- **Visual specification:** Mockups §7A (v1.1 addition)

### Settings

- **Purpose:** Configure
- **Primary action:** Save (per section)
- **Secondary:** Toggle Expert Mode (prominent), test, reset
- **Visible:** Sectioned settings (Integrations / Rules / Notifications / Appearance / Mode)
- **Hidden:** Diagnostics (unless Expert)
- **Expert additions:** Diagnostics section appears, rule editor exposes thresholds, advanced integration options

### Diagnostics (sub-screen of Settings, Expert only)

- **Purpose:** Deep inspection of engine state
- **Primary action:** None — read-only surface
- **Secondary:** Export logs, copy report, force re-run, Investigate (per row)
- **Visible (when Expert):** `Engine status` section (permitted label, v1.1 C4), last run timestamps, validation reports, error logs. The `Reconciliation` row label is permitted here (v1.1 C4) and nowhere else.
- **Hidden:** Always hidden in Normal Mode
- **Visual specification:** Mockups §9

### First Run Experience (pre-auth flow, v1.1 M5)

- **Purpose:** Connect integrations and reach a state where Handoffarr can start working
- **Primary action (per step):** `Get started` (Step 1) → `Continue` (Step 2) → `Go to Home` (Step 3)
- **Secondary:** Per-integration `Test`, `Skip for now` Ghost on Step 2
- **Visible:** 3-segment progress strip, current step body, primary advancement button
- **Hidden:** Global header, bottom nav (replaced by the progress strip), Expert Mode (introduced post-onboarding)
- **Expert additions:** None (Expert is opt-in post-onboarding)
- **Visual specification:** Mockups §10

---

## 5. ASCII WIREFRAMES

Format note: these are layout sketches, not visual specs. They show *what goes where*, not pixel measurements.

### HOME

```
┌────────────────────────────────────────────────────────────────────┐
│ Handoffarr        Home  Recover  Library  Health  Settings    [SP]│
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                                                              │  │
│  │   42 GB ready to recover                                     │  │
│  │   14 items you've already watched · safe to remove           │  │
│  │                                                              │  │
│  │   [ Review and recover ]      Last cleanup: 6 days ago       │  │
│  │                                                              │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────┐    │
│  │  STORAGE       │  │  ACTIVITY      │  │  HEALTH            │    │
│  │                │  │                │  │                    │    │
│  │  1.8 TB free   │  │  12 imports    │  │  ✓ All connected   │    │
│  │  of 8 TB       │  │  this week     │  │                    │    │
│  │  ████████░░    │  │                │  │                    │    │
│  └────────────────┘  └────────────────┘  └────────────────────┘    │
│                                                                    │
│  Recently added                                            [View]  │
│  ─────────────────────────────────────────────────────────────     │
│   ▣  The Pitt · S01E08             Imported · 2 hours ago          │
│   ▣  Severance · S02E10            Imported · yesterday            │
│   ▣  Dune: Part Two (2024)         Imported · 2 days ago           │
│   ▣  Shōgun · S01E04               Imported · 3 days ago           │
│   ▣  Fountain of Youth (2025)      Imported · 4 days ago           │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### RECOVER SPACE (summary, default state)

```
┌────────────────────────────────────────────────────────────────────┐
│ ← Home                                                  [History]  │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│   Recover Space                                                    │
│                                                                    │
│   42 GB ready to recover                                           │
│   Based on what you've watched, replaced versions, and unused      │
│   items.                                                           │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  ✓  Safe to remove                              12 items     │  │
│  │     Watched, complete, no seeding obligation.   38 GB        │  │
│  │                                                              │  │
│  │     [ Recover 38 GB ]    [ Review items ]    [ Preview ]     │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  ⚠  Needs your judgment                          2 items     │  │
│  │     Still seeding or recently added.             4 GB        │  │
│  │                                                              │  │
│  │     [ Review ]                                               │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ▸ Show items not recommended for cleanup (87)                     │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### SAFE CANDIDATES (expanded review)

```
┌────────────────────────────────────────────────────────────────────┐
│ ← Recover Space                                                    │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│   Safe to remove — 12 items, 38 GB                                 │
│   Uncheck anything you want to keep.                               │
│                                                                    │
│   [✓] Recover 32 GB (10 selected)              [Select all]        │
│                                                                    │
│   ┌──────────────────────────────────────────────────────────┐     │
│   │ ☑ ▣  Friends · S03 (complete season)           4.2 GB    │     │
│   │     Last watched 6 weeks ago               [Why safe?]   │     │
│   ├──────────────────────────────────────────────────────────┤     │
│   │ ☐ ▣  Oppenheimer (2023) · 1080p                8.1 GB    │     │
│   │     Replaced by 2160p version              [Why safe?]   │     │
│   ├──────────────────────────────────────────────────────────┤     │
│   │ ☑ ▣  The Office · S05E12                       1.4 GB    │     │
│   │     Watched 4 weeks ago                    [Why safe?]   │     │
│   ├──────────────────────────────────────────────────────────┤     │
│   │ ☑ ▣  ...                                                 │     │
│   └──────────────────────────────────────────────────────────┘     │
│                                                                    │
│                                                                    │
│   ─────────────────────────────────────────────────────────────    │
│   [ Recover 32 GB ]                                  [Cancel]      │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### RISKY CANDIDATES (judgment, one at a time)

```
┌────────────────────────────────────────────────────────────────────┐
│ ← Recover Space                                  Item 1 of 3       │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│                  ┌─────────────────────────────┐                   │
│                  │                             │                   │
│                  │        [ poster ]           │                   │
│                  │                             │                   │
│                  └─────────────────────────────┘                   │
│                                                                    │
│                  Andor · S02 (complete)                            │
│                  18.2 GB                                           │
│                                                                    │
│   ─────────────────────────────────────────────────────────────    │
│   Why this needs your judgment:                                    │
│                                                                    │
│   • Still seeding (0.4 ratio — target is 1.0)                      │
│   • Added 6 days ago                                               │
│   • Watched yesterday                                              │
│                                                                    │
│                                                  [Why? Details]    │
│   ─────────────────────────────────────────────────────────────    │
│                                                                    │
│      [ Remove ]      [ Keep ]      [ Remind me in 7 days ]         │
│                                                                    │
│                                                          [ Skip ]  │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### LIBRARY

```
┌────────────────────────────────────────────────────────────────────┐
│ Handoffarr        Home  Recover  Library  Health  Settings    [SP]│
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│   Library                                                          │
│                                                                    │
│   [🔍 Search titles...                                          ]  │
│                                                                    │
│   [All] [Movies] [Shows] [Music] · Sort: [Recently added ▾]        │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ ▣  The Pitt · S01E08                                         │  │
│  │    Show · 2.1 GB · ✓ Imported 2 hours ago                    │  │
│  ├──────────────────────────────────────────────────────────────┤  │
│  │ ▣  Severance · S02E10                                        │  │
│  │    Show · 1.8 GB · ✓ Imported yesterday                      │  │
│  ├──────────────────────────────────────────────────────────────┤  │
│  │ ▣  Mickey 17 (2025)                                          │  │
│  │    Movie · 6.4 GB · ⟳ Downloading 67%                        │  │
│  ├──────────────────────────────────────────────────────────────┤  │
│  │ ▣  Untitled Request                                          │  │
│  │    Show · — · ⏸ Stuck · last update 3 days ago               │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
│   Showing 25 of 1,247                              [Load more]     │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### ITEM DETAIL (Normal Mode)

```
┌────────────────────────────────────────────────────────────────────┐
│ ← Library                                                          │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│   ┌─────────────┐                                                  │
│   │             │   Severance · S02E10                             │
│   │  [ poster ] │   Show · 1.8 GB · 2160p                          │
│   │             │   ✓ Imported yesterday                           │
│   └─────────────┘                                                  │
│                                                                    │
│                                  [ Open in Sonarr ]                │
│                                                                    │
│   ─────────────────────────────────────────────────────────────    │
│   Recent activity                                                  │
│                                                                    │
│   • Imported into library             Yesterday, 8:14 PM           │
│   • Download completed                Yesterday, 7:52 PM           │
│   • Grabbed by Sonarr                 Yesterday, 6:18 PM           │
│                                                                    │
│   ─────────────────────────────────────────────────────────────    │
│                                                                    │
│   [ Flag for cleanup ]              [ Remove from library ]        │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### HEALTH

```
┌────────────────────────────────────────────────────────────────────┐
│ Handoffarr        Home  Recover  Library  Health  Settings    [SP]│
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│   Health                                                           │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  ⚠  2 issues need attention                                  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
│   Integrations                                                     │
│  ┌────────────────────────┬─────────────────────────────────────┐  │
│  │ ⚠ qBittorrent          │ Connection refused                  │  │
│  │   Last seen 12m ago    │ [ Fix ]                             │  │
│  ├────────────────────────┼─────────────────────────────────────┤  │
│  │ ✓ Sonarr               │ Connected                           │  │
│  ├────────────────────────┼─────────────────────────────────────┤  │
│  │ ✓ Radarr               │ Connected                           │  │
│  ├────────────────────────┼─────────────────────────────────────┤  │
│  │ ✓ Lidarr               │ Connected                           │  │
│  ├────────────────────────┼─────────────────────────────────────┤  │
│  │ ✓ Overseerr            │ Connected                           │  │
│  └────────────────────────┴─────────────────────────────────────┘  │
│                                                                    │
│   Stuck items                                              [View]  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ ⏸  Untitled Request · no progress in 3 days       [Inspect] │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### SETTINGS

```
┌────────────────────────────────────────────────────────────────────┐
│ Handoffarr        Home  Recover  Library  Health  Settings    [SP]│
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│   Settings                                                         │
│                                                                    │
│   ┌──── INTEGRATIONS ──────────────────────────────────────────┐   │
│   │  qBittorrent          http://localhost:8080      [Edit]    │   │
│   │  Sonarr               http://localhost:8989      [Edit]    │   │
│   │  Radarr               http://localhost:7878      [Edit]    │   │
│   │  Lidarr               http://localhost:8686      [Edit]    │   │
│   │  Overseerr            http://localhost:5055      [Edit]    │   │
│   └────────────────────────────────────────────────────────────┘   │
│                                                                    │
│   ┌──── CLEANUP RULES ────────────────────────────────────────┐    │
│   │  Auto-cleanup after watched          [✓] After 30 days    │    │
│   │  Minimum seed ratio before cleanup   [1.0]                │    │
│   │  Excluded items                      [Manage (3)]         │    │
│   └───────────────────────────────────────────────────────────┘    │
│                                                                    │
│   ┌──── NOTIFICATIONS ────────────────────────────────────────┐    │
│   │  Notify when cleanup recommended     [✓]                  │    │
│   │  Notify on integration failure       [✓]                  │    │
│   └───────────────────────────────────────────────────────────┘    │
│                                                                    │
│   ┌──── MODE ─────────────────────────────────────────────────┐    │
│   │  Expert Mode                         [○──── off]          │    │
│   │  Shows diagnostics, lifecycle history, and source trails. │    │
│   └───────────────────────────────────────────────────────────┘    │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### EXPERT MODE — Item Detail (additions visible)

```
┌────────────────────────────────────────────────────────────────────┐
│ ← Library                                              [EXPERT]    │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│   ┌─────────────┐                                                  │
│   │  [ poster ] │  Severance · S02E10  ·  1.8 GB  ·  2160p         │
│   └─────────────┘  ✓ Imported yesterday                            │
│                                                                    │
│   [ Overview ]  [ History ]  [ Source trail ]  [ Inspect ]         │
│                                                                    │
│   ─── HISTORY ────────────────────────────────────────────────     │
│   ● Imported into library              Jun 1, 8:14 PM              │
│   │   path: /media/shows/Severance/S02/...                         │
│   ●  Download completed                Jun 1, 7:52 PM              │
│   │   qBittorrent · hash: a7f3...                                  │
│   ●  Download started                  Jun 1, 6:21 PM              │
│   │   indexer: Indexer-X · seeders: 47                             │
│   ●  Grabbed by Sonarr                 Jun 1, 6:18 PM              │
│   │   release: Severance.S02E10.2160p...                           │
│   ●  Requested via Overseerr           May 28, 9:02 AM             │
│                                                                    │
│   ─── SOURCE TRAIL ───────────────────────────────────────────     │
│   Library entry    ← Sonarr import (✓ matched)                     │
│   qBittorrent      ← hash a7f3... (✓ owned by Sonarr)              │
│   Sonarr           ← release grab (✓ confirmed)                    │
│   Overseerr        ← request #4821 (✓ fulfilled)                   │
│                                                                    │
│   [ Override classification ]   [ Force re-verify ]                │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### EXPERT MODE — Diagnostics

```
┌────────────────────────────────────────────────────────────────────┐
│ ← Settings                                             [EXPERT]    │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│   Diagnostics                                                      │
│                                                                    │
│   ┌──── ENGINE STATUS ────────────────────────────────────────┐    │
│   │  Recommendations    ✓ Last run 4 min ago    [Re-run]      │    │
│   │  Library check      ✓ Last run 1 hour ago   [Re-run]      │    │
│   │  Reconciliation     ✓ Last run 12 min ago   [Re-run]      │    │
│   │  Source matching    ⚠ 3 unresolved          [Investigate] │    │
│   └───────────────────────────────────────────────────────────┘    │
│                                                                    │
│   ┌──── VALIDATION REPORTS ───────────────────────────────────┐    │
│   │  Library vs. Sonarr      0 discrepancies                  │    │
│   │  Library vs. Radarr      1 discrepancy        [View]      │    │
│   │  Library vs. Lidarr      0 discrepancies                  │    │
│   │  qBittorrent ownership   2 orphans            [View]      │    │
│   └───────────────────────────────────────────────────────────┘    │
│                                                                    │
│   ┌──── LOGS ─────────────────────────────────────────────────┐    │
│   │  [Recent activity ▾]  [Filter: errors only ▾]             │    │
│   │                                                           │    │
│   │  06-02 14:22  WARN  Source match unresolved: hash 8c2e... │    │
│   │  06-02 14:18  INFO  Recommendation run complete (4.2s)    │    │
│   │  06-02 14:06  INFO  Reconciliation complete · 0 changes   │    │
│   │  06-02 13:58  INFO  Sonarr sync complete                  │    │
│   │                                                           │    │
│   │                              [Export logs]   [Clear view] │    │
│   └───────────────────────────────────────────────────────────┘    │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 6. DASHBOARD BLUEPRINT

### What appears above the fold

1. **The "one important thing" banner** (variable content):
   - Critical health issue → red banner with [Fix]
   - Else: meaningful recoverable space (≥ a configurable threshold, e.g. 10 GB) → primary banner with [Review and recover]
   - Else: stuck items → warning banner with [View]
   - Else: calm idle state → "✓ Everything's running smoothly"
2. **Three at-a-glance tiles:** Storage / Activity / Health — each a single number with at most one supporting line.

### What appears below the fold

3. **Recently added** — last 5 items, lightweight list, links to Library.

### What is hidden

- Engine metrics (analyzed counts, correlation results, classification confidence)
- Anything labeled with internal terms
- Charts (no charts on Home, ever)
- Configuration status
- Recent cleanup details (in Recover Space → History)

### What the eye sees first

The banner headline. It is the largest text on screen and sits in a card with visible weight. The user's gaze should land on it before anything else.

### The single primary action

The button inside the banner. There is exactly one. Tiles below have no buttons — they are summaries, not actions. The Recently added list has hover affordances but no per-row buttons.

### What never appears on the dashboard

- "Correlation," "Lifecycle," "Attribution," "Validation," "Diagnostics," "Reconciliation," "Engine"
- Per-integration status (that's Health's job)
- Raw counts of operations performed
- Settings shortcuts
- Multiple competing CTAs

### Idle state rule

When the banner has nothing important to say, it becomes calm — short copy, no button, low visual weight. The dashboard is allowed to look quiet. That is a feature.

---

## 7. RECOVER SPACE BLUEPRINT

### Three-section pattern (always)

```
┌─────────────────────────────────────────────────────┐
│ HEADLINE          "X GB ready to recover"           │
├─────────────────────────────────────────────────────┤
│ SAFE              [Recover X GB]  [Review]  [Preview]│
├─────────────────────────────────────────────────────┤
│ JUDGMENT          [Review]                          │
├─────────────────────────────────────────────────────┤
│ NOT RECOMMENDED   ▸ (collapsed)                     │
└─────────────────────────────────────────────────────┘
```

### Interaction rules

**Rule 1 — Recommendation is pre-decided.** The system has already classified. The user does not classify; the user approves.

**Rule 2 — Inline confirmation, not modal.** Clicking [Recover X GB] reveals a confirmation strip immediately below the section. No dialog box. The strip has [Confirm], [Preview first], [Cancel].

**Rule 3 — Live total.** When the user unchecks items in the safe list, the primary button text updates in real time: "Recover 32 GB."

**Rule 4 — Preview = dry-run.** Preview shows exactly what would happen — files to delete, sizes, post-cleanup free space — without performing the action. Preview has its own clear "Proceed" affordance from within.

**Rule 5 — Execution is non-blocking.** A progress strip appears at the top; the user can navigate away. Completion shows a toast/banner.

**Rule 6 — Success state includes Undo.** "✓ Recovered 38 GB · [Undo (24h)]" sits in place of the section that was acted on. The Undo window is configurable in Settings but defaults to 24 hours.

**Rule 7 — Risky items are never bundled with safe items.** Even if the user wants to "do everything," they must explicitly enter the judgment flow for risky items. This is intentional friction at the only place it's earned.

**Rule 8 — Empty state is a success message.**
> ✓ Nothing to recover right now.
> Next automatic check in 18 hours.
> [ Run a check now ]

### Execution sub-states

```
Idle           → "Recover 38 GB" button
Confirming     → inline strip with Confirm/Preview/Cancel
Executing      → top progress strip "Recovering… 8 of 12"
Succeeded      → success banner with Undo + View
Partial fail   → "Recovered 34 GB (10 of 12). 2 items could not be removed. [View]"
Total fail     → "Cleanup failed. [Retry] [View error]" — links to Health
```

### Dry-run / Preview behavior

Preview is a full-screen state, not a modal:
```
┌─────────────────────────────────────────────────┐
│ ← Recover Space                                 │
│                                                 │
│   Preview                                       │
│   This is what would happen. Nothing is removed │
│   until you confirm.                            │
│                                                 │
│   • 12 files would be deleted                   │
│   • Free space: 1.80 TB → 1.84 TB               │
│   • qBittorrent torrents removed: 9             │
│   • Files kept (already removed elsewhere): 3   │
│                                                 │
│   [ Proceed and recover 38 GB ]      [Cancel]   │
└─────────────────────────────────────────────────┘
```

---

## 8. EXPERT MODE BLUEPRINT

### Activation

Single toggle in Settings → Mode. Persists per-user. A small `[EXPERT]` chip appears in the top-right of every screen when active. No other visual change to the chrome.

### What Expert Mode does

It **adds**. It never removes or rearranges Normal Mode surfaces. A user who toggles Expert on still sees the same Home, the same Recover Space, the same Library. They additionally see:

#### 1. Inspect panels (on items)

Every item gains a tab strip: **Overview / History / Source trail / Inspect.**

- **History:** Chronological events for the item (request → grab → download → import → play → recommendation).
- **Source trail:** Cross-reference state across qBittorrent, Sonarr/Radarr/Lidarr, Overseerr — with match/mismatch indicators.
- **Inspect:** Raw record IDs, classification confidence, "force re-verify," "override classification."

These are the surfaces powered by the lifecycle, correlation, and attribution engines — **named for what the user does with them**, not for the engine that produces them.

#### 2. Diagnostics section (in Settings)

A new top-level section appears in Settings when Expert is on. It contains:
- Engine status (recommendations, library check, reconciliation, source matching) with last-run times and re-run buttons
- Validation reports (library vs. each *arr, qBittorrent ownership)
- Logs with filter and export

#### 3. In-place enrichment

Normal-mode surfaces gain modest density:
- Recover Space adds: classification confidence, rule attribution per item, "apply to similar"
- Health adds: per-integration sync history, validation summary inline
- Library adds: bulk select, additional sort/filter options (by source, by lifecycle stage)
- Item Judgment expands "Why flagged?" by default and shows the lifecycle compact timeline

#### 4. Dry-run becomes default

In Expert Mode, destructive actions default to Preview. The user must explicitly switch to live execution. This honors Pat's mental model: "I want to see before I do."

### Navigation structure with Expert on

```
Home  Recover  Library  Health  Settings  [EXPERT]
                                   │
                                   ├── Integrations
                                   ├── Cleanup rules
                                   ├── Notifications
                                   ├── Appearance
                                   ├── Mode
                                   └── Diagnostics      ← appears only in Expert
                                       ├── Engine status
                                       ├── Validation reports
                                       └── Logs
```

No new top-level nav entries. Expert lives inside existing surfaces or in Settings → Diagnostics.

### What Expert Mode does NOT do

- Does not rename anything from Normal Mode
- Does not expose internal terminology ("Correlation Engine") even here
- Does not become the default for new users
- Does not hide the Mode toggle (it must always be reachable)

---

## 9. COMPONENT LIBRARY

### Primary Banner (Home)
- **Purpose:** Present the single most important thing right now
- **Anatomy:** Headline, subline, primary button, optional meta
- **Usage:** Home only. One per page. Content varies by system state.
- **Anti-patterns:** Multiple banners. Banner without a clear action when an action is possible. Banner that re-renders frequently (visual noise).

### Stat Tile
- **Purpose:** At-a-glance metric tied to a decision
- **Anatomy:** Label, single value, optional one-line supporting text, optional micro-visual (thin bar)
- **Usage:** Home and Health summaries. Groups of 3.
- **Anti-patterns:** Tiles with charts. Tiles with buttons. Tiles that show vanity metrics. Tile grids larger than 3 — that's a dashboard within a dashboard.

### Recommendation Card
- **Purpose:** Present a system-recommended decision with a clear default
- **Anatomy:** Status icon, title, supporting line, primary button, secondary actions
- **Usage:** Recover Space sections, Health issues
- **Anti-patterns:** Cards without a primary action. Cards that just describe state. Stacks of more than ~4 — collapse into list view.

### Item Row (Safe Candidate variant)
- **Purpose:** Display an item in a bulk-selectable list
- **Anatomy:** Checkbox, poster thumbnail, title, supporting line, size, "Why?" link
- **Usage:** Safe candidate list
- **Anti-patterns:** Per-row delete buttons (use bulk action). Showing risky items in the same component.

### Item Row (Risky variant)
- **Purpose:** Single-item judgment surface
- **Anatomy:** Large poster, title, size, "Why risky" bulleted plain text, three equal-weight buttons
- **Usage:** Item Judgment flow only
- **Anti-patterns:** Stacking risky items in a scrollable list. Skipping the plain-language explanation.

### Item Row (Library variant)
- **Purpose:** Browse and inspect items
- **Anatomy:** Thumbnail, title, type · size · status, status badge
- **Usage:** Library list
- **Anti-patterns:** Showing per-item bulk actions in Normal Mode. Cramming metadata.

### Health Tile
- **Purpose:** Show one integration or system component's state
- **Anatomy:** Status icon, name, last-contact line, contextual button (Fix / Inspect)
- **Usage:** Health screen
- **Anti-patterns:** Showing healthy integrations with the same visual weight as broken ones — broken should dominate.

### Evidence Drawer
- **Purpose:** Reveal the "why" for any decision on demand
- **Anatomy:** Triggered by a context-specific link — **`Why safe?`** in safe-cleanup contexts, **`Why risky?`** in risky-cleanup contexts, **`Why?`** as the generic fallback in all other contexts (Item Detail, Diagnostics, Health). Slides in from the right (desktop) or up (mobile); plain-language explanation, optional bulleted facts, link to full detail (Expert)
- **Standardized labels (v1.1 T1):** Use `Why safe?` / `Why risky?` / `Why?` exclusively. The variant `Why? Details` is retired.
- **Usage:** Any recommendation, classification, or flag
- **Anti-patterns:** Always-visible evidence panels (defeats the purpose). Evidence drawers full of jargon. Drawers without close affordance.

### Activity Timeline (Compact / Full)
- **Purpose:** Show what happened to an item, in chronological order
- **Anatomy:** Vertical timeline, event marker, label, timestamp, optional meta (Expert)
- **Usage:** Item Detail (compact, Normal); Item Detail History tab (full, Expert)
- **Anti-patterns:** Showing the full timeline in Normal Mode. Using timeline for non-chronological data.

### Inline Confirmation Strip
- **Purpose:** Confirm an action without a modal
- **Anatomy:** Single line of text describing what will happen + [Confirm] [Preview] [Cancel]
- **Usage:** Default for destructive actions where reversibility is provided
- **Anti-patterns:** Using a modal when an inline strip suffices. Inline strip without context ("Are you sure?").

### Confirmation Dialog (modal)
- **Purpose:** Confirm catastrophic, non-reversible actions
- **Anatomy:** Title, body explaining consequences, optional "type to confirm" field, two buttons
- **Usage:** Reserved for: deleting all data, removing integration with data loss, factory reset
- **Anti-patterns:** Using modals for routine deletions. Modals without context. Modals styled to look harmless.

### Success State Banner
- **Purpose:** Confirm completion of an action and offer Undo
- **Anatomy:** Check icon, "Recovered X · [Undo (Yh)] [View]"
- **Usage:** After any destructive action
- **Anti-patterns:** Toast-only success (too easy to miss). Success without Undo where Undo is possible.

### Status Badge
- **Purpose:** Compact item status indicator
- **Anatomy:** Icon + label ("✓ Imported", "⟳ Downloading", "⏸ Stuck")
- **Usage:** Library rows, Item Detail header
- **Anti-patterns:** Inventing new statuses per-screen. Color-only badges (must include label for accessibility).

### Mode Indicator
- **Purpose:** Show Expert is active
- **Anatomy:** Small chip in top-right: `[EXPERT]`
- **Usage:** Persistent when Expert Mode on
- **Anti-patterns:** Animating it, highlighting it, treating it as a feature. It's a status indicator.

### Filter Chip Row
- **Purpose:** Quick categorical filter
- **Anatomy:** Pill buttons, single-select default; sort dropdown on the right
- **Usage:** Library
- **Anti-patterns:** More than ~5 chips. Multi-select without clear visual treatment.

---

## 10. DESIGN SYSTEM

### Layout system

**Single-column, max content width ~960px, centered.** Use a 12-column grid only where multiple peers must align (e.g., tile rows). The header is a full-width persistent strip; main content is centered. No fixed sidebars for content. Page chrome stays out of the way.

### Spacing system

**4px base, scale: 4, 8, 12, 16, 24, 32, 48, 64.** Use spacing to communicate grouping before reaching for borders or background fills. Tight (4–8) for intra-element; medium (16–24) for related elements; large (32–48) between sections; extra-large (64) for top-of-page rhythm.

### Typography hierarchy

Five levels, no more:
- **Display** — banner headlines on Home and Recover Space ("42 GB ready to recover"). Used 1× per page.
- **Title** — screen and section titles
- **Subtitle** — section descriptions, card titles
- **Body** — default text
- **Meta** — timestamps, sizes, secondary info

Weight is part of hierarchy. Color is not — most text is the same neutral; emphasis comes from size and weight, not color.

### Color philosophy

**Neutral palette + one accent + three semantic colors.** That's it.
- **Neutrals:** background, surface, text, dividers (4 shades)
- **Accent:** primary actions, current nav state, focus rings (one color)
- **Semantic:**
  - **Green** — success, healthy, completed
  - **Yellow/Amber** — needs judgment, caution
  - **Red** — error, destructive, critical health

If a fifth color is needed, the design is wrong. Status badges use icon + label, with color as reinforcement only — never the sole signal.

### Warning philosophy

Three tiers, strictly distinct:
1. **Info** — neutral background, dismissible, fades after acknowledgement
2. **Caution** (amber) — sticky until resolved, requires explicit dismissal or action
3. **Critical** (red) — blocks the relevant surface, appears in Health and as Home banner

**Rule:** A given screen should never display all three simultaneously. If it does, prioritize Critical, queue the rest.

### Confirmation philosophy

Preference order (use the highest one possible):
1. **Reversible action with Undo** (default for cleanups)
2. **Inline confirmation strip** (for routine destructive actions)
3. **Modal dialog** (for high-stakes irreversible)
4. **Type-to-confirm modal** (for catastrophic)

Every confirmation surface, regardless of form, must state *what will happen* (scope), not just *that something will happen*.

### Table philosophy

Use tables only when users compare rows across the same columns. Otherwise use lists. Tables get:
- Sticky headers
- Sortable columns
- 5 visible columns max in Normal Mode (Expert may expand)
- Row hover affordance
- One primary action per row, secondary actions in a row menu (•••)

No nested tables. No horizontal scroll in Normal Mode. No table where rows have wildly different heights.

### Card philosophy

A card is a commitment that says "this is one cohesive thing." It must have at least two of: title, body, action. Cards without actions are decorative — reconsider.

**Cards summarize. Buttons navigate. (v1.1 C1.)** Stat Tiles, Health Tiles, and section cards present state — they are not click targets for navigation. Navigation always occurs via an explicit button, link, or nav entry. The Storage tile on Home does not respond to clicks; users reach Library through the nav bar or the `View →` link in the Recently added section header. Health Integration Tiles are the explicit exception: each tile is a click target because each row *is* the navigation affordance for that integration's detail screen — but this is communicated visually (hover state, cursor) so the affordance is unambiguous.

**Card budget per screen:**
- Home: max 5 (1 banner + 3 tiles + 1 recent list)
- Recover Space: 3 (sections)
- Health: 1 banner + tiles
- Item Detail: 1 (the item itself)

If a page exceeds the budget, sections should become lists or be moved to a sub-screen.

### Progressive disclosure rules

**Rule 1 — Default to summary.** Every screen opens at the lowest-detail useful state.
**Rule 2 — Detail is a click, never a hunt.** "Show more," "Why?", "View details" — always near the thing they expand.
**Rule 3 — Expanded state survives navigation.** If a user expands a section, then navigates away and returns within the session, the section is still expanded.
**Rule 4 — Three levels max.** Summary → expanded → drawer/detail screen. Never a fourth level. If you need one, restructure.
**Rule 5 — Expert is its own dimension, not a level.** Expert adds *new* surfaces; it doesn't simply uncollapse hidden ones.

---

## 11. MOBILE EXPERIENCE

Mobile is not a shrunk desktop. It is a different product with the same purpose. Two key shifts:

### Navigation

**Bottom tab bar (5 entries, same as desktop):** Home / Recover / Library / Health / Settings. Icons + short labels. Always visible. The Expert mode chip moves to the header.

```
┌────────────────────────┐
│ Handoffarr        [SP] │
├────────────────────────┤
│                        │
│       [content]        │
│                        │
├────────────────────────┤
│  🏠   ↻   📚   ⚕   ⚙   │
│ Home Rec  Lib  Hlth Set│
└────────────────────────┘
```

### Dashboard (mobile)

```
┌────────────────────────┐
│ Home              [SP] │
├────────────────────────┤
│ ┌────────────────────┐ │
│ │ 42 GB              │ │
│ │ ready to recover   │ │
│ │ 14 items           │ │
│ │                    │ │
│ │ [Review & recover] │ │
│ └────────────────────┘ │
│                        │
│ ┌────────────────────┐ │
│ │ Storage            │ │
│ │ 1.8 TB free of 8TB │ │
│ │ ████████░░         │ │
│ └────────────────────┘ │
│ ┌────────────────────┐ │
│ │ Activity           │ │
│ │ 12 imports / week  │ │
│ └────────────────────┘ │
│ ┌────────────────────┐ │
│ │ Health             │ │
│ │ ✓ All connected    │ │
│ └────────────────────┘ │
│                        │
│ Recently added         │
│  ▣ The Pitt · S01E08  │
│  ▣ Severance · S02E10 │
│  ▣ Dune: Part Two     │
│                        │
├────────────────────────┤
│  🏠   ↻   📚   ⚕   ⚙   │
└────────────────────────┘
```

Tiles stack vertically. Banner remains the visual hero. List items get poster + title only; no metadata clutter.

### Cleanup workflow (mobile)

The three-section pattern still works, but each section becomes a full-width card and the safe items list opens as a full-screen view, not an inline expansion.

**Risky review (mobile)** is the same one-item-at-a-time pattern; the three decision buttons stack vertically full-width for thumb reach:

```
┌────────────────────────┐
│ ← Recover    1 of 3    │
├────────────────────────┤
│      [ poster ]        │
│                        │
│  Andor · S02 (complete)│
│  18.2 GB               │
│                        │
│  Why this needs your   │
│  judgment:             │
│  • Still seeding (0.4) │
│  • Added 6 days ago    │
│  • Watched yesterday   │
│                        │
│  [Why? Details]        │
│                        │
│ ┌────────────────────┐ │
│ │     Remove         │ │
│ └────────────────────┘ │
│ ┌────────────────────┐ │
│ │     Keep           │ │
│ └────────────────────┘ │
│ ┌────────────────────┐ │
│ │ Remind in 7 days   │ │
│ └────────────────────┘ │
│              [Skip]    │
└────────────────────────┘
```

### Confirmations (mobile)

**Inline strips become bottom sheets.** Slide up from the bottom edge with the same content as the desktop inline strip. Tap outside to cancel. Bottom sheets respect safe area insets.

```
┌────────────────────────┐
│      [content]         │
│                        │
├────────────────────────┤  ← sheet edge
│ Remove 12 items?       │
│ 38 GB                  │
│                        │
│ [   Confirm   ]        │
│ [   Preview   ]        │
│ [   Cancel    ]        │
└────────────────────────┘
```

### Mobile-specific rules

- **Single-column always.** Even on tablet portrait.
- **No hover-dependent affordances.** "Why?" links are persistent tap targets.
- **Drawers become full screens.** Item Detail on mobile is a full-screen route, not a side drawer.
- **Tables become cards.** Library is always a list of cards on mobile, never a table.
- **No Expert-Mode dense tables on mobile.** Expert surfaces remain accessible but flatten to cards. Diagnostics on mobile is a read-only feed.

---

## 12. IMPLEMENTATION ROADMAP

### Phase 1 — Navigation + IA (2–3 weeks)

**Scope:**
- Implement the 5-item top-level navigation
- Add Mode toggle in Settings
- Migrate all existing surfaces to live under the new IA (without redesigning them yet)
- Apply terminology rewrite across the existing UI

**Effort:** Medium. Mostly routing, relabeling, hiding.
**Risk:** Low. Reversible; doesn't change core flows.
**Impact:** High. Immediately reduces cognitive load and stops the "developer dashboard" feeling.

### Phase 2 — Dashboard (2–3 weeks)

**Scope:**
- Build new Home with banner + tiles + recently added
- Implement banner state machine (critical → recover → stuck → idle)
- Implement calm idle state
- Remove all engine-derived surfaces from Home

**Effort:** Medium.
**Risk:** Low–medium. Requires backend to expose a single "top suggestion" endpoint that prioritizes across categories.
**Impact:** Very high. This is the screen every user sees first; fixing it changes the perception of the entire product.

### Phase 3 — Recover Space (4–6 weeks)

**Scope:**
- Three-section pattern (Safe / Judgment / Not recommended)
- One-click batch Recover with live total
- Inline confirmation strip
- Preview / dry-run flow
- Execution progress + success state with Undo
- History screen
- Item Judgment one-at-a-time flow

**Effort:** High. This is the flagship feature; every detail matters.
**Risk:** Medium. Requires a robust Undo window (backend reversibility) and clear partial-failure semantics.
**Impact:** Massive. This is the moment Handoffarr becomes a *product*.

### Phase 4 — Expert Mode (3–4 weeks)

**Scope:**
- Mode toggle wired into per-user preference
- Item Inspect tabs (History, Source trail, Inspect)
- Diagnostics section in Settings
- Expert enrichments across existing screens
- Dry-run default behavior in Expert

**Effort:** Medium-high.
**Risk:** Low. Additive only; cannot break Normal Mode if scoped correctly.
**Impact:** Retains and re-engages power users without compromising the default experience.

### Phase 5 — Polish (ongoing, 3–4 weeks of focused investment)

**Scope:**
- Empty/idle state pass across all screens
- Onboarding flow for first-time users (3-step setup)
- Mobile layouts (bottom nav, bottom sheets, single-column flows)
- Accessibility audit (focus order, contrast, keyboard navigation, screen reader)
- Microcopy review against the Charter
- Performance: skeletons, optimistic UI on Recover actions
- Notification surface (in-app and external)

**Effort:** Distributed; never truly "done."
**Risk:** Low.
**Impact:** Compounding. This is the difference between a working redesign and a product people recommend.

---

## Closing: What This Blueprint Commits Us To

This blueprint trades **breadth for depth**. We are deliberately exposing fewer surfaces, fewer concepts, and fewer decisions on every screen — and putting the engineering team's intelligence to work *behind* those surfaces instead of on top of them.

The single biggest cultural shift this requires is the willingness to **let the engines disappear**. The correlation engine, the lifecycle engine, the attribution system — these are extraordinary pieces of work, and the temptation will be to give each one a place to shine. This blueprint says: their shine *is* the simplicity of the Recover Space screen. Their shine *is* the user confidently clicking "Recover 38 GB" without needing to know how the classification happened.

If we hold the line on that, Handoffarr stops being a tool that demands its users become operators, and becomes a tool that lets its users get back to watching their shows.