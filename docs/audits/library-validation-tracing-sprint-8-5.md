# Sprint 8.5 Library & Validation Endpoint Tracing Audit

Date: 2026-06-19
Branch: `audit/library-validation-tracing`
Production host: `casaos`
Recovery continuation: 2026-06-19

## Scope

This sprint added temporary tracing only. No endpoint behavior, UI code, caching
strategy, indexes, query shape, cleanup logic, or response schema was changed.

Local authoritative docs available in this worktree:

- `docs/audits/frontend-performance-rendering-sprint-8-4.md`

The named Sprint 8.2 and Sprint 8.3 audit docs were not present locally.

## Production Access Note

Production SSH and HTTP access were available for initial instrumentation and
measurements, then both `casaos:22` and `192.168.55.12:8099` became unreachable
from this workstation.

Evidence collected before connectivity dropped:

- `/api/validation` pre-container instrumentation: `97.231809 s`, `983 B`
- `/api/validation` after host-file copy/restart, before container copy:
  `91.364113 s`, `983 B`
- `/api/library`: `6.502050 s`, `480475 B`
- `/api/validation` with in-container tracing: `87.224473 s`, `983 B`
- Recovery continuation `/api/validation`: `89.501010 s`, `983 B`
- Recovery continuation `/api/library`: `5.624421 s`, `480475 B`
- Container backup path: `/tmp/handoffarr-container-backup-20260619083827`
- Host backup path: `/tmp/handoffarr-audit-backup-20260619083554`

The required five-sample set for every endpoint and item-detail samples could
not be completed after connectivity dropped. During recovery, SSH and app
access returned long enough to verify the environment and capture one more
traced validation sample plus one library sample. Access then dropped again:
`ping 192.168.55.12` continued to pass with 0% packet loss, but TCP checks for
`casaos:22` and `192.168.55.12:8099` failed across multiple retries.

## Recovery Connectivity Status

Verified before the second connectivity loss:

- `ssh casaos`: OK
- Hostname: `casaos`
- Uptime: `14 days, 16:41`
- Container: `handoffarr Up 12 minutes`
- App: `http://127.0.0.1:8099/api/validation` returned HTTP `200`
- Production worktree branch: `ui/sprint-8-1-performance-manual-refresh`
- Production commit: `63b235a`
- Local audit branch: `audit/library-validation-tracing`
- Local audit commit base: `4ecd778`
- Production instrumentation: active inside `/app/app`

## Endpoint Flow Diagrams

### `GET /api/library`

```text
route api_library
  get_config()
  db.all_library_artifacts()
    SELECT * FROM library_artifacts ORDER BY observed_at DESC, id DESC
    JSON-decode evidence_json for each row
  library_response()
    enrich_library_artifacts()
      db.all_import_events()
        SELECT * FROM import_events ORDER BY import_timestamp DESC, id DESC
      db.events_for_source_since("qbittorrent", since)
      collapse qBittorrent events by torrent_hash
      per-artifact import correlation
      per-artifact download-copy correlation
      attach status, paths, cleanup-candidate flag, evidence
    summarize_library()
    partition present/missing/unknown/potential_cleanup_candidates
  JSONResponse serialization
```

Known DB reads by code path: 3.

### `GET /api/library/{media_id}`

```text
route api_library_media
  get_config()
  db.all_library_artifacts(media_id)
    SELECT * FROM library_artifacts WHERE media_id = ?
    JSON-decode evidence_json for each row
  media_library_response()
    enrich_library_artifacts()
      db.all_import_events()
      db.events_for_source_since("qbittorrent", since)
      collapse qBittorrent events
      correlate imports/download copies
    filter enriched artifacts by media_id
  JSONResponse serialization
```

Known DB reads by code path: 3.

### `GET /api/imports/{media_id}`

```text
route api_import_media
  db.all_import_events(media_id)
    SELECT * FROM import_events WHERE media_id = ?
    JSON-decode evidence_json for each row
  media_import_response()
    filter history by media_id
    choose latest event
  JSONResponse serialization
```

Known DB reads by code path: 1.

### `GET /api/validation`

```text
route api_validation
  get_config()
  asyncio.to_thread()
    cached_validation()
      validation_fingerprint()
        table_fingerprint import_events
        table_fingerprint library_artifacts
        table_fingerprint cleanup_events
        table_fingerprint recommendations
        completed_cleanup_execution_fingerprint
        table_fingerprint cleanup_execution_batches
        table_fingerprint handoff_traces
        raw_event_fingerprint cleanup/file_evidence
      db.projection_snapshot("validation:v1")
      on cache miss:
        cached_enriched_library_artifacts()
        cached_cleanup_review_items()
        run_validation()
          db.all_import_events()
          db.all_cleanup_events()
          db.all_recommendations()
          db.all_cleanup_executions(limit=5000)
          db.all_cleanup_execution_batches(limit=5000)
          latest_completed_execution_index()
          validation checks
          db.all_traces()
          completed execution reconciliation
          batch execution safety
        db.upsert_projection_snapshot("validation:v1")
  JSONResponse serialization
```

