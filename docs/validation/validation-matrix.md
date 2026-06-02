# Validation Matrix

A spreadsheet-shaped record for walking real media items through the
lifecycle. Each row captures one media item; each column captures one
lifecycle fact. The matrix is the canonical "did Handoffarr see this the way
production saw it?" artefact.

## Columns

| Column | Meaning |
| --- | --- |
| Media | Title (and media_id) of the item being walked. |
| Request | Seerr request id and status, or `—` if not Seerr-originated. |
| Decision | `Good` / `Acceptable` / `Questionable` / `Bad` / `Unknown` (from `/api/decisions`). |
| Runtime | qBittorrent state classification (`Completed`, `Stalled`, `Downloading`, …). |
| Import | `Success` / `Failed` / `Pending`. |
| Library | `Present` / `Missing` / `Unknown`. |
| Cleanup | `Completed` / `Pending` / `Failed` / `Intentional` / `Unknown`. |
| Responsibility | `responsible_domain` from `/api/responsibility` (e.g. `Cleanup Subsystem`). |
| Recommendation | Top recommendation title for this item, or `—`. |
| Outcome | Expected category — `A` healthy, `B` cleanup, `C` import-fail, `D` library-missing, `E` bad torrent. |
| Pass | `✓` if Handoffarr's row matches expectation, `✗` otherwise. |
| Notes | Free text: anomalies, follow-ups, ticket references. |

The matrix should hold at least 20 rows when walked against a real
deployment. Use the sample below as a starting template and copy it into a
local checklist for each validation pass.

## Examples

| Media | Request | Decision | Runtime | Import | Library | Cleanup | Responsibility | Recommendation | Outcome | Pass | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Dune Part Two (1234) | Seerr #482 Approved | Good | Completed | Success | Present | Completed | — | — | A | ✓ | Clean walk |
| The Bear S03 (4521) | Seerr #501 Approved | Good | Seeding | Success | Present | Pending | Cleanup Subsystem | Reclaim 42 GB pending | B | ✓ | Seeding to ratio |
| Fallout S01 (9111) | Seerr #470 Approved | Acceptable | Completed | Failed | Unknown | Unknown | Radarr | Review import logs | C | ✓ | Permission denied on dest |
| Shogun S01 (8821) | Seerr #463 Approved | Good | Completed | Success | Missing | Unknown | Filesystem | Verify library path | D | ✗ | Path-mapping bug, see case study |
| Civil War (7732) | Seerr #455 Approved | Bad | Stalled | — | — | — | Indexer | Replace bad release | E | ✓ | Dead swarm |
| Furiosa (6611) | Manual | Unknown | Downloading | — | — | — | — | — | A (in-flight) | ✓ | Not yet completed |

## How to fill the matrix

1. Pick the items by walking `/api/timeline` and choosing one per category
   (A–E). Aim for at least four per category.
2. For each row, capture the `media_id` and the values from
   `/api/imports/{media_id}`, `/api/library/{media_id}`,
   `/api/cleanup/{media_id}`, `/api/decisions/{media_id}`,
   `/api/responsibility`, and `/api/recommendations`.
3. Compare each cell against the expected category. Mark `Pass` accordingly.
4. For any `Pass = ✗`, capture the debug export and write a case study.
