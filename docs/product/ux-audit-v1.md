# Handoffarr UX Redesign Proposal
## Principal Product Designer's Strategic Audit & Roadmap

---

## 1. EXECUTIVE SUMMARY

Handoffarr has a backend problem disguised as a UI problem. The engineering team has built a sophisticated intelligence platform — correlation engines, lifecycle analysis, decision attribution — and then exposed every one of those concepts directly to the user. The result is a control panel for the system, not a tool for the human.

The fix is not visual polish. It is **subtraction**. The product needs to be cut down to three jobs users actually do:

1. **Recover disk space** (the killer feature — nothing else matters if a disk is full)
2. **See what their stack is doing** (situational awareness)
3. **Fix things that are broken** (health & repair)

Every other surface is in service of those three jobs or it does not belong on the default screen. The "intelligence" should disappear into the experience — informing decisions, not demanding interpretation.

**The headline reframe:** Handoffarr is not a dashboard. It is a **media librarian**. It tells you what to do, does the boring parts for you, and stays out of the way when nothing is wrong.

Recommended outcome: cut top-level surfaces from ~12+ concepts to **5 navigation entries**, collapse all diagnostic surfaces behind an Expert Mode toggle, and rebuild the cleanup workflow around a single "Recover Space" action that answers the only question a user with a full disk has: *what can I safely delete right now?*

---

## 2. UX AUDIT

Ranked by severity. Severity = (frequency of harm) × (impact when harmed).

### S0 — Critical (fix first, blocks adoption)

**A. No clear primary job-to-be-done on any screen.**
The user opens the app with a goal ("my disk is full" / "did my show download?") and is greeted with panels of analytics. Every screen presents lateral options instead of a forward path. *Harm:* users bounce, or worse, take the wrong action because nothing is highlighted as *the* action.

**B. Terminology leaks implementation.**
"Correlation Engine," "Responsibility Attribution," "Decision Center," "Lifecycle Analysis" are engineering concepts, not user concepts. *Harm:* users cannot form a mental model of what the app does, so they cannot trust it. Trust is non-negotiable for software that deletes files.

**C. Cleanup workflow is fragmented across multiple surfaces.**
"Detection," "Review," "Execution," "Batch Execution," "Purge Queue," "Reconciliation" appear to be separate concepts. They are one workflow: *find stuff → confirm → delete → verify*. *Harm:* the most valuable workflow is also the most confusing, which inverts the value proposition.

### S1 — High (degrade daily usability)

**D. Cognitive overload on landing.**
Too many cards, too many metrics, no hierarchy. Everything looks equally important, so nothing is important. *Harm:* every visit costs effort even when no action is needed.

**E. Diagnostics mixed with operations.**
"Validation" and "Diagnostics" sit next to user-facing features. *Harm:* normal users see scary-looking technical surfaces and assume something is broken.

**F. No mode separation.**
The homelab tinkerer and the spouse who just wants to know if the show downloaded share the same interface. *Harm:* the interface satisfies neither — too complex for one, too shallow for the other.

### S2 — Medium (friction, not blockers)

**G. Weak visual hierarchy.**
Likely uniform card sizes, similar weights, no clear "look here first" signal.

**H. Decision fatigue in cleanup review.**
Asking the user to evaluate every candidate individually defeats the purpose of having an intelligence layer. The system should pre-decide; the user should approve batches.

**I. Navigation likely flat and wide.**
Many top-level items means the IA does the user's categorization work for them — poorly.

### S3 — Low (polish)

**J. Empty/idle states probably underdesigned.** When nothing is wrong, the dashboard should feel calm, not blank or alarming.

**K. No progressive onboarding.** New users see the same complexity as veterans.

---

## 3. UX CHARTER (10 Principles)

These are mandatory. Every future design decision is checked against them.

1. **One primary action per screen.** Every screen has exactly one button styled as *the* action. If a screen has no primary action, it is a reading screen and should look like one.

2. **Progressive disclosure by default.** Show the answer. Hide the evidence behind "Show details." Hide the diagnostics behind Expert Mode. The user asks; the system reveals.

3. **Decisions, not data.** A metric earns its place on screen only if it changes what the user does. "847 files analyzed" is data. "42 GB safe to delete" is a decision.

4. **The system has a recommendation.** Never present a list of options without a default. If the intelligence layer cannot recommend, it has failed — say so explicitly rather than offload the choice.

