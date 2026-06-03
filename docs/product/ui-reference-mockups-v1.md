# Handoffarr UI Reference Mockups — v1.1
## Final visual appearance of every screen before implementation

> **v1.1 reconciliation note.** This revision incorporates the audit reconciliation. Changes are additive (new screen mockups for Integration Detail, Cleanup History, Cleanup Batch Detail, Preview) and clarifying (Expert Mode variant notes for Safe Candidate Review, Risky Candidate Review, and Library; `Why? Details` → `Why risky?`; Stuck items `View →` link removed). No tokens, layouts, or components were changed. See §0 Change Log.

---

## 0. CHANGE LOG (v1 → v1.1)

| ID | Change | Sections touched |
|---|---|---|
| C1 | Home Stat Tiles confirmed non-clickable (already correct in v1); cross-reference to Blueprint v1.1 Flow B added in §1. | §1 |
| C2 | Safe Candidate Review screen retained as previously specified; now backed by formal Blueprint Screen Inventory entry (no visual change). | §3 |
| M1 | **New mockup added (§7A): Integration Detail.** | §7A |
| M2 | **New mockup added (§2B): Cleanup History + Cleanup Batch Detail.** | §2B |
| M3 | **New mockup added (§2A): Preview (dry-run).** | §2A |
| M4 | Stuck items remain inline in Health. The `View →` link is removed from the Stuck items section header; per-row `Inspect` continues to navigate to Item Detail. | §7 |
| M5 | First Run Experience (§10) retained; now backed by formal Blueprint Screen Inventory and Flow G entries. | §10 |
| S1 | **Expert variant note added to §3:** classification confidence per row; "Apply to similar items" bulk action. | §3 |
| S2 | **Expert variant note added to §4:** lifecycle timeline visible by default; source trail expanded; "Apply to similar items" action; `R / K / L` keyboard shortcut hint at bottom of screen. | §4 |
| S3 | **Expert variant added (§5A): Library Expert Mode.** Bulk select + sticky bulk-action bar; additional sort options. | §5A |
| T1 | All `Why? Details` instances replaced with `Why risky?`. `Why safe?` and `Why?` (generic fallback) confirmed elsewhere. | §3, §4 |
| C4 | Diagnostics labels `Engine status` and `Reconciliation` confirmed as permitted Expert-Diagnostics-only exceptions. | §9 |

---

---

## 0. PURPOSE & SCOPE

This document is the **last specification artifact** before frontend implementation begins. It locks the visual appearance of every screen in the Blueprint, screen by screen, so that an engineer can recreate the interface without making design decisions.

It strictly inherits and does not modify:

- **UX Audit v1** — diagnoses and Charter.
- **UX Blueprint v1** — IA, screen inventory, flows, components, blueprint.
- **Visual Design Foundation v1** — tokens, type, color, spacing, motion, component visuals.

No new screens. No re-architecture. No re-flow. No new components. No new tokens. Only the appearance of what already exists.

**Reading the ASCII mockups.** They show layout — relative position, hierarchy, density — not pixel measurements. Type sizes, spacing, color, and component anatomy are governed by the Visual Design Foundation. Where a mockup and the Foundation disagree, the Foundation wins.

**Frame conventions used throughout:**
- `═══` = display headline / dominant element
- `───` = section divider (in practice, spacing carries this — see Foundation §4)
- `▣` = poster thumbnail
- `[ Label ]` = primary button
- `[Label]` = secondary or ghost button (context-dependent — see Foundation §9.1)
- `(•)` selected radio / chip · `[✓]` checkbox · `[ ]` unchecked
- `✓ ⚠ ✕ ⟳ ⏸ ⓘ` = the Foundation §6.3 status icon vocabulary
- `[SP]` = settings/profile shortcut in the top-right of the global header
- `[EXPERT]` = mode chip (Foundation §9.15)

---

# 1. Home

## Visual Intent

- **Calm.** The default frame should feel like a well-organized reading room.
- **Trustworthy.** A single sentence + a single button = the system has already done the thinking.
- **Invisible intelligence.** No mention of engines, correlations, attribution. Just outcomes.
- **Appliance-like.** Looks the same every visit; predictable slots, variable content.

## Layout

Top-to-bottom hierarchy:

1. **Global header** (56px fixed) — wordmark left, primary nav center, `[SP]` right.
2. **Primary Banner** ("one important thing"), Foundation §9.2.
3. **Stat Tile row** (3 tiles, equal width) — Storage / Activity / Health.
4. **Recently added** — section header + 5-row lightweight list, link to Library at right of header.

Single-column, max content width 960px, centered. Outer page gutter 32px desktop, 16px mobile.

## Component Placement

**Above the fold (desktop 1440×900, dark mode):**
- Header
- Primary Banner (full content visible — headline, subline, primary button, meta line)
- Top of Stat Tile row

**Below the fold:**
- Bottom of Stat Tile row (depending on viewport)
- Recently added list (5 rows)

**Hidden entirely:**
- Engine counts, correlation results, classification confidence
- Per-integration status (lives in Health)
- Settings shortcuts
- Charts of any kind

## Visual Hierarchy

- **Largest:** the Display headline numeral inside the Banner ("**42 GB**"), Display 32/40 weight 700, numeral in `--accent`.
- **Second:** the primary button inside the Banner.
- **Third:** Stat Tile values (Title size, tabular-nums).
- **Lowest priority:** "Last cleanup: 6 days ago" meta, Recently added timestamps, "View" link.

## Desktop Mockup

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Handoffarr        Home   Recover   Library   Health   Settings        [SP] │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐   │
│   │                                                                      │   │
│   │   42 GB ready to recover                                             │   │
│   │   14 items you've already watched · safe to remove                   │   │
│   │                                                                      │   │
│   │                                          [ Review and recover ]      │   │
│   │   Last cleanup: 6 days ago                                           │   │
│   │                                                                      │   │
│   └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐    │
│   │  STORAGE           │  │  ACTIVITY          │  │  HEALTH            │    │
│   │                    │  │                    │  │                    │    │
│   │  1.8 TB free       │  │  12 imports        │  │  ✓ All connected   │    │
│   │  of 8 TB           │  │  this week         │  │                    │    │
│   │  ████████░░        │  │                    │  │                    │    │
│   └────────────────────┘  └────────────────────┘  └────────────────────┘    │
│                                                                              │
│                                                                              │
│   Recently added                                                     View →  │
│                                                                              │
│   ▣  The Pitt · S01E08                          Imported · 2 hours ago      │
│   ▣  Severance · S02E10                         Imported · yesterday        │
│   ▣  Dune: Part Two (2024)                      Imported · 2 days ago       │
│   ▣  Shōgun · S01E04                            Imported · 3 days ago       │
│   ▣  Fountain of Youth (2025)                   Imported · 4 days ago       │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Tablet Mockup

(Portrait, ~768px wide. Single column, page gutter 24px. Tiles remain in a row but compress proportionally.)

```
┌────────────────────────────────────────────────┐
│ Handoffarr   Home  Recover  Library  …    [SP]│
├────────────────────────────────────────────────┤
│                                                │
│  ┌──────────────────────────────────────────┐  │
│  │  42 GB ready to recover                  │  │
│  │  14 items you've already watched ·       │  │
│  │  safe to remove                          │  │
│  │                                          │  │
│  │            [ Review and recover ]        │  │
│  │  Last cleanup: 6 days ago                │  │
│  └──────────────────────────────────────────┘  │
│                                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │ STORAGE  │  │ ACTIVITY │  │ HEALTH   │     │
│  │ 1.8 TB   │  │ 12 imp.  │  │ ✓ All    │     │
│  │ of 8 TB  │  │ this wk  │  │ connected│     │
│  │ ███████░ │  │          │  │          │     │
│  └──────────┘  └──────────┘  └──────────┘     │
│                                                │
│  Recently added                       View →   │
│   ▣ The Pitt · S01E08         2 hours ago      │
│   ▣ Severance · S02E10        yesterday        │
│   ▣ Dune: Part Two (2024)     2 days ago       │
│   ▣ Shōgun · S01E04           3 days ago       │
│   ▣ Fountain of Youth (2025)  4 days ago       │
│                                                │
└────────────────────────────────────────────────┘
```

## Mobile Mockup

```
┌────────────────────────┐
│ Handoffarr        [SP] │
├────────────────────────┤
│                        │
│ ┌────────────────────┐ │
│ │ 42 GB              │ │
│ │ ready to recover   │ │
│ │ 14 items you've    │ │
│ │ already watched    │ │
│ │                    │ │
│ │ [Review & recover] │ │
│ │                    │ │
│ │ Last cleanup:      │ │
│ │ 6 days ago         │ │
│ └────────────────────┘ │
│                        │
│ ┌────────────────────┐ │
│ │ STORAGE            │ │
│ │ 1.8 TB free of 8TB │ │
│ │ ████████░░         │ │
│ └────────────────────┘ │
│ ┌────────────────────┐ │
│ │ ACTIVITY           │ │
│ │ 12 imports / week  │ │
│ └────────────────────┘ │
│ ┌────────────────────┐ │
│ │ HEALTH             │ │
│ │ ✓ All connected    │ │
│ └────────────────────┘ │
│                        │
│ Recently added  View → │
│  ▣ The Pitt · S01E08   │
│  ▣ Severance · S02E10  │
│  ▣ Dune: Part Two      │
│  ▣ Shōgun · S01E04     │
│  ▣ Fountain of Youth   │
│                        │
├────────────────────────┤
│  🏠   ↻   📚   ⚕   ⚙   │
│ Home Rec  Lib Hlth Set │
└────────────────────────┘
```

## States

- **Empty / Idle (calm success):** Banner becomes the Idle variant (Foundation §9.2). Headline weight 600, `check-circle ✓` in `--success` to the left. Copy: "Everything's running smoothly." Subline: "Last cleanup recovered 24 GB · 6 days ago." No primary button. Optional Ghost "Run a check now" right-aligned.
- **Loading:** Banner shows a 60% skeleton block where the headline goes (one line wide). Tiles show skeleton blocks for value + supporting line; labels remain. Recently added shows 5 skeleton rows (thumbnail + two text lines). No spinner overlay; shell visible at all times.
- **Healthy (default recover state):** As pictured. Banner accent numeral. Tiles neutral. Health tile shows "✓ All connected".
- **Warning (stuck items, no health issues):** Banner content swaps to "3 items stuck in download." Subline names the queue context. Primary button: "View stuck items." No banner color shift — content drives meaning.
- **Critical (health issue dominates):** Banner numeral colored `--critical` instead of `--accent`. Icon `alert-octagon` left of headline at 20px. Headline: "qBittorrent unreachable." Subline: plain-language status. Primary button: "Fix integration." Storage/Activity tiles remain neutral; Health tile shows `⚠ 2 issues` in `--caution` strong.

## Component Behavior

- **Banner — Expanded / Collapsed:** Banner has no expand state. Its content is its content. State changes crossfade at `--motion-slow` (Foundation §7.2).
- **Banner — Hover:** None. The button inside the banner has hover; the banner itself does not.
- **Banner — Focus:** The primary button receives focus first when tabbing; Tab order: Banner button → first tile (only if clickable; tiles on Home are not) → Recently added first row.
- **Stat Tile — Expanded / Hover / Active:** None. Tiles are not interactive on Home. Cursor remains default.
- **Recently added row — Hover:** Row background `--surface-raised`, no scale or translate.
- **Recently added row — Focus:** 2px `--accent` ring, 2px offset.
- **Recently added row — Active:** 1px translate-y, ≤80ms.

## Example Content

Banner (recover state):
- Headline: "**42 GB** ready to recover"
- Subline: "14 items you've already watched · safe to remove"
- Button: "Review and recover"
- Meta: "Last cleanup: 6 days ago"

Tiles:
- Storage — "1.8 TB free / of 8 TB" + 8-cell progress bar at 78% full.
- Activity — "12 imports / this week"
- Health — "✓ All connected"

Recently added (relative timestamps in Normal Mode):
- The Pitt · S01E08 — Imported · 2 hours ago
- Severance · S02E10 — Imported · yesterday
- Dune: Part Two (2024) — Imported · 2 days ago
- Shōgun · S01E04 — Imported · 3 days ago
- Fountain of Youth (2025) — Imported · 4 days ago

---

# 2. Recover Space

## Visual Intent

- **Trustworthy.** The system has classified; the user approves.
- **Premium.** A single confident number, a single primary action.
- **Appliance-like.** Always the same three sections. The user learns the rhythm.
- **Calm under decision.** No urgency theatrics, no countdowns, no red unless something failed.

## Layout

1. **Top bar** with "← Home" back-link left, "[History]" link right.
2. **Screen Title** ("Recover Space"), Title size.
3. **Display headline** ("42 GB ready to recover") + one line of supporting body.
4. **Safe section card** (Recommendation Card).
5. **Judgment section card** (Recommendation Card).
6. **"Not recommended" disclosure** (collapsed by default), Ghost arrow expander.

48px vertical gap between Display headline and Safe card. 32px between cards.

## Component Placement

**Above the fold:**
- Top bar, screen title, Display headline + subline.
- Safe card with primary button visible.

**Below the fold:**
- Judgment card.
- "Not recommended" disclosure.

**Hidden:**
- Per-item evidence (one click via "Why?").
- Classification confidence (Expert only).
- Rule attribution per item (Expert only).

## Visual Hierarchy

- **Largest:** Display headline ("**42 GB** ready to recover") — numeral in `--accent`.
- **Second:** Primary button inside Safe card ("Recover 38 GB").
- **Lowest priority:** "Not recommended" disclosure label and the meta on each card row.

## Desktop Mockup

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ← Home                                                              History  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Recover Space                                                              │
│                                                                              │
│                                                                              │
│   42 GB ready to recover                                                     │
│   Based on what you've watched, replaced versions, and unused items.         │
│                                                                              │
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐   │
│   │  ✓  Safe to remove                                  12 items · 38 GB │   │
│   │     Watched, complete, no seeding obligation.                        │   │
│   │                                                                      │   │
│   │     [ Recover 38 GB ]     [ Review items ]     [ Preview ]           │   │
│   └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐   │
│   │  ⚠  Needs your judgment                              2 items · 4 GB  │   │
│   │     Still seeding or recently added.                                 │   │
│   │                                                                      │   │
│   │     [ Review ]                                                       │   │
│   └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   ▸  Show items not recommended for cleanup (87)                             │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Confirming sub-state** (inline strip appears flush beneath Safe card):

```
   ┌──────────────────────────────────────────────────────────────────────┐
   │  ✓  Safe to remove                                  12 items · 38 GB │
   │     Watched, complete, no seeding obligation.                        │
   │                                                                      │
   │     [ Recover 38 GB ]     [ Review items ]     [ Preview ]           │
   └──────────────────────────────────────────────────────────────────────┘
   ────────────────────────────────────────────────────────────────────────
     Remove 12 items (38 GB)?         [ Confirm ]  [Preview first]  [Cancel]
     [ ] Run as preview (dry-run)
   ────────────────────────────────────────────────────────────────────────
```