Validation fingerprint DB reads by code path: 8.
Validation generation DB reads after artifacts/review are provided: 6.
Cold validation can also run cleanup-review generation, whose code path reads
cleanup events, import events, library artifacts, traces, executions, and raw
file evidence through review helpers.

## Timing Breakdown

### `/api/validation`, traced production sample

Total request: `87217.86 ms`

| Stage | Time |
| --- | ---: |
| validation fingerprint | `9124.71 ms` |
| validation snapshot read | `0.85 ms` |
| validation cache state | miss |
| enriched library projection fingerprint | `1.54 ms` |
| enriched library projection snapshot read | `6.12 ms` |
| enriched library projection cache state | hit, `175` artifacts |
| cleanup review fingerprint | `316.80 ms` |
| cleanup review snapshot read | `32.99 ms` |
| cleanup review cache state | miss |
| cleanup review generation | `77421.78 ms`, `515` items |
| cleanup review snapshot write | `68.80 ms` |
| validation DB read import_events | `26.31 ms`, `560` rows |
| validation DB read cleanup_events | `121.19 ms`, `515` rows |
| validation DB read recommendations | `1.03 ms`, `3` rows |
| validation DB read cleanup_executions | `20.67 ms`, `55` rows |
| validation DB read cleanup_execution_batches | `22.77 ms`, `12` rows |
| completed execution index | `0.08 ms` |
| recommendation cleanup filter | `0.92 ms` |
| all validation checks combined | `3.21 ms` |
| validation DB read handoff_traces | `4.06 ms`, `74` rows |
| validation generation total | `78081.93 ms` |
| validation snapshot write | `4.80 ms` |
| endpoint validation_cache_lookup/threaded_validation | `87215.36/87216.51 ms` |
| JSON serialization | `0.87 ms` |
| payload | `983 B` |

### `/api/library`, production sample

Total timing collected before access dropped:

- Total: `6502.05 ms`
- Payload: `480475 B`
- Recovery continuation total: `5624.42 ms`
- Recovery continuation payload: `480475 B`

Route-stage evidence captured from instrumentation:

| Stage | Time |
| --- | ---: |
| import read | `20.18 ms` |
| qBittorrent raw-event read | `608.07 ms` |
| qBittorrent latest collapse | `10.98 ms` |
| enrichment transform/correlation | `3377.19 ms` |
| artifacts processed | `175` |
| import events processed | `560` |
| qBittorrent raw events processed | `29614` |
| qBittorrent latest events processed | `871` |

### `/api/library/{id}` and `/api/imports/{id}`

Item-detail production measurements are incomplete because production access
dropped before a real `media_id` could be sampled with tracing.

## Cold vs Warm Comparison

Collected validation samples:

| Request | Endpoint | Latency | Payload | Cache evidence |
| --- | --- | ---: | ---: | --- |
| first observed | `/api/validation` | `97.231809 s` | `983 B` | untraced |
| after host restart | `/api/validation` | `91.364113 s` | `983 B` | untraced |
| traced | `/api/validation` | `87.224473 s` | `983 B` | validation miss; cleanup review miss; enriched library hit |
| recovery traced | `/api/validation` | `89.501010 s` | `983 B` | validation miss; cleanup review miss; enriched library miss |

Second/third warm requests after the traced request were not collected because
SSH and HTTP connectivity dropped.

Recovery traced cache evidence:

- `validation:v1`: miss
- `validation_library_artifacts:v1`: miss
- `cleanup_review:v1`: miss
- `validation_library_artifacts:v1` rebuilt in `2682.16 ms`
- `cleanup_review:v1` rebuilt in `75545.04 ms`

## DB Activity Breakdown

### `/api/validation`, traced sample

Rows materialized during `run_validation()`:

- `import_events`: `560`
- `cleanup_events`: `515`
- `recommendations`: `3`
- `cleanup_executions`: `55`
- `cleanup_execution_batches`: `12`
- `handoff_traces`: `74`
- provided enriched library artifacts: `175`
- provided cleanup review items: `515`

Observed expensive DB-related work:

- `validation_fingerprint()` alone took `9124.71 ms` before cache lookup.
- Normal validation DB reads were not the dominant cost; the slowest direct
  validation table read was cleanup events at `121.19 ms`.
- Python cleanup-review generation dominated at `77421.78 ms`.

### `/api/library`

Expected by implementation:

- `library_artifacts`: all rows, observed related count `175`
- `import_events`: all rows, observed related count `560`
- qBittorrent raw events since lookback: count not captured before access loss
- transformed records: one enriched output per library artifact
- response duplicates each enriched artifact across `artifacts` plus one status
  partition and maybe `potential_cleanup_candidates`

### `/api/library/{id}`

Expected by implementation:

- `library_artifacts` filtered by media_id
- all `import_events`
- qBittorrent raw events since lookback
- transformed records: filtered library rows only, but still scans all import
  rows and all recent qBittorrent rows for enrichment

### `/api/imports/{id}`

