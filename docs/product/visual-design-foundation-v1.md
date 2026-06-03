# Handoffarr Visual Design Foundation — v1.1
## The visual layer for the approved Phase 2 blueprint

> **v1.1 note.** This revision incorporates the audit reconciliation. No tokens, scales, or component visuals were changed. The only edits: T1 evidence-drawer link label standardized (`Why safe?` / `Why risky?` / `Why?`), and a cross-reference to Blueprint v1.1 C1 ("Cards summarize. Buttons navigate.") added to §8.1.

---

## 0. PURPOSE & SCOPE

This document translates the blueprint's architectural decisions into a concrete visual system. It is the layer between "we know what to build" and "we can build it consistently."

**It does not redesign.** Information architecture, screen inventory, flows, and component anatomies are locked by the blueprint. This document only answers:

- What does it look like?
- What are the tokens?
- How do components render?
- How does it feel?

If a decision in this document contradicts the blueprint, the blueprint wins.

---

## 1. DESIGN PRINCIPLES (VISUAL)

These extend the Charter from the audit into visual-language territory. Every visual decision is checked against them.

1. **Quiet by default, loud only on signal.** The default screen looks like a reading app, not a control room. Warning colors and bold weights are reserved for moments that genuinely earn them.

2. **Hierarchy through space and weight, not lines and color.** Reach for whitespace and type weight before borders, dividers, or color fills. If a section needs a box to feel grouped, the spacing is wrong first.

3. **One accent, used sparingly.** A single accent color carries the primary action, the active nav state, and the focus ring. Everywhere else is neutral. If three things on screen are the accent color, two of them are wrong.

4. **Semantic color is a signal, not a style.** Green/amber/red mean something specific. They are never decorative. A green badge that doesn't represent success is a bug.

5. **Numbers and labels look stable.** Tabular figures, consistent units, monospaced where it aids scanning (sizes, hashes). The library should feel inventoried.

6. **Motion confirms, never entertains.** Transitions exist to maintain spatial continuity (drawer opens, sheet rises, state changes). No decorative animation. No spring physics.

7. **Dark mode is not a theme — it is the home.** Homelab users live in dark UIs. Dark mode is designed first; light mode is the courtesy port.

8. **The librarian aesthetic.** Confident, calm, slightly warm. Not enterprise SaaS. Not gamer-RGB. Closer to a well-organized reading room than a NOC dashboard.

---

## 2. COLOR SYSTEM

All colors are expressed in `oklch()` for perceptual consistency and easy dark/light parity. Hex fallbacks shown for tooling compatibility.

### 2.1 Neutrals — warm-tinted grayscale

A slight warm hue (hue 70°) avoids the clinical feel of pure grays. Used for background, surface, text, and dividers.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` | `oklch(0.985 0.003 70)` `#FBFAF8` | `oklch(0.16 0.004 70)` `#1A1917` | Page background |
| `--surface` | `oklch(1 0 0)` `#FFFFFF` | `oklch(0.20 0.005 70)` `#211F1C` | Cards, banners, sheets |
| `--surface-raised` | `oklch(1 0 0)` `#FFFFFF` | `oklch(0.235 0.006 70)` `#272421` | Hover, popover, drawer |
| `--border` | `oklch(0.92 0.004 70)` `#E8E5E0` | `oklch(0.28 0.006 70)` `#322F2B` | Hairlines (used rarely) |
| `--border-strong` | `oklch(0.85 0.005 70)` `#D2CEC7` | `oklch(0.35 0.007 70)` `#3F3B36` | Inputs, focus context |
| `--text` | `oklch(0.22 0.006 70)` `#272421` | `oklch(0.96 0.004 70)` `#F4F1ED` | Default body |
| `--text-muted` | `oklch(0.48 0.006 70)` `#736E66` | `oklch(0.72 0.006 70)` `#B6B0A7` | Meta, captions |
| `--text-subtle` | `oklch(0.62 0.005 70)` `#948E84` | `oklch(0.58 0.006 70)` `#8E887E` | Placeholders, disabled |

