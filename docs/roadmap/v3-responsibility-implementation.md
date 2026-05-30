# V3 Responsibility Implementation Roadmap

This roadmap describes the minimum practical implementation path for introducing
`ResponsibilityAssessment` into Handoffarr.

It does not define new architecture. The canonical architecture already lives in:

- `docs/architecture/pipeline-model.md`
- `docs/architecture/handoffs.md`
- `docs/architecture/interpreter-model.md`
- `docs/architecture/telemetry.md`
- `docs/architecture/import-model.md`
- `docs/architecture/cleanup-model.md`
- `docs/architecture/storage-model.md`
- `docs/architecture/responsibility-model.md`

The implementation should preserve the existing shape:

```text
Collectors -> Persistence -> Interpreters -> Dashboard
```

No framework, message bus, background worker, Redis, Kafka, Celery, external
database, or orchestration layer is required.

## Current Codebase Inventory

### Existing collectors

Current collectors live in `app/collectors/`:

| Collector | File | Current role | Persisted output |
|-----------|------|--------------|------------------|
| Seerr / Jellyseerr / Overseerr | `app/collectors/seerr.py` | Polls recent requests and normalizes request id, status, title, and requested timestamp. | `raw_events` rows with `source = "seerr"` and `event_type = "request"`. |
| Radarr | `app/collectors/radarr.py` | Polls recent history records, especially grab/import-shaped events, and normalizes selected release, indexer, reported seeds, download id, movie title, and torrent hash. | `raw_events` rows with `source = "radarr"` and grab/import event types. |
| qBittorrent | `app/collectors/qbittorrent.py` | Polls torrents and normalizes hash, name, state, seeds, peers, speed, progress, and optional trackers. Also exposes live queue/torrent diagnostics. | `raw_events` rows with `source = "qbittorrent"` and `event_type = "torrent"`. |

There is no filesystem collector today. There are no Sonarr, Lidarr, Prowlarr,
or Jellyfin collectors.

### Existing database tables

SQLite persistence lives in `app/db.py`.

Current tables:

| Table | Purpose |
|-------|---------|
| `raw_events` | Append-only collector snapshots. Columns include `source`, `event_type`, `external_id`, `title`, `torrent_hash`, `download_id`, `payload_json`, and `observed_at`. |
| `handoff_traces` | Derived snapshot rebuilt on every correlation pass. Columns include request, Radarr, qBittorrent, diagnosis, match, normalized title, and state-classification fields. |

The app already uses lightweight in-place migrations through
`_migrate_handoff_traces`. V3 should continue that pattern instead of adding a
migration framework.

### Existing correlation outputs

Correlation lives in `app/correlation.py`.

Current outputs:

- `build_traces(config)` returns derived handoff trace dictionaries.
- `run_correlation(config)` persists those traces through `db.replace_traces`.
- `correlation_report(config)` returns a live debug report without writing.
- `diagnose(...)` emits per-item lifecycle diagnosis strings.

Persisted trace fields already include:

- request evidence: `seerr_request_id`, `seerr_status`
- decision evidence: `radarr_history_id`, `selected_release`,
  `reported_seeds`, `reported_indexer`
- runtime evidence: `torrent_hash`, `download_id`, `qbittorrent_state`,
  `actual_seeds`, `actual_peers`, `dlspeed`
- interpretation evidence: `diagnosis`, `state_classification`
- correlation evidence: `match_source`, `match_confidence`, `match_reasons`,
  `normalized_title`

### Existing dashboard outputs

Dashboard routes and API routes live in `app/main.py`.

Current stable routes:

| Route | Output |
|-------|--------|
| `/` | Server-rendered dashboard from `app/templates/dashboard.html`. |
| `/timeline` | Server-rendered lifecycle projection from `app/templates/timeline.html`. |
| `/api/traces` | Persisted handoff traces. |
| `/api/timeline` | Timeline projection over persisted traces. |
| `/api/events` | Recent raw events. |
| `/api/poll-now` | Manual poll trigger. |

Current debug routes include:

- `/api/debug/radarr`
- `/api/debug/qbit`
- `/api/debug/seerr`
- `/api/debug/states`
- `/api/debug/queue`
- `/api/debug/torrent/{torrent_hash}`
- `/api/debug/correlation`
- `/api/debug/radarr-fields`

`dashboard.html` already renders:

- a qBittorrent queue card loaded from `/api/debug/queue`
- a handoff trace table
- diagnosis badges
- match confidence indicators
- qBittorrent state classification