5. **Destructive actions require evidence, not just confirmation.** Before deleting, show *what* and *why* — not just "Are you sure?" Confirmation dialogs without context train users to click through.

6. **Calm by default, loud when it matters.** When nothing is wrong, the UI is quiet. Warnings and errors are reserved for things that actually require user attention. Yellow badges everywhere = no signal.

7. **Speak the user's language, not the codebase's.** No term appears in the UI that wasn't designed for the user. Internal names stay internal.

8. **Reversibility over confirmation.** Where possible, make actions undoable for a window of time rather than gating them with friction. "Deleted — Undo (30s)" beats "Are you sure? Type DELETE to confirm."

9. **Mode-appropriate density.** Normal Mode is sparse. Expert Mode is dense. Never the average of both.

10. **The empty state is a feature.** "Nothing to clean up" is a success message, not a blank canvas. Design idle states with the same care as active ones.

---

## 4. PERSONAS

### Casey — The Casual Household User
- **Tech:** Low. Uses Plex/Jellyfin, doesn't know what qBittorrent is.
- **Goals:** Know whether requested shows arrived. Occasionally ask "why isn't this working?"
- **Tasks:** Glance at status. Approve cleanups their partner set up.
- **Frequency:** Weekly, < 2 min per visit.
- **Design implication:** May not be a primary persona, but the app should not actively repel them.

### Sam — The Homelab Owner *(PRIMARY PERSONA)*
- **Tech:** Medium-high. Set up the *arr stack themselves, comfortable with Docker, doesn't want to read documentation to use a tool.
- **Goals:** Keep storage healthy without thinking about it. Trust the system to recommend cleanup. Avoid manual file management.
- **Tasks:** Weekly cleanup approval, occasional troubleshooting, glance at health.
- **Frequency:** 2–4× per week, 2–10 min per visit.
- **Design implication:** This is the persona Handoffarr exists for. Default UX is tuned for Sam.

### Pat — The Power User / Storage Hawk
- **Tech:** High. Has 80TB+, multiple drives, understands seeding ratios, cares about lifecycle policies.
- **Goals:** Fine-grained control over what gets removed and why. Audit trails. Bulk operations.
- **Tasks:** Tune cleanup rules, run dry-runs, inspect correlation results, review attribution.
- **Frequency:** Daily-ish, 10–30 min per visit.
- **Design implication:** Expert Mode exists for Pat. Should never feel like Pat's needs are a special case — when toggled on, the app becomes their tool.

### Riley — The Administrator / Operator
- **Tech:** Very high. May run this for a small group, may be the SRE for their household.
- **Goals:** Diagnose integration issues, verify the system is correctly attributing actions, validate against external state (qBittorrent, *arr stack).
- **Tasks:** Health checks, diagnostics, configuration, troubleshooting handoffs.
- **Frequency:** Reactive — when something breaks.
- **Design implication:** Diagnostics live in Settings/Health, not on the main surface.

---

## 5. INFORMATION ARCHITECTURE

### Current (inferred) → Proposed

**Current surfaces** (approximate): Import Tracking, Library Verification, Cleanup Detection, Cleanup Review, Cleanup Execution, Batch Execution, Recommendations, Storage Recovery, Lifecycle Analysis, Decision Analysis, Validation, Diagnostics, Correlation Engine, Responsibility Attribution.

**Proposed top-level navigation (5 entries):**

| Nav | Purpose | Target user | Primary action |
|---|---|---|---|
| **Home** | At-a-glance: is everything okay, is there space to recover, is anything stuck? | All | Resolve the one most important thing |
| **Recover Space** | The cleanup workflow, end to end | Sam, Pat | "Recover X GB" |
| **Library** | What was requested, downloaded, imported — recent activity and verification | Sam, Casey | Search / inspect an item |
| **Health** | Integration status, stuck items, things that need attention | Sam, Riley | Fix or dismiss |
| **Settings** | Configuration, integrations, rules, **Expert Mode toggle**, diagnostics | Riley, Pat | Configure |

### Merges (what folds into what)