**Four shades of meaningful text contrast (not eight).** If a fifth neutral text shade is needed, the layout is wrong.

### 2.2 Accent — Indigo

One color. Used for: primary buttons, active nav, focus rings, links, the progress fill, the recover-space-total numeral.

| Token | Light | Dark |
|---|---|---|
| `--accent` | `oklch(0.56 0.18 268)` `#5B6CFF` | `oklch(0.66 0.17 268)` `#7C8BFF` |
| `--accent-hover` | `oklch(0.50 0.19 268)` `#4858EE` | `oklch(0.72 0.16 268)` `#94A1FF` |
| `--accent-quiet` | `oklch(0.96 0.02 268)` `#EFF0FF` | `oklch(0.28 0.06 268)` `#2A2D4A` |
| `--accent-on` | `oklch(0.99 0 0)` `#FFFFFF` | `oklch(0.16 0.02 268)` `#181B2A` |

Indigo over teal/blue because: (a) the *arr family already saturates the blue space — indigo gives Handoffarr a quiet differentiator; (b) it pairs cleanly with amber for caution states without clashing; (c) it reads as trustworthy/library rather than alert/system.

### 2.3 Semantic colors

Each has *quiet* (background tint) and *strong* (icon/text/border) variants. Never use the strong variant as a fill behind text.

**Success — Green**
| Token | Light | Dark |
|---|---|---|
| `--success` | `oklch(0.58 0.14 152)` `#3BA76A` | `oklch(0.70 0.14 152)` `#5EC78A` |
| `--success-quiet` | `oklch(0.96 0.04 152)` `#E6F6EC` | `oklch(0.28 0.05 152)` `#1F3527` |

**Caution — Amber**
| Token | Light | Dark |
|---|---|---|
| `--caution` | `oklch(0.74 0.15 75)` `#D89A2B` | `oklch(0.80 0.15 75)` `#EBB14B` |
| `--caution-quiet` | `oklch(0.96 0.04 75)` `#FAF1DD` | `oklch(0.28 0.05 75)` `#3A2F18` |

**Critical — Red**
| Token | Light | Dark |
|---|---|---|
| `--critical` | `oklch(0.58 0.20 25)` `#D9483B` | `oklch(0.68 0.20 25)` `#F06A5D` |
| `--critical-quiet` | `oklch(0.96 0.04 25)` `#FBE9E6` | `oklch(0.28 0.06 25)` `#3D2220` |

### 2.4 Contrast guarantees

All text/background pairings meet **WCAG AA (4.5:1)** for body and **AAA (7:1)** for `--text` on `--bg`. Status icons accompany every semantic color use — color is never the sole signal.

### 2.5 Anti-patterns

- ❌ Using `--accent` for non-actionable elements (headings, badges, decoration).
- ❌ Using semantic quiet-tints as decorative section backgrounds.
- ❌ Painting healthy items green. Healthy = neutral. Green = a thing was completed.
- ❌ More than three semantic colors on a single screen simultaneously. Promote critical, queue the rest (per blueprint §10).

---

## 3. TYPOGRAPHY

### 3.1 Font stack

```css
--font-sans: "Inter Variable", "Inter", system-ui, -apple-system,
             "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
--font-mono: "JetBrains Mono", ui-monospace, "SF Mono", Menlo,
             Consolas, monospace;
```

Inter for everything readable. Monospace **only** for: file paths, hashes, log lines (Diagnostics), and raw IDs (Inspect tab).

**Tabular figures globally** via `font-variant-numeric: tabular-nums` — sizes, counts, percentages, timestamps. Numbers should not shift width as they change.

### 3.2 Scale

Five levels. No more. Sizes use `rem` to respect user font-size preferences; values below assume `1rem = 16px`.