**Executing sub-state** (top progress strip):

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ██████████████████░░░░░░░░░░░░  Recovering… 8 of 12                          │
├──────────────────────────────────────────────────────────────────────────────┤
│ ← Home                                                              History  │
│   Recover Space                                                              │
│   …                                                                          │
```

**Succeeded sub-state** (Safe card replaced by Success Banner):

```
   ┌──────────────────────────────────────────────────────────────────────┐
   │  ✓  Recovered 38 GB.  12 items removed.                              │
   │                              [ Undo (24h) ]   [ View what was removed ] │
   └──────────────────────────────────────────────────────────────────────┘
```

## Tablet Mockup

```
┌────────────────────────────────────────────────┐
│ ← Home                                History  │
├────────────────────────────────────────────────┤
│                                                │
│  Recover Space                                 │
│                                                │
│  42 GB ready to recover                        │
│  Based on what you've watched, replaced        │
│  versions, and unused items.                   │
│                                                │
│  ┌──────────────────────────────────────────┐  │
│  │ ✓ Safe to remove        12 items · 38 GB │  │
│  │   Watched, complete, no seeding.         │  │
│  │                                          │  │
│  │   [ Recover 38 GB ]  [Review]  [Preview] │  │
│  └──────────────────────────────────────────┘  │
│                                                │
│  ┌──────────────────────────────────────────┐  │
│  │ ⚠ Needs your judgment    2 items · 4 GB  │  │
│  │   Still seeding or recently added.       │  │
│  │                                          │  │
│  │   [ Review ]                             │  │
│  └──────────────────────────────────────────┘  │
│                                                │
│  ▸ Show items not recommended (87)             │
│                                                │
└────────────────────────────────────────────────┘
```

## Mobile Mockup

```
┌────────────────────────┐
│ ← Recover  History     │
├────────────────────────┤
│                        │
│ Recover Space          │
│                        │
│ 42 GB                  │
│ ready to recover       │
│ Based on what you've   │
│ watched, replaced      │
│ versions, and unused.  │
│                        │
│ ┌────────────────────┐ │
│ │ ✓ Safe to remove   │ │
│ │   12 items · 38 GB │ │
│ │   Watched,         │ │
│ │   complete, no     │ │
│ │   seeding.         │ │
│ │                    │ │
│ │ [ Recover 38 GB ]  │ │
│ │ [   Review items ] │ │
│ │ [   Preview      ] │ │
│ └────────────────────┘ │
│                        │
│ ┌────────────────────┐ │
│ │ ⚠ Needs judgment   │ │
│ │   2 items · 4 GB   │ │
│ │   Still seeding    │ │
│ │   or recently      │ │
│ │   added.           │ │
│ │ [    Review      ] │ │
│ └────────────────────┘ │
│                        │
│ ▸ Not recommended (87) │
│                        │
├────────────────────────┤
│  🏠   ↻   📚   ⚕   ⚙   │
└────────────────────────┘
```

Confirmation on mobile rises as a bottom sheet (Foundation §7.2):

```
├────────────────────────┤  ← sheet edge
│ Remove 12 items?       │
│ 38 GB · cannot be      │
│ undone after 24 h.     │
│                        │
│ [✓] Run as preview     │
│                        │
│ [    Confirm        ]  │
│ [    Preview first  ]  │
│ [    Cancel         ]  │
└────────────────────────┘
```

## States

- **Empty (nothing to recover):**
  ```
     Recover Space

     ✓  Nothing to recover right now.
        Next automatic check in 18 hours.

        [ Run a check now ]
  ```
  Centered column, max 360px, generous breathing room (Foundation §10.1).
- **Loading:** Display headline area shows a single 60% skeleton line; cards show skeleton header rows + skeleton button placeholders (radius preserved). No spinner.
- **Healthy:** As pictured above (default state).
- **Warning — Judgment-only:** Safe card collapses to a thin status row: "✓ No safe items right now." Judgment card carries the primary action.
- **Warning — Partial success after execution:**
  ```
     ⚠  Recovered 34 GB (10 of 12). 2 items could not be removed.
        [ View ]   [ Retry ]
  ```
  Surface `--caution-quiet`, icon `--caution` strong.
- **Error — Total failure:**
  ```
     ✕  Cleanup failed.
        We couldn't remove these items. Try again or check Health.
        [ Retry ]   [ View error ]   [ Go to Health ]
  ```
  Surface `--critical-quiet`, icon `--critical` strong, links to Health.

## Component Behavior

- **Recommendation Card — Expanded:** Cards do not expand on this screen. "Review items" navigates to the Safe Candidate Review screen; "Review" on the Judgment card navigates to Risky Candidate Review.
- **Recommendation Card — Hover:** No hover state on the card itself; only its buttons hover.
- **Recommendation Card — Focus:** Focus order moves through buttons left-to-right within a card, then to the next card.
- **Not-recommended disclosure — Collapsed:** Ghost label "▸ Show items not recommended for cleanup (87)". Click expands to a lightweight list inline below; arrow rotates to ▾. Expansion animates height with `--motion-base`.
- **Not-recommended disclosure — Expanded:** Shows a Library-style list (read-only Item Rows). No bulk actions, no per-row remove. "Why not recommended?" Evidence drawer per row.
- **Inline confirmation strip:** Appears flush below Safe card with top border `--border-strong`. Disappears on Cancel (`--motion-base`). On Confirm, replaced immediately by progress strip at top.

## Example Content

- "42 GB ready to recover"
- Safe: 12 items · 38 GB · "Watched, complete, no seeding obligation."
- Judgment: 2 items · 4 GB · "Still seeding or recently added."
- Not recommended count: 87.
- History link top-right.

---

# 2A. Preview (Dry-Run) — v1.1 M3

## Visual Intent

- **Trustworthy.** Show exactly what would happen — no surprises.
- **Calm.** A summary, not a spreadsheet. Bullet-list of impact, one confident proceed action.
- **Reversible by construction.** Nothing is removed until the user proceeds from this screen.

## Layout

1. **Top bar:** "← Recover Space" back-link left.
2. **Screen title:** "Preview"
3. **Subtitle:** "This is what would happen. Nothing is removed until you confirm."
4. **Impact list** — bulleted summary of projected outcome.
5. **Bottom action bar:** Primary "Proceed and recover X GB" + Ghost "Cancel".

Single column, max 720px.

## Component Placement

**Above the fold:** title, subtitle, impact list, action bar (on standard desktop viewports).
**Hidden:** per-item enumeration (return to Safe Candidate Review to adjust selection).

## Visual Hierarchy

- **Largest text:** screen title "Preview".
- **Second:** primary button "Proceed and recover X GB".
- **Lowest priority:** the subtitle and the meta on each impact bullet.

## Desktop Mockup

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ← Recover Space                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Preview                                                                    │
│   This is what would happen. Nothing is removed until you confirm.           │
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐   │
│   │  •  12 files would be deleted                                        │   │
│   │  •  Free space: 1.8 TB → 1.9 TB                                      │   │
│   │  •  qBittorrent torrents removed: 9                                  │   │
│   │  •  Files kept (already removed elsewhere): 3                        │   │
│   └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   ────────────────────────────────────────────────────────────────────────   │
│                                                                              │
│   [ Proceed and recover 38 GB ]                                      Cancel  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Tablet Mockup

```
┌────────────────────────────────────────────────┐
│ ← Recover Space                                │
├────────────────────────────────────────────────┤
│ Preview                                        │
│ This is what would happen. Nothing is removed  │
│ until you confirm.                             │
│                                                │
│ ┌──────────────────────────────────────────┐   │
│ │ • 12 files would be deleted              │   │
│ │ • Free space: 1.8 TB → 1.9 TB            │   │
│ │ • qBittorrent torrents removed: 9        │   │
│ │ • Files kept: 3                          │   │
│ └──────────────────────────────────────────┘   │
│                                                │
│ [ Proceed and recover 38 GB ]          Cancel  │
└────────────────────────────────────────────────┘
```

## Mobile Mockup

```
┌────────────────────────┐
│ ← Recover Space        │
├────────────────────────┤
│ Preview                │
│ This is what would     │
│ happen. Nothing is     │
│ removed until you      │
│ confirm.               │
│                        │
│ • 12 files would be    │
│   deleted              │
│ • Free space:          │
│   1.8 TB → 1.9 TB      │
│ • qBittorrent          │
│   torrents removed: 9  │
│ • Files kept: 3        │
│                        │
│ [ Proceed and recover  │
│   38 GB              ] │
│ [ Cancel             ] │
├────────────────────────┤
│  🏠   ↻   📚   ⚕   ⚙   │
└────────────────────────┘
```

## States

- **Empty:** Should not be reachable with nothing to preview.
- **Loading:** Title and subtitle render; impact list shows 4 skeleton bullet lines; action bar shows skeleton button.
- **Healthy:** As pictured.
- **Warning — projection incomplete:** Inline `--caution` Meta below the impact list: "Some projections couldn't be computed. Proceeding will still remove only what you've selected."
- **Error — projection failed:** Section-level error in the impact-list area: "Couldn't compute preview. [ Retry ] [ Back ]".

## Component Behavior

- **Impact list:** Static read-only; bullet markers are neutral dots (not `--caution`). Numbers use tabular-nums.
- **"Proceed and recover X GB"** — Primary. Click triggers the same inline confirmation strip used on Recover Space, then execution. Returns to Recover Space on success.
- **Cancel** — Ghost. Returns to Recover Space with no state change.

## Expert Mode variant

- Impact list adds: per-rule grouping ("from rule `watched-30d`: 8 items"), per-integration cross-reference summary, and a "Show per-item breakdown" Ghost link that opens a read-only list inline.
- No new tokens or components.

## Example Content

- "12 files would be deleted"
- "Free space: 1.8 TB → 1.9 TB"
- "qBittorrent torrents removed: 9"
- "Files kept (already removed elsewhere): 3"
- Button: "Proceed and recover 38 GB"

---

# 2B. Cleanup History — v1.1 M2

## Visual Intent

- **Calm.** A reading list of past actions. No urgency.
- **Trustworthy.** Each batch shows what was recovered, when, by what trigger, and whether Undo is still available.
- **Appliance-like.** Reverse-chronological, predictable rhythm.

## Layout

1. **Top bar:** "← Recover Space" back-link left.
2. **Screen title:** "Cleanup History"
3. **List of batch rows** (one per cleanup execution).
4. **Pagination / Load more** at the bottom.

Single column, max 720px.

## Component Placement

**Above the fold:** title and first 6–8 batch rows.
**Below the fold:** older batches, "Load more" Ghost.

**Hidden:** per-batch item list (one drill-down — see Cleanup Batch Detail below).

## Visual Hierarchy

- **Largest text:** screen title.
- **Second:** per-row "Recovered X GB · N items" headline (Body weight 600).
- **Lowest:** date, source meta, "View items" Ghost link.

## Desktop Mockup

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ← Recover Space                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Cleanup History                                                            │
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐   │
│   │  Recovered 38 GB · 12 items                                          │   │
│   │  Today, 2:14 PM · Manual                            [Undo (23h)]     │   │
│   │                                                            View items│   │
│   ├──────────────────────────────────────────────────────────────────────┤   │
│   │  Recovered 24 GB · 9 items                                           │   │
│   │  6 days ago · Scheduled                                              │   │
│   │                                                            View items│   │
│   ├──────────────────────────────────────────────────────────────────────┤   │
│   │  Recovered 12 GB · 4 items                                           │   │
│   │  13 days ago · Auto-rule `watched-30d`                               │   │
│   │                                                            View items│   │
│   ├──────────────────────────────────────────────────────────────────────┤   │
│   │  Recovered 56 GB · 18 items                                          │   │
│   │  3 weeks ago · Manual                                                │   │
│   │                                                            View items│   │
│   └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   Showing 4 of 27                                                  Load more │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Tablet Mockup

```
┌────────────────────────────────────────────────┐
│ ← Recover Space                                │
├────────────────────────────────────────────────┤
│ Cleanup History                                │
│                                                │
│ Recovered 38 GB · 12 items                     │
│ Today, 2:14 PM · Manual    [Undo (23h)]        │
│                              View items        │
│ ────────────────────────────────────────       │
│ Recovered 24 GB · 9 items                      │
│ 6 days ago · Scheduled                         │
│                              View items        │
│ ────────────────────────────────────────       │
│ Recovered 12 GB · 4 items                      │
│ 13 days ago · Auto-rule `watched-30d`          │
│                              View items        │
│                                                │
│ Showing 4 of 27                    Load more   │
└────────────────────────────────────────────────┘
```

## Mobile Mockup

```
┌────────────────────────┐
│ ← Recover Space        │
├────────────────────────┤
│ Cleanup History        │
│                        │
│ Recovered 38 GB        │
│ 12 items               │
│ Today, 2:14 PM         │
│ Manual                 │
│      [Undo (23h)]      │
│           View items   │
│ ─────────────────────  │
│ Recovered 24 GB        │
│ 9 items                │
│ 6 days ago · Scheduled │
│           View items   │
│ ─────────────────────  │
│ Recovered 12 GB        │
│ 4 items                │
│ 13 days ago            │
│ Auto-rule watched-30d  │
│           View items   │
│                        │
│ 4 of 27     Load more  │
├────────────────────────┤
│  🏠   ↻   📚   ⚕   ⚙   │
└────────────────────────┘
```

## States

- **Empty:**
  ```
     Cleanup History

     ✓  No cleanups yet.
        Your first recovery will show up here.

        [ Back to Recover Space ]
  ```
  Foundation §10.1 calm-empty pattern.
- **Loading:** Title renders; 6 skeleton batch rows (two text lines per row, button-shaped skeleton on the right).
- **Healthy:** As pictured.
- **Warning — partial-success batch in history:** Row carries an inline `⚠` icon to the left of the headline; meta line reads "Recovered 34 GB (10 of 12) · Today, 2:14 PM".
- **Error — failed batch in history:** Row carries `✕` icon and reads "Failed cleanup · Today, 2:14 PM"; `View items` becomes `View error`.

## Component Behavior

- **Batch row — Hover:** background `--surface-raised`. Entire row is the click target (navigates to Cleanup Batch Detail).
- **Batch row — Focus:** 2px `--accent` ring.
- **`[Undo (Yh)]` button — Secondary, small size.** Visible only within the reversibility window (default 24h, configurable in Settings). Click opens the inline confirmation strip and triggers a restore job.
- **`View items` — Ghost link**, `--accent` text.
- **Load more — Ghost button.**

## Expert Mode variant

- Header row adds filter chips: `All` `Manual` `Scheduled` `Auto-rule` (Foundation §9.16).
- Each row shows an additional Meta line with classification confidence summary (e.g., "Confidence: high (10) / medium (2)").
- No new tokens or components.

## Example Content

- "Recovered 38 GB · 12 items — Today, 2:14 PM · Manual — [Undo (23h)] — View items"
- "Recovered 24 GB · 9 items — 6 days ago · Scheduled — View items"
- "Recovered 12 GB · 4 items — 13 days ago · Auto-rule `watched-30d` — View items"
- "Recovered 56 GB · 18 items — 3 weeks ago · Manual — View items"

---

# 2C. Cleanup Batch Detail — v1.1 M2

## Visual Intent

- **Trustworthy.** Per-item visibility into what was removed. Restore individually if needed.
- **Calm.** A read-mostly list. Undo is available where applicable; otherwise the page is informational.

## Layout

1. **Top bar:** "← Cleanup History" back-link.
2. **Batch header:** date, total recovered, source.
3. **Per-item list** (read-only Library-row variant with status: `Removed` / `Still in trash` / `Restored`).
4. **Bottom action bar (within Undo window):** `[ Undo all ]` Primary + `Close` Ghost.

## Component Placement

**Above the fold:** header, batch summary, top 5–6 item rows.
**Below the fold:** remaining rows, bottom action bar.

## Visual Hierarchy

- **Largest text:** batch summary headline ("Recovered 38 GB · 12 items").
- **Second:** `[ Undo all ]` Primary if visible.
- **Lowest:** per-item timestamps and status labels.

## Desktop Mockup

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ← Cleanup History                                                            │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Recovered 38 GB · 12 items                                                 │
│   Today, 2:14 PM · Manual                                                    │
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐   │
│   │ ▣  Friends · S03 (complete season)         4.2 GB     ✓ Removed      │   │
│   │    Still in trash                                       Restore item │   │
│   ├──────────────────────────────────────────────────────────────────────┤   │
│   │ ▣  Oppenheimer (2023) · 1080p              8.1 GB     ✓ Removed      │   │
│   │    Still in trash                                       Restore item │   │
│   ├──────────────────────────────────────────────────────────────────────┤   │
│   │ ▣  The Office · S05E12                     1.4 GB     ↺ Restored     │   │
│   ├──────────────────────────────────────────────────────────────────────┤   │
│   │ ▣  The Bear · S02E05                       2.0 GB     ✓ Removed      │   │
│   │    Still in trash                                       Restore item │   │
│   └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   ────────────────────────────────────────────────────────────────────────   │
│                                                                              │
│   [ Undo all ]                                                       Close   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Tablet / Mobile Mockup

Single column, full-width rows. `[ Undo all ]` and `Close` stack vertically on mobile.

## States

- **Within Undo window:** As pictured; `[ Undo all ]` + per-row `Restore item` visible.
- **Outside Undo window:** Bottom action bar shows `Close` Ghost only; per-row `Restore item` links are absent; rows display final status text only.
- **Restoration in progress (after Undo all click):** Top progress strip (Foundation §10.2): "Restoring… 4 of 12".
- **Restoration succeeded:** Success Banner replaces the bottom action bar: "✓ Restored 12 items. [ Close ]".

## Component Behavior

- **`Restore item` — Ghost link** per row. Click opens inline confirmation strip for that single item; immediate restoration.
- **`Undo all` — Primary** at the bottom. Click opens an inline confirmation strip (Foundation §9.10): "Restore all 12 items? [ Confirm ] [ Cancel ]".

---

# 3. Safe Candidate Review

## Visual Intent

- **Trustworthy.** The system has decided these are safe. The user is verifying, not deciding.
- **Calm.** A list that reads, not a spreadsheet that demands.
- **Premium.** The live total at the bottom feels confident, not transactional.

## Layout

1. **Top bar:** "← Recover Space" left, no right action.
2. **Screen title:** "Safe to remove — 12 items, 38 GB"
3. **Subtitle:** "Uncheck anything you want to keep."
4. **Selection meta + Select-all toggle row.**
5. **List of Safe Candidate Item Rows** (Foundation §9.6).
6. **Bottom action bar** with primary button (live total) + Cancel.

Single column, max 720px (narrower than 960px for reading comfort). Each row is full content width.

## Component Placement

**Above the fold:** title, subtitle, selection meta row, first 4–6 item rows.
**Below the fold:** remaining rows, bottom action bar (sticky on desktop only when list exceeds viewport).

**Hidden:** per-item evidence (via "Why safe?" → Evidence Drawer).

## Visual Hierarchy

- **Largest:** screen title ("Safe to remove — 12 items, 38 GB"), Title size.
- **Second:** primary button at the bottom ("Recover 32 GB").
- **Third:** item titles in each row (Body, weight 600).
- **Lowest priority:** per-row supporting line, "Why safe?" link.

## Desktop Mockup

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ← Recover Space                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Safe to remove — 12 items, 38 GB                                           │
│   Uncheck anything you want to keep.                                         │
│                                                                              │
│   10 selected · 32 GB                                            Select all  │
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐   │
│   │ [✓] ▣  Friends · S03 (complete season)                       4.2 GB  │   │
│   │        Last watched 6 weeks ago                            Why safe? │   │
│   ├──────────────────────────────────────────────────────────────────────┤   │
│   │ [ ] ▣  Oppenheimer (2023) · 1080p                            8.1 GB  │   │
│   │        Replaced by 2160p version                           Why safe? │   │
│   ├──────────────────────────────────────────────────────────────────────┤   │
│   │ [✓] ▣  The Office · S05E12                                   1.4 GB  │   │
│   │        Watched 4 weeks ago                                 Why safe? │   │
│   ├──────────────────────────────────────────────────────────────────────┤   │
│   │ [✓] ▣  The Bear · S02E05                                     2.0 GB  │   │
│   │        Watched 5 weeks ago                                 Why safe? │   │
│   ├──────────────────────────────────────────────────────────────────────┤   │
│   │ [✓] ▣  Top Gun: Maverick (2022) · 1080p                      5.8 GB  │   │
│   │        Replaced by 2160p version                           Why safe? │   │
│   ├──────────────────────────────────────────────────────────────────────┤   │
│   │ [✓] ▣  Better Call Saul · S06E13                             2.6 GB  │   │
│   │        Watched 3 months ago                                Why safe? │   │
│   ├──────────────────────────────────────────────────────────────────────┤   │
│   │ [✓] ▣  Avatar (2009) · 1080p                                 4.7 GB  │   │
│   │        Replaced by 2160p version                           Why safe? │   │
│   └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   ────────────────────────────────────────────────────────────────────────   │
│                                                                              │
│   [ Recover 32 GB ]                                                  Cancel  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

Selected rows show a 3px left bar in `--accent` (per Foundation §9.6). Unchecked rows show no bar and the checkbox empty.

## Tablet Mockup

Identical structure; list rows compress horizontally. "Why safe?" stays right-aligned. Bottom action bar remains.

```
┌────────────────────────────────────────────────┐
│ ← Recover Space                                │
├────────────────────────────────────────────────┤
│                                                │
│ Safe to remove — 12 items, 38 GB               │
│ Uncheck anything you want to keep.             │
│                                                │
│ 10 selected · 32 GB                Select all  │
│                                                │
│ [✓] ▣ Friends · S03            4.2 GB · Why?   │
│ [ ] ▣ Oppenheimer (2023) 1080p 8.1 GB · Why?   │
│ [✓] ▣ The Office · S05E12      1.4 GB · Why?   │
│ [✓] ▣ The Bear · S02E05        2.0 GB · Why?   │
│ [✓] ▣ Top Gun: Maverick 1080p  5.8 GB · Why?   │
│ ...                                            │
│                                                │
│ ───────────────────────────────────────────    │
│ [ Recover 32 GB ]                      Cancel  │
└────────────────────────────────────────────────┘
```

## Mobile Mockup

```
┌────────────────────────┐
│ ← Safe items           │
├────────────────────────┤
│                        │
│ Safe to remove         │
│ 12 items, 38 GB        │
│ Uncheck what you keep. │
│                        │
│ 10 selected · 32 GB    │
│              Select all│
│                        │
│ [✓] ▣ Friends · S03    │
│       4.2 GB           │
│       Last watched     │
│       6 weeks ago      │
│              Why safe? │
│ ─────────────────────  │
│ [ ] ▣ Oppenheimer      │
│       (2023) · 1080p   │
│       8.1 GB           │
│       Replaced by 2160p│
│              Why safe? │
│ ─────────────────────  │
│ [✓] ▣ The Office       │
│       · S05E12         │
│       1.4 GB           │
│       Watched 4w ago   │
│              Why safe? │
│ ...                    │
│                        │
├────────────────────────┤
│ [ Recover 32 GB ]      │
│           Cancel       │
└────────────────────────┘
```

Bottom action bar is pinned above the bottom nav.

## Expert Mode variant (v1.1 S1)

Normal-mode layout unchanged. Expert adds:

- A per-row Meta line beneath the supporting line showing classification confidence: e.g., `Confidence: high · rule: watched-30d`. Uses `--text-muted`, Meta size.
- An "Apply to similar items" Ghost action in the selection meta row: appears only when ≥ 3 currently-selected rows share a rule attribution. Opens an inline confirmation strip that extends the selection to all matching candidates in the safe set.
- Keyboard: `Space` toggles the focused row's checkbox (already standard); `A` toggles Select all when focus is on the meta row.

No new tokens, no new components. The Expert variant reuses Foundation §9.6 row anatomy with one additional Meta line.

## States

- **Empty:** Should not reach this screen if there are no safe items (the entry button on Recover Space won't be present). If reached via deep link: "✓ No safe items right now." with Ghost "Back to Recover Space."
- **Loading:** Title and subtitle render; list shows 6 skeleton rows (checkbox square + 48×72 poster block + two text lines + 4ch size block + 8ch link block). Bottom button shows skeleton.
- **Healthy:** As pictured.
- **Warning:** None unique to this screen — warnings live on parent Recover Space screen.
- **Error — total list failed to load:** Section-level error inside the list area (Foundation §10.3): `--critical-quiet` surface, "We couldn't load safe items," `[ Retry ]`.

## Component Behavior

- **Safe Candidate Row — Default:** checkbox unchecked or checked per system default (all checked initially).
- **Safe Candidate Row — Hover:** entire row `--surface-raised`, checkbox + title gain mild emphasis, "Why safe?" link underlines.
- **Safe Candidate Row — Focus:** 2px `--accent` ring around the whole row when row is focused; checkbox focus takes precedence when the checkbox itself is tab-targeted.
- **Safe Candidate Row — Active:** 1px translate-y on row press for click-to-toggle target.
- **Safe Candidate Row — Selected:** checkbox accent-filled, 3px `--accent` left bar.
- **Live total:** Bottom primary button text updates immediately on toggle. No animation on the numeral — numbers change instantly (Foundation §7.3).
- **Select all:** Toggle. When all rows selected, label reads "Deselect all." When mixed, label reads "Select all." Indeterminate visual on the header checkbox if one is present (not pictured but allowed).
- **"Why safe?" link:** Opens Evidence Drawer from right; row remains visible underneath the backdrop.

## Example Content

- "Friends · S03 (complete season) — 4.2 GB — Last watched 6 weeks ago"
- "Oppenheimer (2023) · 1080p — 8.1 GB — Replaced by 2160p version"
- "The Office · S05E12 — 1.4 GB — Watched 4 weeks ago"
- Bottom button: "Recover 32 GB" (updates as user toggles).

Evidence drawer content for one row:

> **Why this is safe to remove**
>
> You watched this 28 days ago. No active seeding obligation. A 2160p version was added on 2026-05-12.
>
> - Watched 4 weeks ago
> - No seed ratio target outstanding
> - Replaced by 2160p · 12.6 GB
>
> [View item](Library link)

---

# 4. Risky Candidate Review

## Visual Intent

- **Trustworthy.** The system surfaces *why* and presents three equal choices.
- **Calm.** One item, one decision, no list of demands.
- **Invisible intelligence.** The Foundation says: plain language, no jargon. "Still seeding," not "ratio variance against policy."
- **Appliance-like.** Same layout every item. Progress indicator anchors the user in the flow.

## Layout

1. **Top bar:** "← Recover Space" left, "Item 1 of 3" right.
2. **Centered column, max 480px** (Foundation §9.7).
3. **Poster** (160×240, `--radius-md`), centered.
4. **Title** + **Size** (Meta) below.
5. **"Why this needs your judgment"** subtitle.
6. **Bulleted list** with `--caution` dot markers.
7. **"Why risky?"** right-aligned Ghost link (opens Evidence Drawer).
8. **Three buttons** of equal weight — Remove / Keep / Remind me in 7 days.
9. **Skip** Ghost link, bottom-right.

## Component Placement

**Above the fold:** entire judgment surface for one item; everything visible in one frame on standard desktop.
**Below the fold:** nothing — this is a single-screen decision.

**Hidden:** lifecycle timeline (visible in Expert Mode by default), full attribution chain (Inspect tab).

## Visual Hierarchy

- **Largest:** the poster (visual anchor, not text).
- **Second largest text:** Title at Title level.
- **Most important interaction:** the three decision buttons, equal weight.
- **Lowest priority:** "Skip" Ghost link.

## Desktop Mockup

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ← Recover Space                                              Item 1 of 3    │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                                                                              │
│                       ┌─────────────────────────────┐                        │
│                       │                             │                        │
│                       │                             │                        │
│                       │         [ poster ]          │                        │
│                       │                             │                        │
│                       │                             │                        │
│                       └─────────────────────────────┘                        │
│                                                                              │
│                            Andor · S02 (complete)                            │
│                                    18.2 GB                                   │
│                                                                              │
│   ────────────────────────────────────────────────────────────────────────   │
│                                                                              │
│   Why this needs your judgment                                               │
│                                                                              │
│   ●  Still seeding (0.4 ratio — target is 1.0)                               │
│   ●  Added 6 days ago                                                        │
│   ●  Watched yesterday                                                       │
│                                                                              │
│                                                            Why risky?      │
│   ────────────────────────────────────────────────────────────────────────   │
│                                                                              │
│   [   Remove   ]      [   Keep   ]      [   Remind me in 7 days   ]          │
│                                                                              │
│                                                                      Skip    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

Three buttons are equal width, Secondary visual weight. "Remove" text uses `--critical` color; background remains `--surface-raised`. No red fill (Foundation §9.7).

**Final summary state** (after last item decided):

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ← Recover Space                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                                                                              │
│                   ✓  Reviewed 3 items.                                       │
│                                                                              │
│                      1 removed · 1 kept · 1 deferred                         │
│                                                                              │
│                          [ Back to Recover Space ]                           │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Tablet Mockup

Identical to desktop, narrower poster (140×210), three buttons stay in a row if width permits, else stack as on mobile.

```
┌────────────────────────────────────────────────┐
│ ← Recover               Item 1 of 3            │
├────────────────────────────────────────────────┤
│                                                │
│            ┌────────────────────┐              │
│            │                    │              │
│            │     [ poster ]     │              │
│            │                    │              │
│            └────────────────────┘              │
│                                                │
│           Andor · S02 (complete)               │
│                   18.2 GB                      │
│                                                │
│ ───────────────────────────────────────────    │
│ Why this needs your judgment                   │
│  ● Still seeding (0.4 ratio — target is 1.0)   │
│  ● Added 6 days ago                            │
│  ● Watched yesterday                           │
│                              Why risky?      │
│ ───────────────────────────────────────────    │
│                                                │
│ [  Remove  ]  [  Keep  ]  [ Remind 7 days ]    │
│                                                │
│                                       Skip     │
└────────────────────────────────────────────────┘
```

## Mobile Mockup

```
┌────────────────────────┐
│ ← Recover  Item 1 of 3 │
├────────────────────────┤
│                        │
│      ┌──────────┐      │
│      │          │      │
│      │ [poster] │      │
│      │          │      │
│      └──────────┘      │
│                        │
│  Andor · S02           │
│  (complete)            │
│      18.2 GB           │
│                        │
│ ───────────────────    │
│ Why this needs your    │
│ judgment               │
│                        │
│ ● Still seeding (0.4)  │
│ ● Added 6 days ago     │
│ ● Watched yesterday    │
│                        │
│         Why risky?   │
│ ───────────────────    │
│                        │
│ ┌────────────────────┐ │
│ │      Remove        │ │
│ └────────────────────┘ │
│ ┌────────────────────┐ │
│ │       Keep         │ │
│ └────────────────────┘ │
│ ┌────────────────────┐ │
│ │ Remind in 7 days   │ │
│ └────────────────────┘ │
│                Skip    │
├────────────────────────┤
│  🏠   ↻   📚   ⚕   ⚙   │
└────────────────────────┘
```

## Expert Mode variant (v1.1 S2)

Normal-mode layout unchanged. Expert adds, below the bulleted "Why this needs your judgment" list and before the divider:

- **Compact lifecycle timeline** (Foundation §9, Activity Timeline — Compact form) showing the 4–6 most recent events for the item, expanded by default. No "Show more" affordance — the timeline is already part of the page.
- **Source trail snippet:** 3-line cross-reference summary (Library / qBittorrent / *arr / Overseerr) with match indicators. Mirrors Mockups §6 Source trail anatomy in compressed form.
- **"Apply to similar items" Ghost action** below the three decision buttons, left-aligned. Click opens an inline confirmation strip describing how many other risky candidates match the current decision's heuristics.
- **Keyboard shortcut hint** (Meta, `--text-muted`) pinned at the bottom of the screen: `R Remove   K Keep   L Later   S Skip`. Active only in Expert Mode per Foundation §11.4.

No new tokens, no new components.

## States

- **Empty:** "No items need your judgment right now. ✓" with Ghost "Back to Recover Space." Should rarely be reached directly.
- **Loading:** Skeleton poster (160×240), title skeleton (24ch), size skeleton (8ch), three bulleted skeleton lines (40–55ch), three button skeletons preserved at full width. No spinner.
- **Healthy (default):** As pictured.
- **Warning — Remind already set:** "Reminders scheduled for 1 item." Inline meta below the buttons; no color change.
- **Error — decision failed to save:** Inline error below the buttons, `--critical` Meta: "Couldn't save your decision. [Retry]" Item stays in view.

## Component Behavior

- **Decision buttons — Default:** Three Secondary buttons, equal width, 12px gap (desktop), full-width stacked (mobile).
- **Decision buttons — Hover:** background `--surface-raised`, no scale. Remove gets a subtle `--critical-quiet` tint on hover only.
- **Decision buttons — Focus:** 2px `--accent` ring (Remove also uses `--accent` ring, not red — focus is consistent across all buttons site-wide).
- **Decision buttons — Active:** 1px translate-y, ≤80ms.
- **After selection:** Next item loads with `--motion-base` crossfade. Item count updates ("Item 2 of 3").
- **"Why risky?" — opens Evidence Drawer** (right on desktop, full-screen on mobile).
- **Skip:** Defers the item but does not record a decision. Item returns to the queue on next Recover Space visit.

## Example Content

- Title: "Andor · S02 (complete)"
- Size: "18.2 GB"
- Bullets (plain language only):
  - "Still seeding (0.4 ratio — target is 1.0)"
  - "Added 6 days ago"
  - "Watched yesterday"
- Buttons: "Remove", "Keep", "Remind me in 7 days"

Evidence drawer:

> **Why this is risky**
>
> This item is still actively seeding and was added recently, so removing it now may waste the upload you've already contributed.
>
> - Seed ratio 0.4 (target 1.0)
> - Added 2026-05-27
> - Last watched 2026-06-01
> - 9 other peers connected

---

# 5. Library

## Visual Intent

- **Appliance-like.** Inventoried. Confident. Reads like a catalog, not a database.
- **Calm.** Search bar present, but not loud. Status badges do the heavy lifting.
- **Invisible intelligence.** "Imported," "Downloading," "Stuck" — never "engine matched."

## Layout

1. **Global header** (same as Home).
2. **Screen title** "Library".
3. **Search bar** (40px, full width within 960px column).
4. **Filter chip row** (Foundation §9.16) with Sort dropdown right-aligned.
5. **List of Library Item Rows** (Foundation §9.5).
6. **Paging meta + Load more** at the bottom.

## Component Placement

**Above the fold:** header, title, search, filter row, first 6–8 item rows.
**Below the fold:** remaining rows, "Load more" affordance.

**Hidden:** item detail (opens as drawer right, or full-screen on mobile).

## Visual Hierarchy

- **Largest:** screen title "Library" (Title size).
- **Second:** search input (40px, prominent placeholder).
- **Third:** item titles in rows.
- **Lowest:** status badges, meta line, "Load more" Ghost.

## Desktop Mockup

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Handoffarr        Home   Recover   Library   Health   Settings        [SP] │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Library                                                                    │
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐   │
│   │ 🔍  Search titles…                                                   │   │
│   └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   ( All )  ( Movies )  ( Shows )  ( Music )                Sort: Recently ▾  │
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐   │
│   │ ▣  The Pitt · S01E08                                                 │   │
│   │    Show · 2.1 GB                                  ✓ Imported · 2h    │   │
│   ├──────────────────────────────────────────────────────────────────────┤   │
│   │ ▣  Severance · S02E10                                                │   │
│   │    Show · 1.8 GB                                  ✓ Imported · 1d    │   │
│   ├──────────────────────────────────────────────────────────────────────┤   │
│   │ ▣  Mickey 17 (2025)                                                  │   │
│   │    Movie · 6.4 GB                                ⟳ Downloading · 67% │   │
│   ├──────────────────────────────────────────────────────────────────────┤   │
│   │ ▣  Untitled Request                                                  │   │
│   │    Show · —                                       ⏸ Stuck · 3d      │   │
│   ├──────────────────────────────────────────────────────────────────────┤   │
│   │ ▣  Dune: Part Two (2024)                                             │   │
│   │    Movie · 14.2 GB                                ✓ Imported · 2d    │   │
│   ├──────────────────────────────────────────────────────────────────────┤   │
│   │ ▣  Shōgun · S01E04                                                   │   │
│   │    Show · 2.3 GB                                  ✓ Imported · 3d    │   │
│   └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   Showing 25 of 1,247                                              Load more │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

`( All )` shown with `--accent` background indicates selected chip; remaining chips are `--surface-raised`.

## Tablet Mockup

```
┌────────────────────────────────────────────────┐
│ Handoffarr   Home  Recover  Library  …    [SP]│
├────────────────────────────────────────────────┤
│ Library                                        │
│                                                │
│ ┌──────────────────────────────────────────┐   │
│ │ 🔍 Search titles…                        │   │
│ └──────────────────────────────────────────┘   │
│                                                │
│ (All) (Movies) (Shows) (Music)  Sort: Recent ▾ │
│                                                │
│ ▣ The Pitt · S01E08          ✓ Imported · 2h   │
│   Show · 2.1 GB                                │
│ ────────────────────────────────────────       │
│ ▣ Severance · S02E10         ✓ Imported · 1d   │
│   Show · 1.8 GB                                │
│ ────────────────────────────────────────       │
│ ▣ Mickey 17 (2025)        ⟳ Downloading 67%    │
│   Movie · 6.4 GB                               │
│ ────────────────────────────────────────       │
│ ▣ Untitled Request          ⏸ Stuck · 3d       │
│   Show · —                                     │
│                                                │
│ Showing 25 of 1,247                Load more   │
└────────────────────────────────────────────────┘
```

## Mobile Mockup

```
┌────────────────────────┐
│ Library           [SP] │
├────────────────────────┤
│ ┌────────────────────┐ │
│ │ 🔍 Search…         │ │
│ └────────────────────┘ │
│                        │
│ (All) (Mov) (Shw) (♪)  │
│ Sort: Recent ▾         │
│                        │
│ ▣ The Pitt · S01E08    │
│   Show · 2.1 GB        │
│   ✓ Imported · 2h      │
│ ─────────────────────  │
│ ▣ Severance · S02E10   │
│   Show · 1.8 GB        │
│   ✓ Imported · 1d      │
│ ─────────────────────  │
│ ▣ Mickey 17 (2025)     │
│   Movie · 6.4 GB       │
│   ⟳ Downloading · 67%  │
│ ─────────────────────  │
│ ▣ Untitled Request     │
│   Show · —             │
│   ⏸ Stuck · 3d         │
│                        │
│ 25 of 1,247  Load more │
├────────────────────────┤
│  🏠   ↻   📚   ⚕   ⚙   │
└────────────────────────┘
```

## States

- **Empty (no items at all):**
  ```
     Library

     Your library is empty.
     Once Sonarr or Radarr imports something, it shows up here.

     [ Open Sonarr ]   [ Open Radarr ]
  ```
- **Empty (no results for search):** Below search bar inside the list area: "No items match '`<query>`'." with Ghost "Clear search."
- **Loading:** 8 skeleton rows (poster + title line + meta line + status badge block). Search and filter chrome remain rendered and interactive.
- **Healthy:** As pictured.
- **Warning — Some items stuck:** Stuck rows show `⏸` badge in `--caution` strong. No section-level warning; per-row.
- **Error — failed to load:** Section-level error in the list area with `[ Retry ]`.

## Component Behavior

- **Search input — Default / Focus:** Default border `--border-strong`; focus border replaced by 2px `--accent` (Foundation §9.13). Placeholder `--text-subtle`.
- **Search — Typing:** instant client-side filter on the current loaded set; debounced server query on backspace pause.
- **Filter chip — Default:** `--surface-raised` background, `--text` text.
- **Filter chip — Selected:** `--accent` background, `--accent-on` text. Single-select default.
- **Filter chip — Hover:** ≤4% accent overlay. Active: 1px translate-y.
- **Sort dropdown — Ghost trigger, chevron** 16px. Opens popover (Foundation `--elev-2`) with sort options.
- **Library Row — Default:** Hairline `--border` between rows; no row borders top or bottom of the list.
- **Library Row — Hover:** background `--surface-raised`. Entire row is the click target.
- **Library Row — Focus:** 2px `--accent` ring around the row.
- **Library Row — Active:** 1px translate-y.
- **Click row:** Opens Item Detail drawer (desktop/tablet) or navigates to full-screen Item Detail (mobile).
- **Load more:** Ghost button; on click, appends next page, scroll position preserved.

## Example Content

- "The Pitt · S01E08 — Show · 2.1 GB — ✓ Imported · 2h"
- "Severance · S02E10 — Show · 1.8 GB — ✓ Imported · 1d"
- "Mickey 17 (2025) — Movie · 6.4 GB — ⟳ Downloading · 67%"
- "Untitled Request — Show · — — ⏸ Stuck · 3d"
- "Dune: Part Two (2024) — Movie · 14.2 GB — ✓ Imported · 2d"
- "Showing 25 of 1,247"

---

# 5A. Library — Expert Mode variant (v1.1 S3)

## Visual Intent

Same as Normal Library. Expert adds bulk selection and additional sort/filter affordances. No re-layout, no new component primitives.

## Layout deltas vs. §5

1. **Filter chip row** gains an additional `Source` Ghost dropdown (right of the existing Sort dropdown) with options: `All`, `Sonarr`, `Radarr`, `Lidarr`, `qBittorrent`, `Overseerr`.
2. **Sort dropdown** gains options: `Recently added`, `Size (largest)`, `Size (smallest)`, `Lifecycle stage`, `Source`.
3. **Library rows** gain a 16px checkbox at the far left (Foundation §9.6 Safe Candidate Row pattern, reused).
4. **Sticky bulk-action bar** at the bottom of the viewport appears when ≥ 1 row is selected, containing `[ Flag for cleanup ]` Secondary and `[ Remove from library ]` destructive Primary, plus a `Cancel` Ghost.

## Desktop Mockup

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Handoffarr        Home   Recover   Library   Health   Settings    [EXPERT] │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Library                                                                    │
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐   │
│   │ 🔍  Search titles…                                                   │   │
│   └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   ( All )  ( Movies )  ( Shows )  ( Music )    Sort: Recently ▾  Source ▾   │
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐   │
│   │ [✓] ▣  The Pitt · S01E08                       ✓ Imported · 2h       │   │
│   │        Show · 2.1 GB                                                 │   │
│   ├──────────────────────────────────────────────────────────────────────┤   │
│   │ [ ] ▣  Severance · S02E10                      ✓ Imported · 1d       │   │
│   │        Show · 1.8 GB                                                 │   │
│   ├──────────────────────────────────────────────────────────────────────┤   │
│   │ [✓] ▣  Mickey 17 (2025)                       ⟳ Downloading · 67%   │   │
│   │        Movie · 6.4 GB                                                │   │
│   ├──────────────────────────────────────────────────────────────────────┤   │
│   │ [ ] ▣  Untitled Request                         ⏸ Stuck · 3d         │   │
│   │        Show · —                                                      │   │
│   └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   Showing 25 of 1,247                                              Load more │
│                                                                              │
│   ────────────────────────────────────────────────────────────────────────   │
│   2 selected · 8.5 GB    [ Flag for cleanup ]   [ Remove from library ]  Cancel │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Tablet Mockup

Same structure; bulk-action bar pins to the bottom of the content area. Filter row may wrap (Source dropdown drops to a second line).

## Mobile Mockup

Same as §5 Mobile, with:
- Per-row checkbox added on the left.
- Bulk-action bar pins above the bottom nav when ≥ 1 row is selected, with the two destructive buttons stacked.

## Component Behavior

- **Checkbox toggling:** Tap target is the checkbox only; tapping the rest of the row still opens Item Detail. Long-press on mobile activates select mode (selects the long-pressed row and reveals the bulk-action bar).
- **Bulk-action bar — Visibility:** Appears with `--motion-base` ease when first selection is made; hides when selection drops to 0.
- **`Flag for cleanup` — Secondary:** Click opens inline confirmation strip with selection summary.
- **`Remove from library` — destructive Primary:** Click opens inline confirmation strip with selection summary and explicit warning ("These items will be moved to trash. You can restore from Cleanup History for 24h."). Routes through the same Undo-window mechanism as Recover Space (Foundation §9.12).
- **`Cancel` — Ghost:** Clears selection.

## States

- **Empty selection:** Bulk-action bar absent.
- **Selection ≥ 1:** Bulk-action bar visible with live count and total size.
- **Bulk action in progress:** Top progress strip (Foundation §10.2).
- **Bulk action partial failure:** Same partial-success pattern as Recover Space.

## Expert Mode density

Per Foundation §14.2, Expert Mode default density is `compact`. Row vertical padding reduces from 16px → 12px; section gaps from 32px → 24px. No type, color, or component changes.

---

# 6. Item Detail

## Visual Intent

- **Premium.** A respectful detail page. The item is the hero.
- **Calm.** Compact recent activity, never a wall of timestamps.
- **Trustworthy.** Single contextual primary action, plain language.

## Layout (Normal Mode)

1. **Top bar:** "← Library" back link.
2. **Header block:** poster (left, 144×216), title + meta + status badge (right column).
3. **Contextual action button(s)** in a row right of the meta block ("Open in Sonarr").
4. **"Recent activity"** section (compact timeline, 3–5 events).
5. **Footer action row:** "Flag for cleanup" (Secondary), "Remove from library" (destructive Primary).

Drawer width 480px on desktop; full-screen on mobile.

## Component Placement

**Above the fold:** header block, contextual action, top 3 activity events.
**Below the fold:** remaining activity events, footer action row.

**Hidden in Normal:** full lifecycle timeline, source trail, attribution data. Visible in Expert Mode via tabs (see Mockup Variant below).

## Visual Hierarchy

- **Largest:** poster image.
- **Largest text:** item title (Title size).
- **Second:** contextual primary button.
- **Lowest priority:** activity timestamps (Meta).

## Desktop Mockup (Normal Mode, drawer)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                       │ ← Library                          ✕ │
│                                       ├──────────────────────────────────────│
│         (Library still visible        │                                      │
│          behind, dimmed 30%)          │ ┌──────────────┐                     │
│                                       │ │              │  Severance · S02E10 │
│                                       │ │  [ poster ]  │  Show · 1.8 GB ·    │
│                                       │ │              │  2160p              │
│                                       │ │              │                     │
│                                       │ └──────────────┘  ✓ Imported · 1d    │
│                                       │                                      │
│                                       │                  [ Open in Sonarr ]  │
│                                       │                                      │
│                                       │ ─────────────────────────────────── │
│                                       │ Recent activity                     │
│                                       │                                      │
│                                       │ • Imported into library             │
│                                       │   Yesterday, 8:14 PM                │
│                                       │ • Download completed                │
│                                       │   Yesterday, 7:52 PM                │
│                                       │ • Grabbed by Sonarr                 │
│                                       │   Yesterday, 6:18 PM                │
│                                       │                                      │
│                                       │ ─────────────────────────────────── │
│                                       │                                      │
│                                       │ [ Flag for cleanup ]                │
│                                       │ [ Remove from library ]             │
│                                       │                                      │
└──────────────────────────────────────────────────────────────────────────────┘
```