- **Cleanup Detection + Review + Execution + Batch + Purge Queue + Reconciliation** → single **Recover Space** flow.
- **Import Tracking + Library Verification** → **Library** (one timeline view per item).
- **Lifecycle Analysis + Decision Analysis + Correlation Engine + Responsibility Attribution** → **never surface these as features.** They are *engines* that power recommendations, attribution badges, and the "why this was suggested" drawer. They do not deserve nav real estate.
- **Validation + Diagnostics** → **Health** (user-facing problems) + **Settings → Diagnostics** (developer-facing detail).
- **Recommendations** → contextual within Home and Recover Space, not its own surface.
- **Storage Recovery Analysis** → the body of the **Recover Space** screen.

### What gets demoted

The "intelligence" surfaces (Correlation, Lifecycle, Decision, Attribution) are the engine, not the product. They appear as:
- Badges on items ("Orphaned download — qBittorrent has it, no *arr claim")
- "Why?" drawers next to recommendations
- Expert Mode panels for users who want to audit

They do not appear in navigation.

---

## 6. NORMAL MODE VS EXPERT MODE

**Yes — two modes, with a single toggle in Settings (and a subtle indicator in the header when Expert is on).**

### Normal Mode (default)
- 5-item navigation as above
- Recommendations presented as decisions ("Delete these 12 items to recover 42 GB")
- One-click batch actions on system-classified safe items
- Risky items hidden behind "Show items needing your judgment (3)"
- No raw correlation data, no attribution chains, no lifecycle timelines visible
- Health shows: "✓ All integrations healthy" or "⚠ 2 items need attention"