| Level | Size / line-height | Weight | Tracking | Use |
|---|---|---|---|---|
| Display | `2rem` / `2.5rem` (32/40) | 600 | -0.01em | Banner headline ("42 GB ready to recover"). 1× per screen, max. |
| Title | `1.375rem` / `1.75rem` (22/28) | 600 | -0.005em | Screen titles, section titles |
| Subtitle | `1rem` / `1.375rem` (16/22) | 600 | 0 | Card titles, group headers |
| Body | `0.875rem` / `1.25rem` (14/20) | 400 | 0 | Default text |
| Meta | `0.75rem` / `1rem` (12/16) | 500 | 0.01em | Timestamps, sizes, captions, badges |

Mobile reduces Display to `1.75rem` / `2.25rem` (28/36). All other levels unchanged.

### 3.3 Hierarchy rules

- **Weight first, size second.** Two pieces of text at the same size can differ only by weight (400 vs 600). Don't reach for a new size level when weight will do.
- **Color is not hierarchy.** Use `--text` and `--text-muted` only — not the accent — to express emphasis.
- **Numbers in the Display level use weight 700, not 600.** The recover-space total ("42 GB") gets one extra notch of weight because it *is* the screen.
- **No all-caps body.** Section labels in component headers may use small-caps tracking (12px, 600, 0.06em tracking) — sparingly, and never in user-generated text.

### 3.4 Reading width

Body copy is capped at **~70 characters** per line (≈`44ch`). The 960px max content width accommodates this with comfortable margins; inside cards, copy may need its own max-width.

---

## 4. SPACING & LAYOUT

### 4.1 Token scale

The blueprint's 4px base, formalized:

| Token | Value | Semantic use |
|---|---|---|
| `--space-0` | 0 | — |
| `--space-1` | 4px | Intra-element (icon ↔ label) |
| `--space-2` | 8px | Tight pairings (badge padding) |
| `--space-3` | 12px | Compact gaps (table cells) |
| `--space-4` | 16px | Default (card padding, list rows) |
| `--space-5` | 24px | Related groups |
| `--space-6` | 32px | Section gaps |
| `--space-7` | 48px | Major sections |
| `--space-8` | 64px | Page rhythm (top of page, between hero and body) |

### 4.2 Layout primitives

- **Page max-width:** 960px, centered. Outer page gutter: 32px desktop, 16px mobile.
- **Card padding:** 24px desktop, 16px mobile. Top-of-banner padding 32px (hero feel).
- **Header height:** 56px fixed.
- **Mobile bottom nav:** 64px including safe-area inset.
- **Section rhythm:** 32px between cards within a screen, 48px between distinct sections.

### 4.3 Grid

A 12-column grid exists *only* for tile rows (Home stats, Health integrations) to enforce alignment. Everything else is a single column stack — no grid.

### 4.4 Anti-patterns

- ❌ Using borders to indicate grouping when spacing can do it.
- ❌ Equal spacing between unrelated and related items (collapses hierarchy).
- ❌ Custom one-off spacing values. If you reach for 18px, you mean 16px or 24px.

---

## 5. RADIUS, ELEVATION, BORDERS

### 5.1 Border radii

| Token | Value | Use |
|---|---|---|
| `--radius-sm` | 4px | Inputs, badges, micro-tags |
| `--radius-md` | 8px | Buttons, list rows, tiles |
| `--radius-lg` | 12px | Cards, banners, sheets |
| `--radius-pill` | 999px | Filter chips, status pills |

Only four. No 6, no 10.

### 5.2 Elevation

Flat by default. Three levels, used purposefully:

| Token | Shadow | Use |
|---|---|---|
| `--elev-0` | none | Surfaces flush with background (most things) |
| `--elev-1` | `0 1px 2px oklch(0 0 0 / 0.04), 0 1px 1px oklch(0 0 0 / 0.03)` | Cards on Home, banners |
| `--elev-2` | `0 8px 24px oklch(0 0 0 / 0.10), 0 2px 4px oklch(0 0 0 / 0.06)` | Popovers, dropdowns, bottom sheets |
| `--elev-3` | `0 24px 48px oklch(0 0 0 / 0.18)` | Modals (critical confirmations only) |