Drawer background `--surface-raised`, `--elev-2`. Close affordance top-right (16px X, Ghost).

## Desktop Mockup (Expert Mode, full pane with tabs)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ← Library                                                          [EXPERT]  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────┐                                                           │
│   │              │   Severance · S02E10  ·  1.8 GB  ·  2160p                 │
│   │  [ poster ]  │   ✓ Imported · 2026-06-01 20:14                           │
│   │              │                                                           │
│   └──────────────┘                       [ Open in Sonarr ]                  │
│                                                                              │
│   [ Overview ]   [ History ]   [ Source trail ]   [ Inspect ]                │
│                                                                              │
│   ─── HISTORY ──────────────────────────────────────────────────             │
│                                                                              │
│   ●  Imported into library                  Jun 1, 8:14 PM                   │
│   │     path: /media/shows/Severance/S02/Severance.S02E10.2160p.mkv         │
│   ●  Download completed                     Jun 1, 7:52 PM                   │
│   │     qBittorrent · hash a7f3b8c2…                                        │
│   ●  Download started                       Jun 1, 6:21 PM                   │
│   │     indexer: Indexer-X · seeders: 47                                    │
│   ●  Grabbed by Sonarr                      Jun 1, 6:18 PM                   │
│   │     release: Severance.S02E10.2160p.WEB-DL.x265                         │
│   ●  Requested via Overseerr                May 28, 9:02 AM                  │
│                                                                              │
│   ─── SOURCE TRAIL ─────────────────────────────────────────────             │
│   Library entry    ← Sonarr import                  ✓ matched                │
│   qBittorrent      ← hash a7f3b8c2…                 ✓ owned by Sonarr        │
│   Sonarr           ← release grab                   ✓ confirmed              │
│   Overseerr        ← request #4821                  ✓ fulfilled              │
│                                                                              │
│   [ Override classification ]    [ Force re-verify ]                         │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Tablet Mockup