### Existing trace persistence

`handoff_traces` is derived state. `db.replace_traces` deletes and re-inserts the
full trace snapshot on every correlation pass.

That behavior should continue for handoff traces. Responsibility assessments can
follow the same derived-snapshot pattern in a separate table, because the first
goal is current operational visibility, not a durable historical timeline.

## Implementation Principles

Reuse existing code whenever possible.

Prefer extending:

- `app/correlation.py`
- `app/db.py`
- `app/collectors/`
- `app/templates/dashboard.html`

Avoid introducing:

- frameworks
- message buses
- background workers
- Redis
- Kafka
- Celery
- external databases
- a frontend build system

Collectors should gather facts only. Interpreters should assign meaning.
Dashboard code should render interpreter output and should not invent
responsibility.

## Minimum Implementation Path

The fastest valuable path is to answer:

> Why is my disk full?

using only:

- qBittorrent
- filesystem observations
- existing traces

and without requiring:

- a Sonarr collector
- a Radarr collector expansion beyond the current history collector
- a Lidarr collector

This validates the Responsibility Model against the real 535 GB retained-storage
case before the app attempts richer media-application attribution.

The first implementation should therefore attribute the visible symptom to the
best evidence currently available:

- `Storage Failure` when the download volume is critically low or storage usage
  is dominated by retained completed torrents.
- `Cleanup Failure` when completed qBittorrent payloads remain and the app has
  evidence that they are likely retained post-download.
- `qBittorrent`, `Filesystem`, `Cleanup subsystem`, or `Unknown` as the initial
  responsible domain, with confidence based on available evidence.

Application-specific ownership, such as `Sonarr` or `Radarr`, comes later when
import and cleanup evidence names that application directly.

## Phase 1: Storage Visibility

Goal: make disk pressure and download-side storage visible as persisted facts.

### Files to modify

- `app/collectors/qbittorrent.py`
- `app/db.py`
- `app/main.py`
- `app/templates/dashboard.html`
- `config.example.yaml`

### New modules required

- `app/collectors/filesystem.py`

Keep it small and read-only. It should inspect configured paths and report size
and free-space observations.

### New database columns required

No new columns on `raw_events` are required. Store filesystem observations as
`raw_events`:

- `source = "filesystem"`
- `event_type = "volume"` for free-space snapshots
- `event_type = "artifact"` for configured path or folder-size observations
- `external_id = stable path-derived id`
- `title = path or friendly label`
- `payload_json = structured observation`

Add indexes only if needed after the initial implementation:

- optional `idx_raw_events_source_type` on `(source, event_type, observed_at)`

### New API routes required

- `GET /api/storage`

This should return a storage summary derived from persisted `raw_events`, not
from live filesystem reads inside the route.

Suggested response shape:

```json
{
  "summary": {
    "health": "critical",
    "free_bytes": 123456,
    "total_bytes": 1000000000000,
    "download_bytes": 535000000000,
    "completed_torrent_bytes": 535000000000,
    "reclaimable_candidate_bytes": 0
  },
  "volumes": [],
  "artifacts": []
}
```

### New dashboard components required

- Storage Health card in `dashboard.html`

Minimum fields:

- health label
- free space
- completed qBittorrent bytes
- retained torrent count
- top storage contributors

### Reuse

Reuse qBittorrent's existing `queue_report` free-space logic and
`_normalize_torrent_full` shape where possible. The collector should persist the
same kinds of facts that the current debug route only exposes ephemerally:

- `free_space_on_disk`
- `save_path`
- `size`
- `total_size`
- `amount_left`
- `progress`
- `state`
- `completion_on`
- `category`
- `tags`

## Phase 2: Import Visibility

Goal: expose whether completed downloads appear to have reached the library.

For the first useful implementation, this phase can be mostly conservative:
classify import evidence as `unknown` unless current Radarr history already
provides an import event. Do not block storage visibility on complete import
correlation.

### Files to modify

- `app/collectors/radarr.py`
- `app/correlation.py`
- `app/db.py`
- `app/main.py`

### New modules required

- None required for the minimal Radarr path.

Optional later module:

- `app/imports.py` for pure import interpretation if `correlation.py` becomes
  too crowded.

### New database columns required

No new columns are required for Phase 2 if import observations continue to use
`raw_events`.

If trace-level import state is needed for dashboard joins, add columns to
`handoff_traces` through `_TRACE_COLUMNS`:

- `import_status TEXT`
- `import_event_id TEXT`
- `library_path TEXT`
- `download_path TEXT`
- `import_reason TEXT`

### New API routes required

- `GET /api/imports`

Minimum response:

```json
{
  "summary": {
    "success": 0,
    "pending": 0,
    "failed": 0,
    "unknown": 0
  },
  "items": []
}
```

### New dashboard components required

- Import Health card or section

Minimum fields:

- success count
- pending count
- failed count
- unknown count
- largest completed downloads with unknown import state

### Reuse

Reuse existing Radarr history capture. It already admits
`downloadfolderimported` and `movieFileImported` event types through
`GRAB_EVENT_TYPES`. Extend normalization carefully rather than adding a second
Radarr client.

## Phase 3: Cleanup Visibility

Goal: identify retained completed downloads and split them from active runtime
problems.

This phase creates the bridge from storage facts to cleanup candidates.

### Files to modify

- `app/correlation.py`
- `app/db.py`
- `app/main.py`
- `app/templates/dashboard.html`
- `app/states.py` only if additional qBittorrent states need classification

### New modules required

- `app/cleanup.py`

This should be a pure interpreter module. It should not do I/O. It should accept
persisted qBittorrent/filesystem/import observations and return cleanup
interpretations.

### New database columns required

Prefer a new derived table rather than widening `handoff_traces` indefinitely:

```sql
CREATE TABLE IF NOT EXISTS cleanup_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cleanup_id TEXT,
    torrent_hash TEXT,
    download_id TEXT,
    title TEXT,
    download_path TEXT,
    library_path TEXT,
    size_bytes INTEGER,
    cleanup_status TEXT,
    retention_reason TEXT,
    evidence_json TEXT,
    correlation_confidence REAL,
    observed_at TEXT
);
```

Like `handoff_traces`, this can be replaced each poll as derived state.

### New API routes required

- `GET /api/cleanup`

Minimum response:

```json
{
  "summary": {
    "cleaned": 0,
    "pending": 0,
    "failed": 0,
    "retained": 352,
    "candidate_bytes": 535000000000
  },
  "candidates": []
}
```

### New dashboard components required

- Cleanup Health card
- Cleanup Candidates table

Minimum candidate row:

- title
- size
- torrent state
- download path
- cleanup status
- retention reason
- confidence

### Reuse

Reuse:

- `states.is_seeding_state`
- `states.classify`
- qBittorrent normalized torrent payloads in `raw_events`
- `match_confidence` and `match_reasons` from existing traces

Do not attempt automatic deletion. Cleanup candidates mean "operator review",
not mutation.

## Phase 4: ResponsibilityAssessment Generation

Goal: generate canonical `ResponsibilityAssessment` records from storage,
import, cleanup, and existing trace evidence.

### Files to modify

- `app/correlation.py`
- `app/db.py`
- `app/main.py`

### New modules required

- `app/responsibility.py`

This should be pure interpreter logic. It should accept already-collected facts
and derived cleanup/storage/import summaries, then return
`ResponsibilityAssessment` dictionaries.

### New database columns required

Create a derived snapshot table:

```sql
CREATE TABLE IF NOT EXISTS responsibility_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assessment_id TEXT,
    lifecycle_stage TEXT,
    diagnosis TEXT,
    responsible_domain TEXT,
    confidence TEXT,
    evidence_json TEXT,
    impact_json TEXT,
    recommended_action TEXT,
    observed_at TEXT
);
```

Add an index:

```sql
CREATE INDEX IF NOT EXISTS idx_responsibility_assessments_domain
    ON responsibility_assessments (responsible_domain, observed_at);
```

### New API routes required

- `GET /api/responsibility`

Minimum response:

```json
{
  "summary": {
    "top_domain": "Cleanup subsystem",
    "top_diagnosis": "Storage Failure",
    "critical_count": 1,
    "reclaimable_bytes": 535000000000
  },
  "assessments": []
}
```

### New dashboard components required

- Responsibility Summary card
- Responsibility Detail card or expandable row

Minimum card fields:

- diagnosis
- responsible domain
- confidence
- impact
- recommended action
- evidence bullets

### ResponsibilityAssessment MVP schema

The MVP should use the canonical fields directly:

```json
{
  "assessment_id": "storage:cleanup-subsystem:2026-05-29T22",
  "lifecycle_stage": "Storage",
  "diagnosis": "Storage Failure",
  "responsible_domain": "Cleanup subsystem",
  "confidence": "High",
  "evidence": [
    {
      "source": "qbittorrent",
      "field": "completed_torrents",
      "value": 352
    },
    {
      "source": "filesystem",
      "field": "download_bytes",
      "value": 535000000000
    }
  ],
  "impact": {
    "bytes_retained": 535000000000,
    "torrents_affected": 352,
    "free_bytes": 123456
  },
  "recommended_action": "Review cleanup candidates and remove-on-import policy before deleting anything manually.",
  "observed_at": "2026-05-29T22:00:00Z"
}
```

### Storage

Persist MVP assessments in `responsibility_assessments`. Replace the table
contents on each poll, just like `handoff_traces`, until there is a concrete need
for historical assessment retention.

### API route

Add `GET /api/responsibility` in `app/main.py`. It should read persisted
assessments from `db.py`; it should not re-run live collectors.

### Dashboard card

Add a top-level card above the existing queue card:

```text
Why is my disk full?
Storage Failure
Cleanup subsystem is very likely responsible.
Impact: 535 GB retained across 352 completed torrents.
Next: Review cleanup candidates and remove-on-import policy.
```

Confidence wording should follow `responsibility-model.md`:

| Confidence | Dashboard wording |
|------------|-------------------|
| Certain | Responsibility confirmed |
| High | Very likely responsible |
| Medium | Likely responsible |
| Low | Needs investigation |

## Phase 5: Dashboard Integration

Goal: make responsibility the first answer while preserving existing trace and
debug evidence.

### Files to modify

- `app/templates/dashboard.html`
- `app/main.py`
- optionally `app/templates/timeline.html`

### New modules required

- None.

### New database columns required

- None beyond `responsibility_assessments`.

### New API routes required

- No additional route beyond `/api/responsibility`.

Optional:

- `GET /api/dashboard-summary` if the dashboard begins making too many parallel
  requests.

### New dashboard components required

Add, in order:

1. Responsibility Summary
2. Storage Health
3. Cleanup Health
4. qBittorrent queue card
5. Existing handoff trace table

This keeps the first viewport operational:

- what happened
- who is likely responsible
- why
- impact
- what to review next

## First Useful Implementation

The first useful implementation must answer:

> Why is my disk full?

with only qBittorrent, filesystem, and existing traces.

### Required evidence

From qBittorrent:

- torrent hash
- name/title
- state
- size or total size
- progress
- amount left
- save path
- completion timestamp when available
- category/tags when available

From filesystem:

- configured volume path
- total bytes
- free bytes
- used bytes
- optional per-folder size for download roots

From existing traces:

- match confidence
- diagnosis
- selected release when present
- Radarr import event when already available

### Minimum rule

If:

- free space is below the configured critical threshold, and
- completed or seeding qBittorrent torrents account for a large retained byte
  total, and
- there is no stronger evidence of active download pressure,

then emit:

```text
lifecycle_stage: Storage
diagnosis: Storage Failure
responsible_domain: Cleanup subsystem
confidence: High when filesystem + qBittorrent agree, otherwise Medium
impact: bytes retained, torrents affected, free bytes
recommended_action: Review cleanup candidates and remove-on-import / retention policy.
```

If no filesystem collector data is available yet but qBittorrent reports
`free_space_on_disk`, emit the same assessment with `Medium` confidence and
evidence noting that host filesystem confirmation is missing.

If the completed torrents are actively uploading or carry clear retention tags,
downgrade from `Cleanup Failure` to `Retention Intentional` or `Storage Risk`,
depending on free space.

### Expected real-world validation

For the 535 GB case, the first useful output should be able to say:

```text
Storage Failure.
Cleanup subsystem is very likely responsible.
535 GB is retained across 352 completed qBittorrent torrents.
The download volume is critically low.
Review cleanup candidates and remove-on-import / retention policy.
```

It should not claim Sonarr, Radarr, or Lidarr caused the issue unless those
collectors provide direct policy/import evidence.

## Concrete Coding Sequence

### Step 1: Add storage collector

Add `app/collectors/filesystem.py`.

Implement read-only functions:

- `collect(config) -> int`
- `inspect(config) -> dict`

Persist:

- volume free-space observations
- configured download-root folder observations

Extend `config.example.yaml` with a `storage` or `filesystem` section:

```yaml
storage:
  enabled: true
  volumes:
    - label: downloads
      path: /downloads
  thresholds:
    critical_free_bytes: 1073741824
    warning_free_bytes: 10737418240
```