Dark mode replaces shadow with a 1px top highlight (`box-shadow: inset 0 1px 0 oklch(1 0 0 / 0.04)`) plus the same shadow at reduced opacity. Floating surfaces in dark mode read primarily by surface-color difference, not by drop shadow.

### 5.3 Borders

The default is *no* border. Use `--border` only when:
- Inputs need a perceivable edge (always).
- Tables need row separation that spacing cannot provide.
- Tile groups need to clarify clickable boundaries on hover.

Never use a border to separate sections when a 32px gap will do.

---

## 6. ICONOGRAPHY

### 6.1 System

**Lucide** (or equivalent: 1.5px stroke, 24px artboard, rounded joins). One library, one style, no mixing.

### 6.2 Sizes

| Size | Use |
|---|---|
| 14px | Inline with body text, status badges |
| 16px | Buttons, list rows |
| 20px | Section headers, banner icons |
| 24px | Empty states, large affordances |

### 6.3 Status icon vocabulary

A fixed mapping. These never get reassigned to different meanings.

| Icon | Meaning |
|---|---|
| `check-circle` ✓ | Success, completed, healthy, safe |
| `alert-triangle` ⚠ | Caution, needs judgment |
| `alert-octagon` ✕ | Critical, error, broken |
| `loader` ⟳ | In progress (animated 1.2s linear infinite rotation) |
| `pause-circle` ⏸ | Stuck, paused |
| `info` ⓘ | Informational, dismissible |
| `clock` 🕐 | Scheduled, time-based meta |

Status icons are paired with a label always. No color-only badges.

### 6.4 Decorative imagery

Posters from *arr metadata are the only decorative imagery. No abstract illustrations, no mascots, no empty-state cartoons. Empty states use type and a single icon, per §10.

---

## 7. MOTION

### 7.1 Timing

| Token | Value | Use |
|---|---|---|
| `--motion-fast` | 120ms | Hover, focus ring, button press |
| `--motion-base` | 180ms | Drawer/sheet open, expand/collapse |
| `--motion-slow` | 260ms | Modal entry, banner state change |

Easing: `--ease-out: cubic-bezier(0.2, 0.7, 0.2, 1)` for entries; `--ease-in: cubic-bezier(0.5, 0, 0.75, 0)` for exits.

### 7.2 Patterns

- **Drawer (Evidence, Item Detail Normal):** slides from right, 280–360px wide, `--motion-base` with `--ease-out`. Backdrop fades to 30% black over the same duration.
- **Bottom sheet (mobile):** slides from bottom edge, `--motion-base`, respects safe-area inset.
- **Inline expand (safe items list):** content height eases in `--motion-base`; do not animate width.
- **Banner state change:** crossfade old → new at `--motion-slow`; do not slide. The banner is a fixed slot, only its content changes.
- **Progress strip (Recovering…):** width tween at 60fps based on actual completion, not a synthetic loop. No indeterminate stripes.
- **Success ✓:** the check icon draws once on entry (200ms), then settles. Never loops.

### 7.3 What does not animate