```
┌────────────────────────────────────────────────┐
│ ← Library                                   ✕  │
├────────────────────────────────────────────────┤
│                                                │
│ ┌──────────────┐                               │
│ │              │ Severance · S02E10            │
│ │  [ poster ]  │ Show · 1.8 GB · 2160p         │
│ │              │ ✓ Imported · 1d               │
│ └──────────────┘                               │
│                                                │
│              [ Open in Sonarr ]                │
│                                                │
│ ──────────────────────────────────────────     │
│ Recent activity                                │
│ • Imported into library  Yesterday, 8:14 PM    │
│ • Download completed     Yesterday, 7:52 PM    │
│ • Grabbed by Sonarr      Yesterday, 6:18 PM    │
│ ──────────────────────────────────────────     │
│                                                │
│ [ Flag for cleanup ]                           │
│ [ Remove from library ]                        │
└────────────────────────────────────────────────┘
```

## Mobile Mockup

Item Detail on mobile is a **full-screen route**, not a drawer (Foundation/Blueprint mobile rule).

```
┌────────────────────────┐
│ ← Library              │
├────────────────────────┤
│                        │
│      ┌──────────┐      │
│      │          │      │
│      │ [poster] │      │
│      │          │      │
│      └──────────┘      │
│                        │
│  Severance · S02E10    │
│  Show · 1.8 GB · 2160p │
│  ✓ Imported · 1d       │
│                        │
│   [ Open in Sonarr ]   │
│                        │
│ ─────────────────────  │
│ Recent activity        │
│                        │
│ • Imported into        │
│   library              │
│   Yesterday, 8:14 PM   │
│                        │
│ • Download completed   │
│   Yesterday, 7:52 PM   │
│                        │
│ • Grabbed by Sonarr    │
│   Yesterday, 6:18 PM   │
│                        │
│ ─────────────────────  │
│                        │
│ [ Flag for cleanup ]   │
│ [ Remove from library ]│
│                        │
├────────────────────────┤
│  🏠   ↻   📚   ⚕   ⚙   │
└────────────────────────┘
```