### Step 2: Persist richer qBittorrent storage observations

Extend `app/collectors/qbittorrent.py` so normal persisted torrent payloads
include storage fields already used by debug reports:

- `size`
- `total_size`
- `amount_left`
- `downloaded`
- `progress`
- `save_path`
- `completion_on`
- `category`
- `tags`

Do this by reusing or folding in `_normalize_torrent_full`, not by creating a
second normalization style.

### Step 3: Create storage interpreter

Add a pure helper, either in `app/correlation.py` for the smallest diff or in a
new `app/storage.py` if the logic is clearer there.

Inputs:

- recent `raw_events` from `filesystem`
- recent `raw_events` from `qbittorrent`

Outputs:

- storage health summary
- completed torrent byte totals
- retained torrent count
- top storage contributors

Persist only if dashboard/API need stable output. Otherwise compute from
persisted raw events on demand in `db.py` helper functions.

### Step 4: Persist storage observations API

Add `db` helpers:

- `events_for_source_since("filesystem", since)`
- `latest_events_by_source_type(...)` if useful

Add route:

- `GET /api/storage`

Add dashboard Storage Health card.

At this point, Handoffarr should already show whether retained qBittorrent
storage plausibly explains disk pressure.

### Step 5: Create cleanup candidate interpreter

Add `app/cleanup.py`.

Inputs:

- completed/seeding qBittorrent storage observations
- import evidence from existing traces/Radarr history when present
- filesystem artifact observations

Outputs:

- cleanup status per torrent/artifact
- candidate bytes
- retention reason
- confidence

Persist to `cleanup_assessments` using a replace-snapshot helper in `db.py`.

Add route:

- `GET /api/cleanup`

Add dashboard Cleanup Health card and Cleanup Candidates table.

### Step 6: Generate ResponsibilityAssessment

Add `app/responsibility.py`.

Implement the first rules:

1. Disk pressure explained by retained completed torrents.
2. Cleanup candidates explain reclaimable storage.
3. qBittorrent reports critical free space but filesystem confirmation is
   missing.
4. Storage pressure exists but retained content does not explain it.

Persist to `responsibility_assessments` using `db.replace_responsibility_assessments`.

Call responsibility generation after correlation in `poll_once`.

### Step 7: Expose dashboard summary

Add route:

- `GET /api/responsibility`

Add top-level dashboard Responsibility Summary card.

Keep the card short and evidence-backed:

- diagnosis
- responsible domain
- confidence wording
- impact
- next action

### Step 8: Tighten import and cleanup confidence

Extend `app/collectors/radarr.py` only where current history payloads already
provide useful facts:

- import success/failure event type
- movie id
- library path when present
- download path when present
- reason/error when present

Then update cleanup confidence:

- `High` when import success, library evidence, and retained download artifact
  all align.
- `Medium` when qBittorrent/filesystem show retained completed storage but
  import evidence is missing.
- `Low` when only title/path inference exists.

## Phased Summary

| Phase | User-visible value | Main files | New table |
|-------|--------------------|------------|-----------|
| 1. Storage visibility | Shows disk pressure and retained download bytes. | `collectors/filesystem.py`, `collectors/qbittorrent.py`, `db.py`, `main.py`, `dashboard.html` | none |
| 2. Import visibility | Shows whether completed downloads appear imported, pending, failed, or unknown. | `collectors/radarr.py`, `correlation.py`, `db.py`, `main.py` | optional trace columns |
| 3. Cleanup visibility | Shows retained completed downloads and cleanup candidates. | `cleanup.py`, `correlation.py`, `db.py`, `main.py`, `dashboard.html` | `cleanup_assessments` |
| 4. Responsibility generation | Names the responsible domain with confidence, evidence, impact, and action. | `responsibility.py`, `correlation.py`, `db.py`, `main.py` | `responsibility_assessments` |
| 5. Dashboard integration | Makes "Why is my disk full?" the first dashboard answer. | `dashboard.html`, `main.py` | none |

## Non-Goals

Do not implement:

- automatic deletion
- torrent pause/resume/remove actions
- Radarr/Sonarr/Lidarr setting mutation
- a task queue
- a message bus
- Redis/Kafka/Celery
- a frontend framework
- a separate metrics system
- a new database

Do not require Sonarr, Radarr expansion, or Lidarr before validating the retained
storage case. The first milestone should work with qBittorrent plus filesystem
facts and should honestly label missing media-application evidence in the
assessment confidence.
