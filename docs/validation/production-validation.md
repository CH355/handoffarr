# Production Validation

Handoffarr is feature-complete across the lifecycle (Request → Decision →
Runtime → Import → Library → Cleanup → Responsibility → Recommendation →
Outcome). What it has not yet proven is that those interpreters agree with
reality on a running deployment. This document defines how we validate the
running system against production data.

## Methodology

1. Trigger a poll (`POST /api/poll-now`) and wait for collectors to settle.
2. Pull `/api/debug/export` to snapshot the current lifecycle state.
3. Run `/api/validation` to apply the automated checks.
4. For each lifecycle category below, walk a sample of real media items
   through the matrix in `validation-matrix.md` and verify the expected
   transitions hold.
5. Anything that fails is either a bug in an interpreter, a collector that is
   missing context, or a real production incident — file it as one of those
   three.

## Expected lifecycle transitions

A canonical healthy item moves through:

```
Request → Decision → Runtime → Import Success → Library Present → Cleanup Completed
```

Each stage produces a fact in storage that the next stage depends on. The
validation framework asserts the *consistency* of these facts; it does not
re-derive them.

## Pass / fail criteria

A run is considered **PASS** when every check in `/api/validation` reports
`status = OK` *and* every Category A item walked manually matches the matrix
columns. A run is **FAIL** if any check returns `FAIL`. A run is **WARN** if
checks pass but matrix walking surfaces unexplained `Unknown` states.

## Validation categories

### Category A — Healthy Pipeline

Expected facts present:

- Request (Seerr)
- Decision (Radarr/Sonarr/Lidarr history)
- Runtime (qBittorrent completed)
- Import Success
- Library Present
- Cleanup Completed

### Category B — Cleanup Candidate

- Import Success
- Library Present
- Download copy still present in qBittorrent
- Cleanup Pending
- Recoverable bytes > 0

### Category C — Failed Import

- Import Failure
- Responsibility assessment names the Import Subsystem (Radarr/Sonarr/Lidarr)

### Category D — Missing Library

- Import Success
- Library Missing (path expected, file not present)
- Responsibility assessment names the Library Subsystem (Filesystem)

### Category E — Bad Torrent

- Runtime Failure (stalled / dead swarm / etc.)
- Decision Quality = Bad Selection
- Responsibility assessment names the Decision Subsystem (Indexer / *arr)

## Troubleshooting workflow

When a check fails:

1. Read the failing item's full row via `/api/timeline/{media_id}` to see
   which stage's facts disagree.
2. Pull the supporting raw events via `/api/events?source=<source>`.
3. Pull `/api/debug/library`, `/api/debug/imports`, or
   `/api/debug/correlation` for the relevant subsystem.
4. If the disagreement is real, capture the debug export and add it to
   `/debug-fixtures` for regression coverage.
5. File the case under `docs/validation/` using the case-study template
   (see `case-study-library-verification.md`).