## States

- **Empty:** Not reachable directly. If an item is deleted while detail is open: "This item has been removed. [ Back to Library ]."
- **Loading:** Header block skeleton (poster block + 2 text lines + status block); contextual button skeleton; 3 activity skeleton lines. Footer buttons skeleton.
- **Healthy:** As pictured.
- **Warning:** If item is `⏸ Stuck`, status badge in `--caution`; contextual primary becomes "View in Health" instead of "Open in Sonarr"; Inline note: "This item has shown no progress in 3 days."
- **Error:** If detail fails to load, section error inside drawer: "We couldn't load this item. [ Retry ]" — drawer remains open for navigation back.

## Component Behavior

- **Drawer — Expanded:** slides from right at `--motion-base`; backdrop fades to 30% black.
- **Drawer — Hover (close button):** Ghost hover treatment.
- **Drawer — Focus:** focus moves to drawer title on open; trapped within drawer; Esc closes; returns focus to invoking row.
- **Tabs (Expert):** Default tab is Overview. Selected tab shows `--accent` underline 2px, body switches content. No animation between tabs beyond `--motion-fast` crossfade of content area.
- **Activity timeline — Compact:** 3–5 most recent events, label + relative timestamp.
- **Activity timeline — Full (Expert):** Vertical timeline rail with event dots, per-event meta line in `--text-muted`.
- **Footer action row — "Remove from library":** Destructive Primary (`--critical` accent). Clicking opens Inline Confirmation Strip inside the drawer body, not a modal.

## Example Content

- Title: "Severance · S02E10"
- Meta: "Show · 1.8 GB · 2160p"
- Status: "✓ Imported · 1d" (Normal) / "✓ Imported · 2026-06-01 20:14" (Expert)
- Activity (Normal — relative):
  - Imported into library — Yesterday, 8:14 PM
  - Download completed — Yesterday, 7:52 PM
  - Grabbed by Sonarr — Yesterday, 6:18 PM
- Expert tab order: Overview / History / Source trail / Inspect.

---

# 7. Health

## Visual Intent

- **Trustworthy.** Plain language, broken things dominate, healthy things recede.
- **Calm.** Even with issues, the screen doesn't shout — `--caution` and `--critical` are used precisely, not decoratively.
- **Appliance-like.** Same tiles every visit, status changes drive content.

## Layout

1. **Global header.**
2. **Screen title** "Health".
3. **Status summary banner** (varies: critical / caution / clean).
4. **Integrations section** — header + bordered tile group with 5 integration rows.
5. **Stuck items section** — header + list of stuck Library Rows (compact variant) with per-row "Inspect" link. **v1.1 M4:** no `View →` link; stuck items are inline-only on Health. Per-row `Inspect` navigates to Item Detail with the stuck-state variant (see §6). If the list grows beyond ~10 items, paginate within this section — never promote to a dedicated screen.
6. **Recent issues** — chronological list (Expert mode adds severity).

## Component Placement

**Above the fold:** header, title, status summary banner, top of Integrations.
**Below the fold:** rest of Integrations, Stuck items section, Recent issues.

**Hidden:** validation report internals, raw diagnostics (link to Diagnostics in Expert Mode).

## Visual Hierarchy

- **Largest text:** the status summary banner ("⚠ 2 issues need attention" or "✓ Everything connected").
- **Visually dominant on warning:** the broken integration row, with strong `--caution`/`--critical` icon and `[ Fix ]` Primary button.
- **Recedes:** healthy integration rows, in `--text-muted` for right-column text.
- **Lowest priority:** the "Recent issues" list timestamps.

## Desktop Mockup (warning state)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Handoffarr        Home   Recover   Library   Health   Settings        [SP] │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Health                                                                     │
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐   │
│   │  ⚠  2 issues need attention                                          │   │
│   └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   Integrations                                                               │
│   ┌──────────────────────────────┬───────────────────────────────────────┐   │
│   │ ⚠ qBittorrent                │ Connection refused              [Fix] │   │
│   │   Last seen 12m ago          │                                       │   │
│   ├──────────────────────────────┼───────────────────────────────────────┤   │
│   │ ✓ Sonarr                     │ Connected                             │   │
│   │   Last seen just now         │                                       │   │
│   ├──────────────────────────────┼───────────────────────────────────────┤   │
│   │ ✓ Radarr                     │ Connected                             │   │
│   │   Last seen just now         │                                       │   │
│   ├──────────────────────────────┼───────────────────────────────────────┤   │
│   │ ✓ Lidarr                     │ Connected                             │   │
│   │   Last seen 1m ago           │                                       │   │
│   ├──────────────────────────────┼───────────────────────────────────────┤   │
│   │ ✓ Overseerr                  │ Connected                             │   │
│   │   Last seen just now         │                                       │   │
│   └──────────────────────────────┴───────────────────────────────────────┘   │
│                                                                              │
│   Stuck items                                                                │
│   ┌──────────────────────────────────────────────────────────────────────┐   │
│   │ ⏸  Untitled Request                                                  │   │
│   │    no progress in 3 days                                  Inspect    │   │
│   └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   Recent issues                                                              │
│   • qBittorrent unreachable               12 min ago                         │
│   • Sonarr search timed out (resolved)    4 hours ago                        │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Tablet Mockup

```
┌────────────────────────────────────────────────┐
│ Handoffarr   Home  Recover  Library Hlth  [SP]│
├────────────────────────────────────────────────┤
│ Health                                         │
│                                                │
│ ┌──────────────────────────────────────────┐   │
│ │ ⚠ 2 issues need attention                │   │
│ └──────────────────────────────────────────┘   │
│                                                │
│ Integrations                                   │
│ ┌──────────────────────────────────────────┐   │
│ │ ⚠ qBittorrent      Connection refused    │   │
│ │   12m ago                        [Fix]   │   │
│ ├──────────────────────────────────────────┤   │
│ │ ✓ Sonarr           Connected             │   │
│ ├──────────────────────────────────────────┤   │
│ │ ✓ Radarr           Connected             │   │
│ ├──────────────────────────────────────────┤   │
│ │ ✓ Lidarr           Connected             │   │
│ ├──────────────────────────────────────────┤   │
│ │ ✓ Overseerr        Connected             │   │
│ └──────────────────────────────────────────┘   │
│                                                │
│ Stuck items                                    │
│ ⏸ Untitled Request · no progress 3d   Inspect  │
│                                                │
│ Recent issues                                  │
│ • qBittorrent unreachable        12 min ago    │
│ • Sonarr search timed out         4 hours ago  │
└────────────────────────────────────────────────┘
```

## Mobile Mockup

```
┌────────────────────────┐
│ Health            [SP] │
├────────────────────────┤
│ ┌────────────────────┐ │
│ │ ⚠ 2 issues need    │ │
│ │   attention        │ │
│ └────────────────────┘ │
│                        │
│ Integrations           │
│ ┌────────────────────┐ │
│ │ ⚠ qBittorrent      │ │
│ │   12m ago          │ │
│ │   Connection       │ │
│ │   refused          │ │
│ │           [ Fix ]  │ │
│ ├────────────────────┤ │
│ │ ✓ Sonarr           │ │
│ │   Connected        │ │
│ ├────────────────────┤ │
│ │ ✓ Radarr           │ │
│ │   Connected        │ │
│ ├────────────────────┤ │
│ │ ✓ Lidarr           │ │
│ │   Connected        │ │
│ ├────────────────────┤ │
│ │ ✓ Overseerr        │ │
│ │   Connected        │ │
│ └────────────────────┘ │
│                        │
│ Stuck items            │
│ ⏸ Untitled Request     │
│   no progress · 3d     │
│           Inspect      │
│                        │
│ Recent issues          │
│ • qBittorrent          │
│   unreachable          │
│   12 min ago           │
│ • Sonarr search        │
│   timed out (resolved) │
│   4 hours ago          │
├────────────────────────┤
│  🏠   ↻   📚   ⚕   ⚙   │
└────────────────────────┘
```

## States

- **Empty (clean):**
  ```
     Health

     ✓  Everything connected.
        Last full check 4 minutes ago.

        [ Run a check now ]
  ```
  Foundation §10.1 calm-empty pattern. Integrations and Stuck items sections still render, both showing healthy / "no stuck items" states.