### Expert Mode (opt-in)
- All Normal Mode surfaces, plus:
- Per-item lifecycle timeline (request → grab → download → import → play → recommend cleanup)
- Attribution chain visible on every item (who/what caused this state)
- Correlation diagnostics surfaced inline
- Raw qBittorrent/*arr cross-references
- Dry-run mode becomes default for destructive actions
- Bulk operations with filters
- "Why this recommendation?" expanded by default rather than collapsed

**Rationale:** A single interface cannot serve Sam and Pat without compromising both. The mode toggle lets each persona get the right interface without forking the product. Default to Normal — Pat will find the toggle; Sam should never need to.

**What does NOT belong in either mode:** terminology like "Correlation Engine" as a feature name. Even in Expert Mode, the surfaces are called "Lifecycle" and "Attribution," not "Correlation Engine Output."

---

## 7. CLEANUP WORKFLOW REDESIGN

**Design goal:** A user with a full disk lands on Home, clicks one thing, and within 10 seconds understands what to do.

### The end-to-end flow (Normal Mode)

**Step 1 — Home banner (the entry point)**
> **42 GB ready to recover** from 14 items you've already watched.
> [ Review and recover ]   *Last cleanup: 6 days ago*

That's it. No table, no chart. One sentence, one button. Only appears if there is meaningful space to recover.

**Step 2 — Recover Space screen (the summary)**

Three stacked sections, top to bottom:

> **42 GB ready to recover**
> Based on what you've watched, what's been replaced by better versions, and what's been sitting unused.
>
> ━━━━━━━━━━━━━━━━━━━━━━━━━
>
> ✓ **Safe to remove — 12 items, 38 GB**
> Watched, complete, no seeding obligation.
> [ Recover 38 GB ]   [ Review items ]
>
> ⚠ **Needs your judgment — 2 items, 4 GB**
> Still seeding, or recently added.
> [ Review ]
>
> [ Show items not recommended for cleanup ]  *(collapsed)*

The user with a full disk clicks **Recover 38 GB** and is done. No per-item review required.

**Step 3 — Confirmation (lightweight)**

Inline confirmation, not modal:
> About to remove 12 items (38 GB). [ Confirm ]   [ Cancel ]
> ☐ Dry run only (show what would happen without deleting)

**Step 4 — Execution (immediate feedback)**

Progress strip at the top of the screen:
> Recovering space… 8 of 12 complete

**Step 5 — Post-execution (confirmation + undo)**

> ✓ Recovered 38 GB. 12 items removed.
> [ Undo (24h) ]   [ View what was removed ]

The undo window is critical. It replaces the friction of a confirmation dialog with the safety of reversibility.

**Step 6 — Reconciliation (invisible)**

The backend reconciles with qBittorrent/*arr automatically. The user never sees a "Reconciliation" surface. If reconciliation finds a discrepancy, it appears in Health, not here.

### Risky-candidate sub-flow

The "Needs your judgment" path opens a focused review:
- One item at a time, full context (poster, last played, seed status, why it was flagged)
- Three buttons: **Remove** / **Keep** / **Remind me later**
- No more than ~5 items expected here — if more, the rules are wrong, not the user.

### What this redesign kills
- The separate "Detection" surface (the system has already detected; just show results)
- The separate "Batch Execution" feature (batch *is* the default; single-item is the exception)
- The "Purge Queue" as a user-facing concept (it's an implementation detail)
- Asking the user to evaluate items one by one when the system can confidently group them

---

## 8. SCREEN INVENTORY

**v1.1 reconciliation (per audit finding M6).** The original "six screens, that's the budget" framing was ambiguous: it conflated primary navigation destinations with the broader set of screens an application needs (item details, sub-flows, onboarding). The corrected framing:

- **5 primary navigation destinations** — appear in the global header / bottom tab bar: **Home, Recover Space, Library, Health, Settings**. This is the budget that matters for nav cognitive load.
- **Sub-screens** — reachable only from within a parent flow; never appear in the global nav. Item Detail, Safe Candidate Review, Risky Candidate Review (Item Judgment), Preview, Cleanup History, Cleanup Batch Detail, Integration Detail, and Diagnostics are all sub-screens.
- **Pre-auth flow** — First Run Experience, seen only on first install.

The "no new screens" rule from `DESIGN_AUTHORITY.md` continues to apply to the **5 primary destinations**. New sub-screens or pre-auth flows still require Blueprint updates before implementation.

| Tier | # | Screen | Purpose | Primary action | Secondary |
|---|---|---|---|---|---|
| Primary | 1 | **Home** | Is everything okay? Is there one important thing to do? | Resolve top suggestion (usually "Recover X GB") | Jump to Library, Health (via nav or explicit links) |
| Primary | 2 | **Recover Space** | Free up disk | "Recover X GB" | Review safe items, review risky items, preview, history |
| Primary | 3 | **Library** | What's in my library and what's its status? | Search / open an item | Filter by status |
| Primary | 4 | **Health** | What's broken or stuck? | Resolve top issue | Per-row Inspect; Stuck items inline (no separate screen) |
| Primary | 5 | **Settings** | Configure | Save | Toggle Expert Mode, view diagnostics, manage integrations |
| Sub | — | Safe Candidate Review | Verify safe-item selection | "Recover X GB" (live total) | Why safe?, Cancel |
| Sub | — | Risky Candidate Review (Item Judgment) | Decide one risky item | Remove / Keep / Later | Why risky?, Skip |
| Sub | — | Preview (dry-run) | Show projected outcome | Proceed and recover X GB | Cancel |
| Sub | — | Cleanup History | Past cleanup batches | Open a batch | (none at list level) |
| Sub | — | Cleanup Batch Detail | Inspect / undo a batch | Undo all | Restore item, Close |
| Sub | — | Item Detail | Everything about one item | Contextual (Verify / Remove / View in Health) | Open in *arr, Inspect (Expert) |
| Sub | — | Integration Detail | Fix one integration | Test connection / Reconnect | Edit settings, View logs (Expert) |
| Sub | — | Diagnostics | Deep inspection | (read-only) | Re-run, Export logs |
| Pre-auth | — | First Run Experience | 3-step onboarding | Continue / Finish | Skip for now |

That's it. Anything not on this list either doesn't exist as a screen or lives as a drawer/modal/section within one of these.

---

## 9. DASHBOARD (HOME) REDESIGN

### Layout (top to bottom)

**Above the fold:**

1. **The one important thing.** A single banner card that shows the highest-value action right now. Priority order:
   - Critical health issue ("qBittorrent unreachable")
   - Meaningful space to recover ("42 GB ready to recover")
   - Stuck items ("3 downloads haven't progressed in 24h")
   - Nothing → calm success state ("Everything's running smoothly")

2. **Three at-a-glance tiles** (small, single-metric, no charts):
   - **Storage** — "1.8 TB free of 8 TB" + thin progress bar
   - **Recent activity** — "12 imports in the last 7 days"
   - **Health** — "All integrations connected" or "⚠ 2 issues"

**Below the fold:**

3. **Recently added** — last 5 items, poster + title. Useful, low-stakes.
4. **Quick links** to Recover Space, Library, Health (redundant with nav; helps discovery)

### What is never visible immediately
- Correlation results
- Lifecycle timelines
- Attribution details
- Raw counts of analyzed/processed/skipped items
- Configuration status (it's in Settings)
- Anything labeled "Engine," "Analysis," "Diagnostics"
- Charts. No charts on Home. If a chart is needed, it lives in a detail screen.

### What metrics deserve cards
A metric earns a card only if it answers: *"Does this change what the user does right now?"*

- ✅ Free space (drives cleanup behavior)
- ✅ Pending recovery (drives cleanup behavior)
- ✅ Integration health (drives troubleshooting)
- ❌ Total items processed (vanity)
- ❌ Correlation accuracy (internal QA metric)
- ❌ Items analyzed today (vanity)

### Idle state
When nothing needs attention:
> ✓ Everything's running smoothly.
> Last cleanup recovered 24 GB · 6 days ago.
> Next check in 18 hours.

Calm, confident, no false urgency.

---

## 10. TERMINOLOGY REWRITE

| Internal / Current | User-facing | Notes |
|---|---|---|
| Cleanup Detection | *(invisible — just "what we found")* | Not a feature, a step |
| Cleanup Review | Review items | Action, not a noun |
| Safe Review Candidate | Safe to remove | Plain language |
| Risky Review Candidate | Needs your judgment | Reframes from "risky" (scary) to user agency |
| Cleanup Execution | Recover space | Outcome, not mechanism |
| Batch Cleanup Execution | *(removed — batch is default)* | |
| Purge Queue | *(invisible)* | Implementation detail |
| Decision Center | *(removed)* | Decisions live where they're needed |
| Decision Analysis | Why safe? / Why risky? / Why? | Inline Evidence Drawer; never a surface. v1.1 T1 standardizes the link label by context: `Why safe?` in safe-cleanup contexts, `Why risky?` in risky-cleanup contexts, `Why?` as the generic fallback (Item Detail, Diagnostics, Health). The earlier variant `Why? Details` is retired. |
| Lifecycle Timeline | History | Expert Mode only |
| Lifecycle Analysis | *(removed as a surface)* | Powers History |
| Correlation Engine | *(invisible)* | Internal |
| Responsibility Attribution | Source: qBittorrent / Sonarr / Manual | Shown as a badge |
| Storage Recovery Analysis | Recover Space | Becomes the screen |
| Validation | *(moved to Health)* | "Library check" if surfaced |
| Diagnostics | Diagnostics | Only in Settings, Expert Mode |
| Reconciliation | *(invisible)* | Background process |
| Import Tracking | Recent activity | Plain language |
| Library Verification | Library check | If surfaced at all |
| Recommendations | Suggestions | But better: just *do them* by default |
| Dry-run | Preview only | Universal language |
| Orphaned download | "qBittorrent has this but Sonarr doesn't" | Plain explanation |

**Rule:** If a label requires a tooltip to explain, the label is wrong.

**v1.1 narrow exception (per audit finding C4).** Two labels are permitted **only** inside Settings → Diagnostics, the Expert-mode-only operator surface: the section header `Engine status` and the row label `Reconciliation`. These terms are the lowest-cost vocabulary for the Riley/Pat operator audience that screen serves; renaming would require new labels less precise than the existing ones. The exception does not extend to any Normal-Mode surface, any other Expert surface, or to the Charter principle "speak the user's language, not the codebase's" — which still binds everywhere else.

---

## 11. DESIGN SYSTEM FOUNDATION

### Layout philosophy
**One-column priority.** Wide screens are tempting, but split layouts force the eye to choose. Default to a centered, single-column flow with a max content width (~960px). Sidebars are for navigation only, never for content the user needs to read. Density is earned per-screen, not granted globally.

### Spacing philosophy
**Generous, consistent, on a scale.** Use a 4 or 8px base scale. Negative space is the cheapest hierarchy tool there is — use it before resorting to dividers, borders, or color. If two things feel related, space them tighter; if they're separate, space them further. Avoid borders to indicate grouping when spacing can do the same job.

### Card philosophy
**Cards are commitments, not containers.** A card means "this is one cohesive thing you can act on." Don't use cards as visual decoration. Rule: a card has a title, a body, and ideally an action. If it has none of these, it's a section, not a card. Limit cards-per-screen aggressively — five cards usually means five competing priorities, which means no priority.

### Table philosophy
**Tables are for comparing rows on the same attributes, nothing else.** If users will scan one row at a time, use a list. If they'll act on one row, use a detail view. Tables get: sticky headers, sortable columns, max 5 visible columns by default, row-level primary action. Never a table where the user is expected to read every row.

### Color usage philosophy
**Color is meaning, not decoration.** Reserve:
- **Red:** destructive actions, errors, critical health issues only
- **Yellow:** warnings that require user judgment, used sparingly — if everything is yellow, nothing is
- **Green:** success states and completed actions, not "this is fine right now" (calm gray is fine for fine)
- **Accent (one color):** primary actions and current navigation state
- **Neutral grayscale:** everything else, including most data

If a screen has more than three colors in use simultaneously, it's a bug.

### Warning philosophy
**Three tiers, strict separation:**
1. **Info** (neutral) — "We did this for you" — fades / dismisses
2. **Caution** (yellow, requires acknowledgment) — "This needs your judgment" — sticky until resolved
3. **Critical** (red, blocks) — "Something is wrong that you must address" — appears in Health and as a banner

Never use warning styling for non-warnings. Don't yellow-badge things that are working as designed.

### Confirmation philosophy
**Confirmation is the last resort.** Order of preference:
1. **Make it reversible** (undo) — preferred
2. **Show context inline** (preview what will happen) — second choice
3. **Explicit confirmation dialog** — only for irreversible, high-stakes actions
4. **Type-to-confirm** — only for catastrophic actions (delete everything)

Every confirmation should tell the user *what will happen*, not just *that something will happen*. "Are you sure?" without scope is meaningless.

---

## 12. ROADMAP

### Phase 1 — High-impact UX surgery (2–4 weeks)
**Goal: stop the bleeding without rebuilding.**
- Terminology rewrite across the existing UI (low effort, high impact)
- Redesign cleanup flow into the three-section summary (Safe / Judgment / Hidden)
- Add "Recover X GB" one-click batch action on safe items
- Add undo window for cleanup execution
- Collapse Diagnostics + Validation into a single Health surface
- Hide intelligence-engine surfaces (Correlation, Lifecycle, Decision, Attribution) from default nav

**Effort:** Medium. Mostly relabeling, restructuring, hiding.
**Impact:** Massive. Removes the top 3 audit findings.

### Phase 2 — Information architecture rebuild (4–8 weeks)
**Goal: the new nav, the new Home, the new flow.**
- Implement the 5-item nav
- Build the new Home with one-important-thing banner
- Build the Recover Space screen as designed
- Build Library with unified Item Detail
- Build Health as a real surface (not a diagnostic dump)
- Migrate existing data sources behind the new IA

**Effort:** High. This is real product work, not relabeling.
**Impact:** Transformational. Handoffarr becomes a product.

### Phase 3 — Expert Mode (3–5 weeks)
**Goal: serve Pat without compromising Sam.**
- Mode toggle in Settings
- Expert-mode panels for Lifecycle, Attribution, Diagnostics
- Per-item timeline view
- Dry-run as default for Expert-mode destructive actions
- Filters and bulk operations for Library and Recover Space
- Diagnostics surface with raw cross-references

**Effort:** Medium-high.
**Impact:** Retains power users without degrading the default experience.

### Phase 4 — Polish (ongoing)
- Empty/idle state design pass
- Onboarding for first-time users (3-step setup wizard)
- Keyboard shortcuts for Expert users
- Accessibility audit (focus order, contrast, screen reader)
- Microcopy pass: every label, button, error message reviewed against the charter
- Performance/perceived performance: skeleton states, optimistic UI for cleanup actions

**Effort:** Distributed, perpetual.
**Impact:** Compounding. This is what separates a working product from a beloved one.

---

## Closing Note: The Hardest Part

The hardest part of this redesign is not building the new screens. It is **deciding what not to show**. The engineering team built a sophisticated intelligence layer and will reasonably want to surface its capabilities. The discipline this redesign requires is: **the intelligence is the engine, not the dashboard.** Its job is to make the right things happen automatically and to make the user's decisions easier — not to be admired.

If, at the end of Phase 2, a new user can open Handoffarr, see that 42 GB is recoverable, click one button, and have it done in under 30 seconds — without ever reading the word "correlation" — the redesign has succeeded.