Expected by implementation:

- `import_events` filtered by media_id
- transformed records: matching history rows

## Payload Analysis

Measured payloads:

- `/api/validation`: `983 B`
- `/api/library`: `480475 B`

Largest known structures by implementation:

- `/api/library.artifacts`: full enriched artifact list
- `/api/library.present`, `.missing`, `.unknown`: partition lists that repeat
  the same object structures also present in `artifacts`
- `/api/library.potential_cleanup_candidates`: another repeated subset

Potential duplication target: `/api/library` returns the same enriched artifact
objects in `artifacts` and status-specific arrays. This audit does not change
that behavior.

## Validation Behavior Analysis

Evidence:

- Validation does not rebuild enriched library artifacts on the traced sample:
  `validation_library_artifacts:v1 cache=hit artifacts=175`.
- On the recovery traced sample, validation did rebuild enriched library
  artifacts: `validation_library_artifacts:v1 cache=miss`, then
  `library_enrichment_for_validation elapsed_ms=2682.16`.
- Validation does trigger cleanup review generation when the cleanup review
  projection misses: `cleanup_review:v1 cache=miss` followed by
  `cleanup_review_generation elapsed_ms=77421.78`; recovery reproduced this
  with `cleanup_review_generation elapsed_ms=75545.04`.
- Validation does not directly invalidate caches in this path. It computes a
  fingerprint, reads projection snapshots, and writes snapshots on miss.
- Validation has cold paths:
  - validation fingerprint: `9124.71 ms`
  - recovery validation fingerprint: `5945.84 ms`
  - recovery cleanup-review fingerprint: `4945.88 ms`
  - cleanup review generation: `77421.78 ms`
  - recovery cleanup review generation: `75545.04 ms`
  - cleanup review snapshot write: `68.80 ms`

Evidence is insufficient to prove why the cleanup review cache missed on that
specific request. The fingerprint includes frequently changing tables/events,
including cleanup events, handoff traces, completed executions, and cleanup
file-evidence raw events.

## Item Detail Analysis

Instrumentation was added for:

- `/api/library/{media_id}` route DB read, projection, JSON serialization,
  payload bytes, rows, and found/missing state
- `/api/imports/{media_id}` route DB read, projection, JSON serialization,
  payload bytes, rows, and history count
- helper-level library enrichment and import filtering

Production item-detail measurements were not completed after connectivity
dropped. Additional measurements required:

- Select a production `media_id` from `/api/library`
- Run `/api/library/{media_id}` cold/second/third and five-sample set
- Run `/api/imports/{media_id}` cold/second/third and five-sample set
- Pull matching `handoffarr.perf` logs

## Root Cause Ranking

### Critical

Validation is blocked by cleanup review generation on cache miss.

Evidence: traced `/api/validation` total `87217.86 ms`; cleanup review
generation `77421.78 ms`.

### High

Validation fingerprinting is itself expensive before cache lookup.

Evidence: `validation_fingerprint elapsed_ms=9124.71` before the cache miss is
known.

### Medium

`/api/library` returns a large duplicated payload.

Evidence: production payload `480475 B`; implementation returns full artifacts
plus repeated partition arrays.

### Medium

`/api/library` and `/api/library/{id}` enrichment rereads import events and
qBittorrent raw events on every request.

Evidence: implementation flow and added tracing. Production stage timings were
not captured before access loss.

### Low

JSON serialization is not the validation bottleneck.

Evidence: validation JSON serialization `0.87 ms` for `983 B`.

## Exact Optimization Targets

No optimizations were implemented in Sprint 8.5. Targets for Sprint 8.6:

1. Decouple `/api/validation` from synchronous cleanup review generation.
2. Reduce or stabilize validation and cleanup-review fingerprint cost.
3. Investigate why `cleanup_review:v1` misses during Home validation requests.
4. Split `/api/library` list shape or remove repeated full-object partitions
   where API compatibility allows.
5. Avoid all-import/all-qBittorrent enrichment for `/api/library/{id}`.
6. Add permanent lightweight endpoint timing for critical API routes.

## Recommended Sprint 8.6 Roadmap

1. Make validation read an existing cleanup-review projection only, and report
   stale/missing review projection explicitly instead of generating it inline.
2. Add targeted fingerprint diagnostics that log which fingerprint component
   changed between validation requests.
3. Create item-detail-specific DB helpers that load only the selected media
   import/library/torrent evidence.
4. Introduce a lean library list response or pagination contract after API
   compatibility review.
5. Keep the temporary Sprint 8.5 traces until the missing five-sample and
   item-detail measurements are collected, then remove or downgrade them.

## Remaining Required Measurements

After production connectivity returns:

```text
/api/library                 five samples, cold/second/third, trace logs
/api/library/{media_id}      five samples, cold/second/third, trace logs
/api/imports/{media_id}      five samples, cold/second/third, trace logs
/api/validation              second/third/five samples after cache warm
payload object counts        via saved JSON payloads
DB query/row confirmation    via trace logs and SQLite counts
```