- **Loading:** Banner skeleton (one line), integration tile group skeleton (5 rows of label + status block + button-shaped block), stuck items section skeleton.
- **Healthy:** Summary banner uses `--success-quiet` background, `check-circle ✓` icon, copy "Everything connected." No `[Fix]` buttons anywhere.
- **Warning:** As pictured.
- **Critical:** Summary banner uses `--critical-quiet` background, `alert-octagon ✕` icon, copy "X critical issues." First integration row shows critical badge instead of caution. Numeral and icon in banner colored `--critical`.

## Component Behavior

- **Status summary banner:** Always renders. Content driven by state machine. Crossfade `--motion-slow` on state change. No primary button on banner — actions are per-tile.
- **Integration tile group:** One bordered group (Foundation §5.3 legitimate border use). Rows separated by 1px `--border`.
- **Integration tile — Default:** Status icon + name + last-seen meta.
- **Integration tile — Healthy:** Right column "Connected" in `--text-muted`.
- **Integration tile — Warning/Critical:** Right column plain-language error + `[ Fix ]` Primary button (small size).
- **Integration tile — Hover:** background `--surface-raised`. Entire tile is the click target (navigates to Integration Detail).
- **Integration tile — Focus:** 2px `--accent` ring around tile.
- **`[ Fix ]` button — Hover/Focus/Active:** standard primary button behavior.
- **Stuck item row — Default / Hover:** Library Row variant (compact); hover background `--surface-raised`.
- **"Inspect" link — Ghost link**, `--accent` color, underline on hover.
- **Recent issues:** Plain bullet list. Items in `--text-muted`. Resolved issues show "(resolved)" inline.

## Example Content

- Banner: "⚠ 2 issues need attention" (caution) / "✓ Everything connected." (clean) / "✕ 1 critical issue" (critical)
- Integrations: qBittorrent (broken), Sonarr / Radarr / Lidarr / Overseerr (healthy)
- Stuck items: "Untitled Request — no progress in 3 days"
- Recent issues: "qBittorrent unreachable — 12 min ago"; "Sonarr search timed out (resolved) — 4 hours ago"

---

# 7A. Integration Detail — v1.1 M1

## Visual Intent

- **Trustworthy.** Plain-language error, an explicit test action, a clear path to fix.
- **Calm.** No log dump in Normal Mode. The page reads as a settings panel for one integration.
- **Appliance-like.** Same layout for every integration; status drives content.

## Layout

1. **Top bar:** "← Health" back-link left.
2. **Integration header:** name + current status badge + last-successful-contact meta.
3. **Status description card:** plain-language explanation of current state (and, if broken, the error in plain language).
4. **Primary action row:** `[ Test connection ]` Primary (or `[ Reconnect ]` after settings change).
5. **Settings section (collapsed by default):** `[ Edit settings ]` Secondary; expands to inline form (URL, credentials/API key).
6. **`View logs`** Ghost link (Expert only) — opens Diagnostics filtered to this integration.

Single column, max 720px.

## Component Placement

**Above the fold:** header, status description, primary action.
**Below the fold:** Edit settings inline editor (if engaged), `View logs` link (Expert).

**Hidden:** Raw logs / stack traces (Expert Diagnostics).

## Visual Hierarchy

- **Largest text:** integration name (Title size).
- **Second:** status description body.
- **Most important interaction:** `[ Test connection ]` Primary.
- **Lowest priority:** last-contact meta, `View logs` Ghost.

## Desktop Mockup (warning state, qBittorrent unreachable)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ← Health                                                                     │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   qBittorrent                                                                │
│   ⚠  Connection refused · Last successful contact: 12 min ago                │
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐   │
│   │  We can't reach qBittorrent at http://localhost:8080.                │   │
│   │                                                                      │   │
│   │  Suggested fix: confirm qBittorrent is running and accepting         │   │
│   │  connections on port 8080.                                           │   │
│   └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   [ Test connection ]     [ Edit settings ]                                  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Edit settings — expanded** (inline below the action row):

```
   ┌──────────────────────────────────────────────────────────────────────┐
   │  URL          [ http://localhost:8080                            ]   │
   │  Username     [ admin                                            ]   │
   │  Password     [ ••••••••                                         ]   │
   │                                                                      │
   │  [ Save and test ]                                       Cancel      │
   └──────────────────────────────────────────────────────────────────────┘
```

**Healthy state** (collapsed):

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ← Health                                                                     │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Sonarr                                                                     │
│   ✓  Connected · Last successful contact: just now                           │
│                                                                              │
│   [ Test connection ]     [ Edit settings ]                                  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Expert mode (additions):**

```
   [ Test connection ]     [ Edit settings ]                       View logs →
```

## Tablet Mockup

```
┌────────────────────────────────────────────────┐
│ ← Health                                       │
├────────────────────────────────────────────────┤
│ qBittorrent                                    │
│ ⚠ Connection refused                           │
│ Last contact: 12 min ago                       │
│                                                │
│ ┌──────────────────────────────────────────┐   │
│ │ We can't reach qBittorrent at            │   │
│ │ http://localhost:8080.                   │   │
│ │                                          │   │
│ │ Suggested fix: confirm qBittorrent is    │   │
│ │ running and accepting connections        │   │
│ │ on port 8080.                            │   │
│ └──────────────────────────────────────────┘   │
│                                                │
│ [ Test connection ]   [ Edit settings ]        │
└────────────────────────────────────────────────┘
```

## Mobile Mockup

```
┌────────────────────────┐
│ ← Health               │
├────────────────────────┤
│ qBittorrent            │
│ ⚠ Connection refused   │
│ Last contact:          │
│ 12 min ago             │
│                        │
│ We can't reach         │
│ qBittorrent at         │
│ http://localhost:8080. │
│                        │
│ Suggested fix:         │
│ confirm qBittorrent    │
│ is running and         │
│ accepting connections  │
│ on port 8080.          │
│                        │
│ [ Test connection ]    │
│ [ Edit settings    ]   │
│                        │
├────────────────────────┤
│  🏠   ↻   📚   ⚕   ⚙   │
└────────────────────────┘
```

## States

- **Empty:** Not reachable directly.
- **Loading:** Header skeleton (name + status block); description card skeleton (3 lines); action button skeleton.
- **Healthy:** Status badge `✓ Connected`, no description card (the meta line carries the message). Both buttons present.
- **Warning:** As pictured (qBittorrent example).
- **Critical:** Status badge uses `--critical`; description card surface `--critical-quiet`; primary button text reads `Reconnect` once settings have been edited.
- **Test in progress:** `[ Test connection ]` shows inline loader spinner; row body shows "Testing…" Meta.
- **Test succeeded after fix:** Description card replaced with Success Banner: "✓ Connection restored. Last successful contact: just now."
- **Test failed:** Description card persists; new plain-language hint appended below: "Test failed: timed out after 5 s. [ Retry ]".

## Component Behavior

- **`Test connection` — Primary.** Click triggers a single test; result updates header status + description.
- **`Edit settings` — Secondary.** Click expands inline editor below the action row (`--motion-base` height ease). Form rows follow Foundation §9.13 input language.
- **`Save and test` — Primary** inside the inline editor. Saves and immediately tests.
- **`Cancel` — Ghost** inside the inline editor. Collapses editor without saving.
- **`View logs →` (Expert) — Ghost link.** Navigates to Diagnostics with a pre-applied filter for this integration.

## Expert Mode variant

- Adds a `View logs →` Ghost link in the action row (right-aligned).
- After a test, adds a small Meta line showing request method/URL and response time (e.g., `GET /api/v2/app/version → 200 in 42 ms`).
- No new tokens, no new components.

## Example Content

- "qBittorrent — ⚠ Connection refused · Last successful contact: 12 min ago"
- "We can't reach qBittorrent at http://localhost:8080."
- "Suggested fix: confirm qBittorrent is running and accepting connections on port 8080."
- Healthy alternate: "Sonarr — ✓ Connected · Last successful contact: just now"

---

# 8. Settings

## Visual Intent

- **Premium.** Settings is where homelab users live. Tactile, well-organized, no enterprise SaaS clutter.
- **Calm.** No nested accordions, no chrome-heavy section panels — sectioned cards with clear headers.
- **Trustworthy.** Edit means edit; Save is explicit; Reset has its own confirmation guardrails.

## Layout

1. **Global header.**
2. **Screen title** "Settings".
3. **Sequential section cards** (Foundation §9 grouping): Integrations / Cleanup rules / Notifications / Appearance / Mode. Each section is a card with internal rows.
4. **Diagnostics section** appears below Mode only when Expert is on (Foundation §9.15 + Blueprint §8).

Single column, 720px column (narrower than 960px for form-density readability).

## Component Placement

**Above the fold:** header, title, Integrations section.
**Below the fold:** Cleanup rules, Notifications, Appearance, Mode, (Diagnostics if Expert).

**Hidden:** Diagnostics in Normal Mode.

## Visual Hierarchy

- **Largest text:** screen title "Settings".
- **Second:** each section card title in small-caps tracked Meta (`INTEGRATIONS`, `CLEANUP RULES`, …).
- **Third:** row labels (Body, weight 600).
- **Lowest priority:** descriptive helper text below toggles (Meta, `--text-muted`).

## Desktop Mockup (Normal Mode)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Handoffarr        Home   Recover   Library   Health   Settings        [SP] │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Settings                                                                   │
│                                                                              │
│   ┌───── INTEGRATIONS ──────────────────────────────────────────────────┐    │
│   │  qBittorrent            http://localhost:8080                [Edit] │    │
│   │  Sonarr                 http://localhost:8989                [Edit] │    │
│   │  Radarr                 http://localhost:7878                [Edit] │    │
│   │  Lidarr                 http://localhost:8686                [Edit] │    │
│   │  Overseerr              http://localhost:5055                [Edit] │    │
│   └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│   ┌───── CLEANUP RULES ─────────────────────────────────────────────────┐    │
│   │  Auto-cleanup after watched               [✓] After 30 days         │    │
│   │  Minimum seed ratio before cleanup        [ 1.0 ]                   │    │
│   │  Excluded items                           Manage (3)                │    │
│   └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│   ┌───── NOTIFICATIONS ─────────────────────────────────────────────────┐    │
│   │  Notify when cleanup recommended          [ ●──── ] On              │    │
│   │  Notify on integration failure            [ ●──── ] On              │    │
│   └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│   ┌───── APPEARANCE ────────────────────────────────────────────────────┐    │
│   │  Theme                                    ( Dark )  ( Light )  ( System ) │
│   │  Density                                  ( Comfortable )  ( Compact )    │
│   └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│   ┌───── MODE ──────────────────────────────────────────────────────────┐    │
│   │  Expert Mode                              [ ────● ] Off             │    │
│   │  Shows diagnostics, lifecycle history, and source trails.           │    │
│   └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

Section card titles use small-caps tracked Meta per Foundation §3.3.

## Desktop Mockup (Expert Mode on — Diagnostics card appears)

```
   ┌───── MODE ──────────────────────────────────────────────────────────┐
   │  Expert Mode                              [ ●──── ] On              │
   │  Shows diagnostics, lifecycle history, and source trails.           │
   └─────────────────────────────────────────────────────────────────────┘

   ┌───── DIAGNOSTICS ───────────────────────────────────────────────────┐
   │  Open the diagnostics surface to inspect engine state.              │
   │                                                                     │
   │  [ Open Diagnostics ]                                               │
   └─────────────────────────────────────────────────────────────────────┘
```

## Tablet Mockup

Identical sections; section cards full-width within a 600px column. Theme/Density radio chip rows wrap as needed.

## Mobile Mockup

```
┌────────────────────────┐
│ Settings          [SP] │
├────────────────────────┤
│                        │
│ ── INTEGRATIONS ──     │
│ qBittorrent            │
│ localhost:8080  [Edit] │
│ Sonarr                 │
│ localhost:8989  [Edit] │
│ Radarr                 │
│ localhost:7878  [Edit] │
│ Lidarr                 │
│ localhost:8686  [Edit] │
│ Overseerr              │
│ localhost:5055  [Edit] │
│                        │
│ ── CLEANUP RULES ──    │
│ Auto-cleanup after     │
│ watched                │
│         [✓] 30 days    │
│ Minimum seed ratio     │
│         [ 1.0 ]        │
│ Excluded items         │
│         Manage (3)     │
│                        │
│ ── NOTIFICATIONS ──    │
│ Cleanup recommended    │
│         [ ●── ] On     │
│ Integration failure    │
│         [ ●── ] On     │
│                        │
│ ── APPEARANCE ──       │
│ Theme                  │
│ (Dark) (Light) (Sys)   │
│ Density                │
│ (Comfortable)(Compact) │
│                        │
│ ── MODE ──             │
│ Expert Mode            │
│         [ ──● ] Off    │
│ Shows diagnostics,     │
│ lifecycle history, and │
│ source trails.         │
│                        │
├────────────────────────┤
│  🏠   ↻   📚   ⚕   ⚙   │
└────────────────────────┘
```

## States

- **Empty:** Settings is never empty — defaults always present.
- **Loading:** Each section card shows row skeletons (label block + control block). Cards remain rendered.
- **Healthy:** As pictured.
- **Warning — integration broken:** Row in Integrations shows `⚠` icon next to integration name, link `[Fix]` instead of `[Edit]`. Section card is otherwise unchanged.
- **Error — settings failed to save:** Inline error below the affected row, `--critical` Meta: "Couldn't save. [Retry]". Original value reverts visually after a successful retry.

## Component Behavior

- **Section card — Expanded/Collapsed:** Sections do not collapse. They are always fully visible.
- **Row — Hover:** mild `--surface-raised` background on the entire row.
- **Row — Focus (on its control):** focus ring on control (input/toggle/button).
- **`[Edit]` button — Click:** opens an inline editor for that integration row (URL + API key inputs) within the same card. Editing one row does not collapse the others.
- **Toggle — Default / On / Off:** standard toggle (Foundation §9.13 input language). On state uses `--accent`.
- **Number input ("Minimum seed ratio"):** standard Input. Validation: positive float; inline error if invalid.
- **Theme radio chips:** Filter chip styling (Foundation §9.16); single-select.
- **Density radio chips:** Same.
- **Expert toggle — Off → On transition:** `[EXPERT]` chip fades in on the header at `--motion-slow`; Diagnostics card appears below Mode card via height ease (`--motion-base`).

## Example Content

- Integrations: qBittorrent / Sonarr / Radarr / Lidarr / Overseerr with their default URLs.
- Cleanup rules: "After 30 days" (with checkbox), "1.0" seed ratio, "Manage (3)" excluded items.
- Notifications toggles on by default.
- Appearance: theme + density chips.
- Mode: Expert toggle with descriptive subline.

---

# 9. Diagnostics (Expert)

## Visual Intent

- **Invisible intelligence, made visible only on request.** This is the only screen where engine-derived data is exposed as engine-derived data — but still named for what the user does ("Engine status," "Validation reports," "Logs"), never with codebase terms.
- **Appliance-like.** Tabular, monospaced where it aids scanning.
- **Read-mostly.** Re-run is the only action that mutates anything; export is read-only.

## Layout