- Hover states on Home tiles (they have no hover affordance — they aren't actions).
- Status badges. They change instantly.
- Numbers in counters during scroll. They are not slot machines.
- The `[EXPERT]` chip. Ever.

### 7.4 Reduced motion

`@media (prefers-reduced-motion: reduce)` collapses all durations to `0.01ms` and disables the loader spin (replace with three pulsing dots at 1s opacity cycle).

---

## 8. INTERACTION STATES

Every interactive element defines five states. No exceptions.

| State | Visual treatment |
|---|---|
| Default | Resting appearance |
| Hover | Subtle bg tint (`--surface-raised`) or 4% accent overlay for accent buttons. No scale, no translate. |
| Focus-visible | 2px `--accent` ring with 2px offset (`outline: 2px solid var(--accent); outline-offset: 2px;`). Visible on keyboard focus only. |
| Active (pressing) | 1px translate-y on buttons, slightly darker bg. ≤80ms. |
| Disabled | Opacity 0.5, `cursor: not-allowed`, no hover response. |

**Focus ring is non-negotiable.** It is the same accent color across light and dark. Never remove it without `:focus-visible` discrimination.

### 8.1 Cursor

- `pointer` on actual actions (buttons, links, clickable rows).
- `default` on stat tiles unless they are clickable (Home tiles are *not* — they are summaries).
- `text` only inside actual text inputs.

**v1.1 cross-reference (Blueprint C1).** Stat Tiles and section cards summarize state; they never serve as navigation. Navigation occurs via buttons, links, or nav entries. Health Integration Tiles are the only exception (each tile *is* the navigation affordance for that integration's detail screen) and they communicate this via cursor `pointer` and hover state.

---

## 9. COMPONENT VISUAL SPECS

Anatomies are fixed by the blueprint (§9 Component Library). This section specifies how they *render*.

### 9.1 Buttons

Three variants. No others.

**Primary** — for *the* action on a screen.
- Background `--accent`, text `--accent-on`, weight 600.
- Padding `10px 16px`, radius `--radius-md`, font 14/20.
- Hover: `--accent-hover`. Active: 1px translate-y.
- One per screen ideally. Two only when a `Confirm` and `Cancel` sit together — `Cancel` is Ghost.

**Secondary** — alternative actions equal in importance.
- Background `--surface-raised`, text `--text`, 1px `--border`.
- Same padding/radius as primary.

**Ghost** — tertiary, dismissive, low-stakes.
- No background, no border, text `--text-muted`, hover background `--surface-raised`.
- Same padding/radius.

**Size variants:** large (12px 20px, font 16/22) only inside banners; small (6px 12px, font 13/18) inside list rows.

**Destructive buttons are Primary with `--critical` instead of `--accent`.** They are never red Ghosts (too easy to miss) and never red Secondaries (too easy to misread as toggles).

### 9.2 Primary Banner (Home)

- Surface `--surface`, radius `--radius-lg`, padding 32px, `--elev-1`.
- Display headline (32/40, 700) in `--text`, with the numeral colored `--accent` when the banner is a recover-space state. Numerals colored `--critical` when the banner is a health-critical state.
- Subline at Body (14/20), `--text-muted`, max 70ch.
- Primary button right-aligned on desktop, full-width below subline on mobile.
- Meta ("Last cleanup: 6 days ago") at Meta (12/16), `--text-subtle`, sits to the right of or below the button.
- Idle variant: no button; reduced padding (24px); headline weight 600 (not 700); icon left of headline at 20px (`check-circle`, `--success`).

### 9.3 Stat Tile

- Surface `--surface`, radius `--radius-lg`, padding 20px, `--elev-0` (no shadow).
- Label at Meta (12/16, 500, `--text-muted`, small-caps tracking).
- Value at Title (22/28, 600, `--text`, tabular-nums).
- Supporting line at Meta (12/16, `--text-muted`).
- Optional thin progress bar (4px tall, radius pill, `--accent` fill on `--border` track).
- Not interactive. No hover state. No cursor change.

### 9.4 Recommendation Card (Recover Space sections)

- Surface `--surface`, radius `--radius-lg`, padding 24px, `--elev-1`.
- Header row: status icon (20px, semantic color) + title (Subtitle weight) + right-aligned count/size at Meta (`--text-muted`, tabular-nums).
- Subline at Body, `--text-muted`.
- Action row: Primary on the left, Secondary/Ghost following, 12px gap.
- Safe variant uses `--success` icon, Judgment uses `--caution` icon. The card background does **not** tint — only the icon carries color.

### 9.5 Item Row — Library

- Padding 16px vertical, 16px horizontal. Border-bottom `--border` (1px) between rows; no border on first/last.
- 48×72 poster thumbnail (radius 4px) on the left.
- Title (Body, 600), one-line truncation.
- Meta line: `Type · Size · Status badge` (Meta size, `--text-muted`).
- Hover: background `--surface-raised`. Entire row is the click target.

### 9.6 Item Row — Safe Candidate

- As Library row, plus a 16px checkbox on the far left.
- Selected state: checkbox accent-filled; row gains a 3px left bar in `--accent`.
- "Why safe?" link right-aligned at Meta size, `--accent` text, underline on hover.

### 9.7 Item Row — Risky (Judgment view)

- Centered column, max 480px wide.
- Poster 160×240, radius `--radius-md`.
- Title at Title level, size at Meta below.
- "Why this needs your judgment" header at Subtitle, then a bulleted list at Body. Bullet markers are `--caution` dots, not generic disc.
- Three buttons full-width-equal in a horizontal row on desktop, stacked full-width on mobile. All three are Secondary visual weight — equal weight is the point. Remove gets `--critical` text only; the surface does not turn red.
- Skip is Ghost, bottom-right.

### 9.8 Health Tile

- Two-column row inside a bordered tile group (this is one of the few legitimate border uses).
- Left column: status icon (16px, semantic) + name (Body, 600). Below name: "Last seen 12m ago" (Meta, `--text-muted`).
- Right column: status text + contextual button (`Fix` Primary if broken, nothing if healthy).
- Healthy tiles are `--text-muted` for the right-column text — they recede.

### 9.9 Evidence Drawer

**Trigger label (v1.1 T1):** `Why safe?` in safe-cleanup contexts, `Why risky?` in risky-cleanup contexts, `Why?` as the generic fallback in Item Detail, Diagnostics, and Health. The variant `Why? Details` is retired.

- Slides from right, 360px wide desktop (full-screen mobile).
- Surface `--surface-raised`, `--elev-2`, no radius on the screen-edge side.
- Header: 56px, drawer title + close button (X, 16px icon, Ghost button).
- Body padding 24px. Content uses Body + Meta types; lists are denser than main content (12px row gap).
- Backdrop is `oklch(0 0 0 / 0.30)` light, `oklch(0 0 0 / 0.50)` dark.

### 9.10 Inline Confirmation Strip

- Appears immediately below the section it confirms. Not a card — a flush horizontal strip.
- 16px vertical padding, separated from above content by a top border `--border-strong`.
- Left: confirmation text (Body), tabular-nums for sizes.
- Right: `Confirm` (Primary) `Preview first` (Secondary) `Cancel` (Ghost), in that order.
- Dry-run checkbox below the buttons, left-aligned, Meta size.

### 9.11 Confirmation Modal (rare)

- Reserved per blueprint for catastrophic actions. Surface `--surface`, `--elev-3`, max-width 480px, padding 32px.
- Title at Title level, body at Body. Two buttons bottom-right: destructive Primary + Ghost Cancel.
- Type-to-confirm field above buttons when used. Input borrows Input styling (§9.13) with `--critical` focus ring instead of `--accent`.

### 9.12 Success State Banner

- Replaces the section that was acted on; does not stack below it.
- Surface `--success-quiet`, text `--text`, icon `--success` at 20px.
- Format: `✓  Recovered 38 GB.  12 items removed.    [Undo (24h)]  [View what was removed]`.
- Undo button is Secondary; View is Ghost.
- After Undo window expires: banner converts to Meta-level inline note ("Removed 38 GB · 24 hours ago"), no buttons.

### 9.13 Inputs

- Height 36px (40px for primary search bar on Library).
- Background `--surface`, 1px `--border-strong`, radius `--radius-sm`.
- Padding 8px 12px, Body type.
- Focus: replace border with 2px `--accent`, no offset (inputs are containers, not click targets — different focus visual from buttons).
- Placeholders at `--text-subtle`.

### 9.14 Status Badge

- Pill shape (`--radius-pill`), padding `2px 8px`, Meta type, weight 500.
- Icon left at 14px + label. Background = quiet semantic; text = strong semantic; no border.
- Variants are fixed: Imported (success), Downloading (accent-quiet/accent), Stuck (caution), Not found (critical), Queued (neutral — `--border` bg, `--text-muted` text).

### 9.15 Mode Indicator

- Pill, 6px 10px, Meta 12/16, weight 600, letter-spacing 0.08em.
- `--accent-quiet` bg, `--accent` text. Static. No animation, no hover state.
- Sits in the top-right of the header, 16px from edge.

### 9.16 Filter Chip Row

- Pills, `--radius-pill`, 6px 12px, Body 14/20.
- Default: `--surface-raised` bg, `--text` text.
- Selected: `--accent` bg, `--accent-on` text.
- Sort dropdown is a Ghost button on the far right with a 16px chevron icon.

---

## 10. EMPTY, LOADING, AND ERROR STATES

The audit calls these out as underdesigned. They are not afterthoughts here.

### 10.1 Empty (idle success)

The single most important visual style after the banner. The default appearance when nothing requires the user.

- Centered column, max 360px.
- 24px `check-circle` in `--success`.
- Title-level message ("Everything's running smoothly.") in `--text`.
- Meta-level supporting line ("Last cleanup recovered 24 GB · 6 days ago.") in `--text-muted`.
- One Ghost button only if a manual action is meaningful ("Run a check now").
- Generous vertical breathing room — at least 48px above and below.

No illustrations, no mascots, no "nothing to see here" tone. The message is calm and confident.

### 10.2 Loading

- **Skeletons over spinners** for layout-known content (lists, cards). Skeleton blocks use `--border` bg with a 1.4s linear `opacity 0.5 → 1 → 0.5` pulse.
- **Inline spinner** (loader icon, 16–20px, `--accent`) for known short waits (button-action in flight).
- **Top progress strip** (3px, `--accent` fill on `--border` track) for screen-spanning execution like Recover. Determinate when possible; pulse-bar fallback only when no progress signal exists.
- No full-page spinners. The shell is always visible.

### 10.3 Error

- **Inline** for in-context errors (input validation): `--critical` text below the input, Meta size, icon left.
- **Section-level** for failed loads: surface `--critical-quiet`, icon + Body explanation + Secondary `Retry` button.
- **Banner-level** for system-wide critical issues (already specified §9.2 critical banner state).
- All error copy states *what failed and what the user can do*. Never "Something went wrong."

---

## 11. ACCESSIBILITY

### 11.1 Contrast targets

- Body text on background: ≥ 7:1 (AAA).
- Secondary/meta text on background: ≥ 4.5:1 (AA).
- Icon + label badges: ≥ 4.5:1 for the label; icons inherit.
- Focus rings: ≥ 3:1 against adjacent colors. The 2px ring at `--accent` clears this in both modes.

### 11.2 Focus order

- Tab order follows reading order. Skip-link at page top jumps to main content.
- Drawer open: focus moves to drawer title; close returns focus to the trigger.
- Modal open: focus trapped; Esc closes and returns focus.

### 11.3 Screen reader

- All status badges expose both icon meaning and label via `aria-label` / visible text.
- The "one important thing" banner has `role="region"` with an `aria-labelledby` pointing at its headline.
- Progress strips have `role="progressbar"` with current/min/max.
- The `[EXPERT]` chip is `aria-label="Expert mode active"`.

### 11.4 Keyboard

- All actions are keyboard-reachable. Item Judgment supports `R / K / L` shortcuts (Remove / Keep / Later) — Expert Mode only, and announced via a small Meta hint at the bottom of the screen when Expert is on.
- Escape closes drawers, sheets, and modals.

### 11.5 Motion preferences

Honored as specified §7.4.

---

## 12. DARK & LIGHT MODES

### 12.1 Default

Dark mode is the default for new installs. A `prefers-color-scheme` check on first visit picks the user's OS preference; the explicit toggle (Settings → Appearance) overrides.

### 12.2 Parity rule

Every component must render identically in structure across modes. Only color tokens swap. If a component needs a different *shape* in dark mode, the design is wrong.

### 12.3 Where modes diverge intentionally

- **Elevation:** light mode uses drop shadows; dark mode adds a 1px top inner highlight and reduces shadow opacity (per §5.2).
- **Poster thumbnails:** dark mode gets a 1px `oklch(1 0 0 / 0.06)` inner border to separate dark-edged posters from the surface.
- **Status quiet-tints:** dark mode quiet-tints are *darker* than the surface, not lighter — they sink, they don't pop.

### 12.4 What to avoid

- Pure black (`#000`) backgrounds. We use a near-black warm gray. Pure black amplifies smearing on OLED scroll and looks harsh.
- White (`#FFF`) text. We use `--text` (slightly off-white) for the same reason inverted.
- Tinting the dark mode with the accent. The accent appears only where it appears in light mode.

---

## 13. WRITING & MICROCOPY (visual implications)

The terminology rewrite (audit §10) is binding. This section addresses how copy renders, not what it says.

- **Sentence case everywhere.** Buttons, headings, labels. Title Case is reserved for proper nouns and brand names.
- **No trailing periods on buttons or labels.** "Recover 38 GB" — not "Recover 38 GB."
- **Periods on full sentences in body copy.** Always.
- **Numbers and units stay together.** Use a non-breaking space: "38 GB", "12 items", "24 h".
- **Sizes formatted via tabular nums, one decimal max:** "1.8 TB", "38 GB", "4.2 GB". Never "1.84 TB" on user surfaces (Expert may show more precision in Diagnostics).
- **Relative timestamps in Normal Mode** ("2 hours ago", "yesterday"). Absolute timestamps in Expert Mode (`Jun 1, 8:14 PM`). Item Detail's history switches based on mode.
- **The accent-colored numeral in the Display headline** is its own micro-pattern: only the numeric portion of the recover-space total takes accent color. Units stay in `--text`. "**42 GB** ready to recover" with 42 in accent, the rest neutral.

---

## 14. ASSET DELIVERY

### 14.1 Token output

Tokens ship as:
- CSS custom properties on `:root` (light) and `[data-theme="dark"]` (dark).
- A `tokens.json` mirror for design tools and future native targets.

### 14.2 Component package

A single component library (framework TBD, but the visual contract here is framework-independent). Each component exposes:
- Default + state visuals matching §8.
- Built-in dark/light parity.
- `data-density="comfortable" | "compact"` attribute. Comfortable is default; compact is Expert.

### 14.3 Icons

Lucide as a peer dependency. A short allowlist (the §6.3 vocabulary) is the only inventory the product should be importing from. New icons get reviewed before they're added — this is how we keep the visual language coherent.

---

## 15. IMPLEMENTATION SEQUENCE

Mapped to the blueprint's Phase 1–5.

**Phase 1 (Nav + IA):** Tokens (color, type, space), header shell, navigation, button/input/badge primitives, focus ring, dark mode parity. Nothing visual-flashy — establish the calm baseline. Mode toggle visible but Expert surfaces deferred.

**Phase 2 (Dashboard):** Primary Banner with state machine (critical / recover / stuck / idle). Stat Tile, Recently added list. Idle/empty state polish. This is the screen the whole visual language is judged by — get it right or redo it.

**Phase 3 (Recover Space):** Recommendation Cards, Safe candidate row + checkbox interaction, Risky judgment layout, Inline confirmation strip, Success banner with Undo, Preview state. Motion polish on expand/confirm/execute transitions.

**Phase 4 (Expert):** `[EXPERT]` chip, Inspect tabs, density toggle, Diagnostics layout, mono-font integration, additional timestamp formatting. No new tokens — Expert reuses everything.

**Phase 5 (Polish):** Mobile (bottom nav, bottom sheets, full-screen drawers), reduced-motion pass, accessibility audit against §11, microcopy pass against §13, skeleton states across every async surface.

---

## Closing: What the Visual Layer Promises

If the blueprint promised that Handoffarr would stop being a control panel and become a librarian, the visual layer is what makes that feel true on the first frame the user sees.

A calm warm-neutral surface. One quiet accent. Numbers that sit still. Whitespace that does the grouping. A single bold sentence that tells the user what to do next, and a single button that does it.

The discipline is the same as the blueprint's: **the absence of visual noise is the feature.** A screen with three colors, four type levels, and one primary action is not under-designed — it is correctly designed. Every additional weight, color, shadow, or animation has to earn its way in. Most don't.