1. **Top bar:** "← Settings" back link, `[EXPERT]` chip top-right.
2. **Screen title** "Diagnostics".
3. **Engine status card** (4 rows, each: name + last-run meta + `[ Re-run ]` Ghost button or `[ Investigate ]` Secondary).
4. **Validation reports card** (rows: name + discrepancy count + `[ View ]` link).
5. **Logs card** (filter row + monospaced log feed + export/clear actions).

## Component Placement

**Above the fold:** title, Engine status card, top of Validation reports.
**Below the fold:** rest of Validation reports, Logs card.

**Hidden:** raw stack traces (drill-in to log entries via row click).

## Visual Hierarchy

- **Largest text:** screen title.
- **Status icons** carry hierarchy: `⚠` rows dominate via icon color.
- **Lowest priority:** log entry timestamps, log levels (small caps).

## Desktop Mockup

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ← Settings                                                         [EXPERT]  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Diagnostics                                                                │
│                                                                              │
│   ┌───── ENGINE STATUS ─────────────────────────────────────────────────┐    │
│   │  ✓ Recommendations           Last run 4 min ago             Re-run  │    │
│   │  ✓ Library check             Last run 1 hour ago            Re-run  │    │
│   │  ✓ Reconciliation            Last run 12 min ago            Re-run  │    │
│   │  ⚠ Source matching           3 unresolved             [ Investigate ] │  │
│   └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│   ┌───── VALIDATION REPORTS ────────────────────────────────────────────┐    │
│   │  Library vs. Sonarr          0 discrepancies                        │    │
│   │  Library vs. Radarr          1 discrepancy                  View    │    │
│   │  Library vs. Lidarr          0 discrepancies                        │    │
│   │  qBittorrent ownership       2 orphans                      View    │    │
│   └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│   ┌───── LOGS ──────────────────────────────────────────────────────────┐    │
│   │  [ Recent activity ▾ ]    [ Filter: errors only ▾ ]                 │    │
│   │                                                                     │    │
│   │  06-02 14:22  WARN  Source match unresolved: hash 8c2e4f12…         │    │
│   │  06-02 14:18  INFO  Recommendation run complete (4.2 s)             │    │
│   │  06-02 14:06  INFO  Reconciliation complete · 0 changes             │    │
│   │  06-02 13:58  INFO  Sonarr sync complete · 142 items                │    │
│   │  06-02 13:50  WARN  qBittorrent request retried (timeout)           │    │
│   │  06-02 13:46  INFO  Library check complete (1.8 s)                  │    │
│   │                                                                     │    │
│   │                                          [ Export logs ]  [ Clear ] │    │
│   └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

Log entries use `--font-mono` for timestamp + level + body (Foundation §3.1).

## Tablet Mockup

Identical sections; logs card scrolls horizontally only if a single entry exceeds width (rare). No horizontal scroll in the layout itself.

```
┌────────────────────────────────────────────────┐
│ ← Settings                          [EXPERT]   │
├────────────────────────────────────────────────┤
│ Diagnostics                                    │
│                                                │
│ ── ENGINE STATUS ──                            │
│ ✓ Recommendations  4 min ago        Re-run     │
│ ✓ Library check    1 hour ago       Re-run     │
│ ✓ Reconciliation   12 min ago       Re-run     │
│ ⚠ Source matching  3 unresolved  Investigate   │
│                                                │
│ ── VALIDATION REPORTS ──                       │
│ Library vs. Sonarr     0 discrepancies         │
│ Library vs. Radarr     1 discrepancy    View   │
│ Library vs. Lidarr     0 discrepancies         │
│ qBittorrent ownership  2 orphans        View   │
│                                                │
│ ── LOGS ──                                     │
│ [Recent ▾]  [Filter: errors ▾]                 │
│                                                │
│ 06-02 14:22  WARN  Source match unresolved…    │
│ 06-02 14:18  INFO  Recommendation run (4.2 s)  │
│ 06-02 14:06  INFO  Reconciliation · 0 changes  │
│ 06-02 13:58  INFO  Sonarr sync · 142 items     │
│                                                │
│              [ Export logs ]   [ Clear view ]  │
└────────────────────────────────────────────────┘
```

## Mobile Mockup

Per Blueprint §11, Diagnostics on mobile is a read-only feed:

```
┌────────────────────────┐
│ ← Settings  [EXPERT]   │
├────────────────────────┤
│ Diagnostics            │
│                        │
│ ── ENGINE STATUS ──    │
│ ✓ Recommendations      │
│   4 min ago            │
│ ✓ Library check        │
│   1 hour ago           │
│ ✓ Reconciliation       │
│   12 min ago           │
│ ⚠ Source matching      │
│   3 unresolved         │
│                        │
│ ── VALIDATION ──       │
│ Lib vs. Sonarr   0     │
│ Lib vs. Radarr   1 →   │
│ Lib vs. Lidarr   0     │
│ qBittorrent owner 2 →  │
│                        │
│ ── LOGS ──             │
│ 06-02 14:22 WARN       │
│  Source match          │
│  unresolved            │
│ 06-02 14:18 INFO       │
│  Recommendation run    │
│  (4.2 s)               │
│ 06-02 14:06 INFO       │
│  Reconciliation        │
│  · 0 changes           │
│                        │
│  [ Export logs ]       │
├────────────────────────┤
│  🏠   ↻   📚   ⚕   ⚙   │
└────────────────────────┘
```

Re-run and Investigate buttons are not surfaced on mobile (read-only per Blueprint).

## States

- **Empty (fresh install):** "No diagnostic activity yet. Run a check to populate." with Ghost `[ Run a check now ]`.
- **Loading:** Each card shows row skeletons; log feed shows 6 monospaced skeleton lines.
- **Healthy:** All rows in Engine status show `✓` and "Last run N ago".
- **Warning:** One or more `⚠` rows with `[ Investigate ]` Secondary button; validation reports show discrepancy counts > 0.
- **Critical:** `✕` rows possible (e.g., Engine failing repeatedly). Row icon and count in `--critical` strong.

## Component Behavior

- **Engine row — Re-run:** Ghost button; click shows inline loader on the row's right-side meta ("Running…"). On completion, meta updates to "Last run just now".
- **Engine row — Investigate:** Secondary button; navigates to a detail surface (validation report or stuck-match detail).
- **Validation row — View:** Ghost link to a sub-view (out of scope for this mockup — reuses Library list patterns).
- **Logs filters:** Ghost dropdowns; selecting filters re-renders feed instantly (client-side).
- **Logs row — Hover:** background `--surface-raised`.
- **Logs row — Focus:** 2px `--accent` ring.
- **Logs row — Click:** opens detail (full message + stack) in Evidence Drawer pattern.
- **Export logs:** triggers file download (no animation, no toast — file save dialog).
- **Clear view:** clears the filtered view; does not delete logs.

## Example Content

- Engine status: Recommendations / Library check / Reconciliation (all ✓); Source matching ⚠ 3 unresolved.
- Validation: Library vs. Sonarr (0), Radarr (1), Lidarr (0), qBittorrent ownership (2 orphans).
- Logs:
  - `06-02 14:22 WARN Source match unresolved: hash 8c2e4f12…`
  - `06-02 14:18 INFO Recommendation run complete (4.2 s)`
  - `06-02 14:06 INFO Reconciliation complete · 0 changes`
  - `06-02 13:58 INFO Sonarr sync complete · 142 items`
  - `06-02 13:50 WARN qBittorrent request retried (timeout)`
  - `06-02 13:46 INFO Library check complete (1.8 s)`

---

# 10. First Run Experience

## Visual Intent

- **Invisible intelligence.** Onboarding does not describe engines or features. It connects integrations and lets the app start working.
- **Trustworthy.** Each step shows clearly what is required and what will happen.
- **Calm.** A three-step wizard, not a fifteen-step pageant. Skippable where safe.

> The First Run Experience is part of Phase 5 polish in the Blueprint (§12) and §11 mobile section references onboarding only briefly. This document specifies its visual appearance using only the already-defined components — banner, recommendation card, inputs, primary buttons, status badges.

## Layout

A centered single-column flow at max 560px (form-density). No global header during onboarding (replaced by a thin progress indicator). No bottom nav on mobile during onboarding.

Three steps:

1. **Welcome / Setup**
2. **Connect integrations**
3. **You're ready**

A 3-segment progress strip at the top (full-width, 3px, segmented).

## Component Placement

**Above the fold:** progress indicator + current step's title + step body.
**Below the fold:** primary `[ Continue ]` button (or `[ Finish ]` on last step).

**Hidden:** Expert Mode (introduced post-onboarding via Settings).

## Visual Hierarchy

- **Largest text:** the step's Display headline ("Welcome to Handoffarr.").
- **Second:** the primary button.
- **Third:** integration row labels in Step 2.
- **Lowest priority:** the "Skip for now" Ghost link.

## Desktop Mockup — Step 1 (Welcome)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  Step 1 of 3                           │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                                                                              │
│                          Welcome to Handoffarr.                              │
│                                                                              │
│              The librarian for your media library — quiet by default,        │
│              ready when you need it.                                         │
│                                                                              │
│              We'll connect to your existing tools (qBittorrent,              │
│              Sonarr, Radarr, Lidarr, Overseerr) and start watching           │
│              for what's worth your attention.                                │
│                                                                              │
│              You can change anything later in Settings.                      │
│                                                                              │
│                                                                              │
│                                              [ Get started ]                 │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Desktop Mockup — Step 2 (Connect integrations)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ████████████████████░░░░░░░░░░░░░░░░░  Step 2 of 3                           │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Connect your tools                                                         │
│                                                                              │
│   Handoffarr reads from these services. You can connect them now or skip     │
│   any and add them later.                                                    │
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐   │
│   │  qBittorrent                                                         │   │
│   │  URL          [ http://localhost:8080                            ]   │   │
│   │  Username     [ admin                                            ]   │   │
│   │  Password     [ ••••••••                                         ]   │   │
│   │                                              [ Test ]   [ Connect ]  │   │
│   ├──────────────────────────────────────────────────────────────────────┤   │
│   │  Sonarr                                                              │   │
│   │  URL          [ http://localhost:8989                            ]   │   │
│   │  API key      [ ••••••••••••                                     ]   │   │
│   │                                              [ Test ]   [ Connect ]  │   │
│   ├──────────────────────────────────────────────────────────────────────┤   │
│   │  Radarr                                                              │   │
│   │  URL          [ http://localhost:7878                            ]   │   │
│   │  API key      [ ••••••••••••                                     ]   │   │
│   │                                              [ Test ]   [ Connect ]  │   │
│   ├──────────────────────────────────────────────────────────────────────┤   │
│   │  Lidarr (optional)                              ▸ Add                │   │
│   ├──────────────────────────────────────────────────────────────────────┤   │
│   │  Overseerr (optional)                           ▸ Add                │   │
│   └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   3 of 5 connected · [ ✓ ] [ ✓ ] [ ✓ ] [ ] [ ]                               │
│                                                                              │
│   Skip for now                                            [ Continue ]       │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

Connected integrations within the group show a `✓` status icon in `--success` left of the integration name. Untested integrations show a neutral state. Failed tests show `⚠` and a plain-language hint inline ("Connection refused — is qBittorrent running on port 8080?") in `--caution` Meta below the row.

## Desktop Mockup — Step 3 (Ready)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ████████████████████████████████████  Step 3 of 3                            │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                                                                              │
│                            ✓                                                 │
│                                                                              │
│                          You're ready.                                       │
│                                                                              │
│              We're doing a first pass on your library now. The first         │
│              recommendation will appear on Home once it's ready —            │
│              usually in a few minutes.                                       │
│                                                                              │
│                                                                              │
│                                              [ Go to Home ]                  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Tablet Mockup

Same flow, narrower column (480px), integration cards stack with form fields full-width. Buttons remain right-aligned.

## Mobile Mockup — Step 1

```
┌────────────────────────┐
│ ███░░░░░  Step 1 of 3  │
├────────────────────────┤
│                        │
│ Welcome to             │
│ Handoffarr.            │
│                        │
│ The librarian for your │
│ media library —        │
│ quiet by default,      │
│ ready when you need it.│
│                        │
│ We'll connect to your  │
│ existing tools and     │
│ start watching for     │
│ what's worth your      │
│ attention.             │
│                        │
│ You can change         │
│ anything later in      │
│ Settings.              │
│                        │
│ [   Get started   ]    │
│                        │
└────────────────────────┘
```

## Mobile Mockup — Step 2

```
┌────────────────────────┐
│ ████░░░░  Step 2 of 3  │
├────────────────────────┤
│ Connect your tools     │
│                        │
│ Connect now or add     │
│ later in Settings.     │
│                        │
│ ┌────────────────────┐ │
│ │ qBittorrent        │ │
│ │ URL                │ │
│ │ [localhost:8080  ] │ │
│ │ Username           │ │
│ │ [admin           ] │ │
│ │ Password           │ │
│ │ [•••••••         ] │ │
│ │ [Test]  [Connect]  │ │
│ ├────────────────────┤ │
│ │ Sonarr             │ │
│ │ URL                │ │
│ │ [localhost:8989  ] │ │
│ │ API key            │ │
│ │ [•••••••         ] │ │
│ │ [Test]  [Connect]  │ │
│ ├────────────────────┤ │
│ │ Radarr             │ │
│ │ ▸ Add              │ │
│ ├────────────────────┤ │
│ │ Lidarr (optional)  │ │
│ │ ▸ Add              │ │
│ ├────────────────────┤ │
│ │ Overseerr (opt.)   │ │
│ │ ▸ Add              │ │
│ └────────────────────┘ │
│                        │
│ 2 of 5 connected       │
│                        │
│  Skip for now          │
│            [Continue]  │
└────────────────────────┘
```

## Mobile Mockup — Step 3

```
┌────────────────────────┐
│ ████████  Step 3 of 3  │
├────────────────────────┤
│                        │
│         ✓              │
│                        │
│   You're ready.        │
│                        │
│ We're doing a first    │
│ pass on your library   │
│ now. The first         │
│ recommendation will    │
│ appear on Home once    │
│ it's ready — usually   │
│ in a few minutes.      │
│                        │
│ [   Go to Home   ]     │
│                        │
└────────────────────────┘
```

## States

- **Empty (initial state):** The default Step 1.
- **Loading (Step 2 testing):** Test button shows inline loader; row otherwise unchanged. On result: success → status icon `✓` next to integration name + Connect button changes to "Connected" Ghost-style label; failure → caution row appears.
- **Healthy (Step 3 reached):** All connected integrations carry `✓`; deferred ones simply absent.
- **Warning (Step 2 — at least one failed test):** Per-row inline caution Meta. Step Continue button remains enabled (failed integrations can be skipped); a subtle Meta line reminds: "You can add or fix integrations anytime in Settings."
- **Error (Step 2 — entire setup failed to save):** Inline section-level error above the buttons: "Couldn't save your setup. [ Retry ]".

## Component Behavior

- **Progress strip:** Segmented bar at top. Active segments use `--accent`; remaining segments `--border`. No animation on transition between steps beyond `--motion-base`.
- **Step body:** Crossfade `--motion-slow` between steps.
- **Integration form rows — Default:** Foundation Input language. Password fields use the same Input pattern.
- **`[ Test ]` — Default/Hover/Focus/Active:** Secondary button language.
- **`[ Connect ]` — Default:** Primary button. After successful test it becomes the obvious next action.
- **`[ Connect ]` — After connect:** Replaced by a Meta-level "✓ Connected" label, optional `[ Edit ]` Ghost.
- **"Optional" rows — Collapsed:** Show name + `▸ Add` Ghost; expand to the same form pattern as required rows.
- **`Skip for now` — Ghost link** bottom-left of action row.
- **`Continue` / `Get started` / `Go to Home`** — Primary button, right-aligned.

## Example Content

- Welcome copy: "The librarian for your media library — quiet by default, ready when you need it."
- Integration prompts: URL, Username, Password (qBittorrent); URL, API key (the *arr family).
- Defaults: `localhost:8080` (qBittorrent), `localhost:8989` (Sonarr), `localhost:7878` (Radarr), `localhost:8686` (Lidarr), `localhost:5055` (Overseerr).
- Step 3 copy: "We're doing a first pass on your library now. The first recommendation will appear on Home once it's ready — usually in a few minutes."

---

# Visual Inspiration Board

Each entry names a product whose visual or interaction language informs Handoffarr's, with explicit boundaries.

## Linear

**Emulate:**
- Quiet neutral palette with one bold accent; minimal chrome.
- Tabular figures everywhere; numbers that don't shift.
- Compact, confident keyboard-friendly UI; focus rings that are taken seriously.
- The "calm hum" of an app that respects the user's attention.

**Do NOT emulate:**
- Dense command bar / cmd-K everywhere. Handoffarr is not an issue tracker.
- Multi-pane layouts. Handoffarr is single-column.
- High-frequency keyboard shortcut overlays. Expert Mode has a few; that's it.
- The brand's saturated purple. Indigo is Handoffarr's accent and it is quieter.

## Arc Browser

**Emulate:**
- The willingness to make ordinary chrome (sidebar, tabs) recede so content dominates.
- Generous warmth in the palette; not clinical grayscale.
- Confident motion that supports spatial continuity (drawer/sheet transitions) — never decorative.

**Do NOT emulate:**
- Spaces, profiles, sidebar gymnastics, color theming per workspace. Handoffarr has *one* visual identity.
- Animated illustrations or playful onboarding. The librarian aesthetic does not perform.
- Color as personality. Color in Handoffarr is semantic only.

## Plex

**Emulate:**
- Poster-forward hierarchy: the artwork is the anchor for any item view.
- Library-first IA: titles and metadata feel inventoried, not data-warehoused.
- The home-server homeliness of a product that runs on your hardware.

**Do NOT emulate:**
- Plex's home dashboard chrome — too many shelves, too many tiles competing.
- Heavy dark-blue / black backgrounds with neon accents.
- The "discovery" framing (Plex Movies & Shows). Handoffarr is a librarian, not a recommendation engine for content.
- Per-screen background art / dynamic theming from poster colors.

## Apple TV

**Emulate:**
- The unapologetically large, single hero element on top of each screen.
- Generous spacing; type carries the weight, not borders.
- The sense that the system has already curated; the user is choosing among finalists, not browsing a database.

**Do NOT emulate:**
- Auto-playing video backgrounds, parallax, or hover-zooming posters.
- TV-OS focus-glow halos; we use a precise 2px ring.
- Cinematic editorial blocks ("Now Trending"). Handoffarr's hero is a *decision*, not a recommendation.

## Tailscale

**Emulate:**
- Plain-language status that explains state in a sentence (e.g., "Connected to 14 devices").
- The way settings feel like a calm settings app, not a configuration nightmare.
- Status colors used precisely and sparingly; healthy is neutral, not green-glowing.
- The trustworthy tone of a homelab-friendly product.

**Do NOT emulate:**
- The product's specifically network-engineer cadence and topology diagrams.
- Admin console density. Handoffarr is a librarian, not a network operator's console.
- Their reliance on extensive log surfaces in the main UI — Handoffarr keeps logs in Diagnostics only.

## 1Password

**Emulate:**
- The reading-room rhythm of the item list ↔ detail pattern.
- Discreet, confident security/health affordances.
- Empty and idle states that feel calm and complete, not blank.
- Inputs that look like inputs — clear edges, focused affordance.

**Do NOT emulate:**
- Cards/categories/vaults as a top-level mental model. Handoffarr has a single library.
- Cross-product browser-extension chrome.
- "Watchtower" risk dashboards. Handoffarr's analog is Health, and it is plainer.
- Heavy in-app marketing prompts.

## GitHub

**Emulate:**
- The discipline of identifying *the* primary action per page (Merge, Open PR) and giving it the only Primary button.
- Plain-language status badges with icons.
- The compact, scannable list rows in Pull Requests / Issues lists.
- Sectioned settings pages with clear headers.

**Do NOT emulate:**
- The information density of repository pages.
- Tabs-everywhere navigation; Handoffarr has one nav layer.
- Markdown rendering, code blocks, syntax color in primary surfaces.
- The platform breadth — Handoffarr has 5 surfaces, total.

---

# Frontend Implementation Guidance

This is a **specification mapping** between the Blueprint's component vocabulary and the implementation stack. No code samples; only correspondences and constraints.

## Stack

- **React** (function components, hooks; routes via the app's router of choice).
- **Tailwind CSS** as the styling system. The Foundation §14 design tokens are exposed as CSS custom properties on `:root` and `[data-theme="dark"]`; Tailwind reads them through `theme.extend.colors` and a sibling `spacing` / `borderRadius` extension. Default tailwind palette tokens are **not used** — only Foundation tokens.
- **shadcn/ui** as the component base layer. Each Blueprint component below maps to one or more shadcn primitives, configured to render the Foundation visuals.
- **lucide-react** as the icon library (matches Foundation §6).
- **Inter Variable** + **JetBrains Mono** loaded as fonts; `font-variant-numeric: tabular-nums` set globally via Tailwind base layer.

## Theming

- Mode toggle (Settings → Appearance → Theme) sets `[data-theme="dark"]` / `[data-theme="light"]` on the `<html>` element.
- Default is dark on first install; `prefers-color-scheme` honored before the user touches the toggle.
- Density (`comfortable` / `compact`) is exposed via `data-density` attribute on `<html>` — components read it through CSS attribute selectors to adjust internal padding. `compact` is the Expert default.
- `prefers-reduced-motion` collapses all `--motion-*` tokens to `0.01ms` via a global CSS block.

## Blueprint → shadcn/ui mapping

| Blueprint component (Blueprint §9 / Foundation §9) | shadcn/ui base | Notes / configuration |
|---|---|---|
| Primary Banner (Home) | `Card` + custom inner layout (`CardHeader` / `CardContent`) | Use `Card` with `--elev-1`, 32px padding; headline = `h1` with Display class; primary button is `Button` size `lg`, variant `default` (accent). Idle variant: omit `Button`, swap headline weight to 600, add `check-circle` icon. |
| Stat Tile | `Card` (no hover state) | Static — must not be wrapped in any interactive element. Apply `cursor-default`. Optional `Progress` (shadcn) for the thin bar; 4px tall, radius pill. |
| Recommendation Card (Recover Space sections) | `Card` | Header row uses an icon (lucide) + `Subtitle`; right-aligned meta uses `Meta` class with `font-variant-numeric: tabular-nums`. Actions are `Button` siblings — Primary, Secondary, Ghost in that order. |
| Item Row (Library / Safe / Risky) | None — custom row component | shadcn does not have a "media row." Build as a `div` with the Foundation §9.5/9.6/9.7 specs. Library row gets `Badge` (shadcn) for status. Safe row gets `Checkbox` (shadcn) on the far left and a `Button` variant `link` for "Why safe?". |
| Health Tile | `Card` with internal two-column rows; tile group bordered | The bordered group uses a single `Card` containing rows separated with `border-b border-[--border]`. Per-tile `Button` (size `sm`, variant `default`) for Fix; healthy rows: no button. |
| Evidence Drawer | `Sheet` (shadcn) | Side `right` on desktop/tablet, side `bottom` on mobile. Header = `SheetHeader` with `SheetTitle` + `SheetClose`. Backdrop opacity per Foundation §9.9. |
| Activity Timeline (Compact / Full) | None — custom timeline | Build as a `ol` with bullet markers; Full (Expert) uses a vertical rail (`border-l` + dots). |
| Inline Confirmation Strip | None — custom strip | Below the Recommendation Card. Top border `border-t-[--border-strong]`. Inside: text + `Button` (Primary) + `Button` (Secondary) + `Button` (Ghost) + `Checkbox` for dry-run. |
| Confirmation Dialog (catastrophic) | `Dialog` (shadcn) — `AlertDialog` variant | Reserve for catastrophic actions per Foundation §9.11. Type-to-confirm uses `Input` with `--critical` focus ring (custom). |
| Success State Banner | `Card` with `--success-quiet` surface | Replaces the section that was acted on (not appended). Internal `Button` variants: Undo = Secondary, View = Ghost. |
| Status Badge | `Badge` (shadcn) | Variants: Imported (success), Downloading (accent), Stuck (caution), Not found (critical), Queued (neutral). Each variant includes its lucide icon + label per Foundation §6.3 vocabulary. |
| Mode Indicator (`[EXPERT]` chip) | `Badge` (shadcn) | Variant `accent-quiet`. Static. `aria-label="Expert mode active"`. Never animated. |
| Filter Chip Row | `ToggleGroup` (shadcn) with `type="single"` | Pills, accent fill when selected. Sort dropdown is `DropdownMenu` (shadcn) triggered by a Ghost `Button` with chevron-down icon. |
| Inputs (text, number, password) | `Input` (shadcn) | 36px height (40px for Library search). Focus replaces border with 2px `--accent`, no offset (Foundation §9.13). |
| Toggle (Settings) | `Switch` (shadcn) | On state = `--accent`. |
| Tabs (Item Detail Expert) | `Tabs` (shadcn) | Active tab indicator: 2px `--accent` underline. |
| Bottom Sheet (mobile confirmation) | `Sheet` (shadcn) side `bottom` | Respect safe-area inset via `padding-bottom: env(safe-area-inset-bottom)`. Tap-outside dismisses. |
| Top Progress Strip (Recover execution) | `Progress` (shadcn) | 3px tall, `--accent` fill on `--border` track. Fixed to top of viewport while executing. |
| Bottom Tab Bar (mobile) | None — custom nav | 5 tabs, icons + labels (Foundation §4.2). Active tab uses `--accent` for icon + label. |
| Global Header (desktop/tablet) | None — custom | 56px fixed; wordmark left, primary nav center, `[SP]` settings/profile shortcut + Mode chip right. |
| Skeleton (loading states) | `Skeleton` (shadcn) | Bg `--border`, 1.4s linear opacity pulse. Used in lists/cards as per Foundation §10.2. |
| Empty/Idle state block | None — composition | Centered column 360px max; lucide `check-circle` at 24px in `--success`; Title + Meta + optional Ghost `Button`. |

## Tailwind configuration constraints

- **Colors:** extend with the Foundation tokens only (`bg`, `surface`, `surface-raised`, `border`, `border-strong`, `text`, `text-muted`, `text-subtle`, `accent`, `accent-hover`, `accent-quiet`, `accent-on`, and `success` / `caution` / `critical` each with `quiet`). Do not add brand-named utility colors.
- **Spacing:** override default scale with `--space-1`..`--space-8` (4 / 8 / 12 / 16 / 24 / 32 / 48 / 64). Forbid arbitrary spacing values in components; the linter should flag custom px values inside component files.
- **Border radii:** `radius-sm` (4), `radius-md` (8), `radius-lg` (12), `radius-pill` (999). No 6, no 10.
- **Shadows:** `--elev-0` (none), `--elev-1`, `--elev-2`, `--elev-3` exactly as Foundation §5.2.
- **Type:** five classes only — `text-display`, `text-title`, `text-subtitle`, `text-body`, `text-meta` — each mapped to its size/line-height/weight pair from Foundation §3.2. Display variant for numerals gets weight 700.
- **Motion:** durations `--motion-fast` (120ms), `--motion-base` (180ms), `--motion-slow` (260ms); easing `--ease-out`, `--ease-in`. Tailwind `transition-duration` extended accordingly.
- **Focus ring:** a global utility `focus-visible:outline focus-visible:outline-2 focus-visible:outline-[--accent] focus-visible:outline-offset-2` applied to every interactive primitive via the shadcn `cn` helper override.

## shadcn/ui configuration constraints

- Generate components with the `default` style baseline, then override class names to match Foundation tokens.
- Replace shadcn's default radius variable with `--radius-md` for buttons and inputs, `--radius-lg` for cards, `--radius-pill` for chips and badges.
- Disable shadcn's default ring color overrides; use `--accent` everywhere.
- Replace any built-in animation classes (e.g., `data-[state=open]:animate-in`) with motion tokens that respect `prefers-reduced-motion`.
- For `Dialog` / `Sheet`: configure backdrop opacity per Foundation §9.9; ensure focus trapping is honored.

## Component density (Expert Mode)

- Setting `data-density="compact"` on `<html>` reduces:
  - Card padding from 24px → 16px.
  - List row vertical padding from 16px → 12px.
  - Section gaps from 32px → 24px.
- Type sizes, borders, radii, and colors do **not** change with density. Density is a spacing dimension only.

## Accessibility integration

- Provide a global `Skip to content` link in the header shell.
- All `Button` variants render an `aria-label` when text is icon-only.
- All `Badge` variants render visible text alongside the icon — color is reinforcement only.
- Progress strips: `role="progressbar"`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`.
- Drawer: `role="dialog"` (shadcn `Sheet` provides this); focus moves to drawer title on open and returns to invoker on close.
- Item Judgment keyboard shortcuts (`R / K / L`) bound only when Expert Mode is on; an unobtrusive Meta hint appears at the bottom of the screen announcing the bindings.

## What this guidance explicitly does not authorize

- New components beyond the Blueprint's library.
- New tokens beyond the Foundation's set.
- Component variants beyond what the Foundation enumerates (e.g., no "danger Ghost" button, no "info Badge" variant).
- Decorative animations, parallax, gradient fills, or per-page accent overrides.
- Custom illustration sets, mascots, or animated empty states.
- Switching the icon library on a per-screen basis or mixing icon styles.

The visual language is small on purpose. Implementation should make it look identical across every screen rather than richer on any one of them.

---

## Closing Note

This document does not invent. It freezes. Every screen here exists in the Blueprint; every visual decision here is derived from the Foundation; every component referenced is already in the Blueprint's library or the Foundation's anatomy specs.

If implementation requires a decision this document does not answer, escalate before guessing. The discipline that makes Handoffarr feel like a librarian — quiet defaults, one accent, three sections on Recover Space, one bold sentence at the top of Home — is the discipline of refusing the small new addition that would, alone, be harmless, and together with all the other small additions, would turn the app back into the control panel it is trying to stop being.
