# Handoffarr Pipeline Model

This is the canonical semantic model for Handoffarr. It defines the lifecycle a
single media item passes through and the entities Handoffarr reasons about. Read
this before adding features — new collectors, rules, or views should map onto the
vocabulary defined here rather than inventing parallel concepts.

## Scope and constraints

Handoffarr observes exactly one path:

```
Seerr / Jellyseerr / Overseerr  →  Radarr  →  qBittorrent
```

It is strictly **read-only**: it polls the official APIs of each service, stores
what it sees in local SQLite, and renders a diagnosis. It never adds, deletes,
pauses, resumes, or otherwise modifies anything.

These constraints are part of the architecture, not incidental:

- One small container. One SQLite file. One background poll loop.
- No React, Redis, Celery, Kafka, Prometheus, Grafana, or message brokers.
- No microservices, no distributed coordination, no external queues.

Keep it lightweight and operational. Do **not** redesign Handoffarr into a
distributed platform. When a feature seems to need heavy orchestration, the
answer is almost always a new pure interpreter function or one more read-only
collector, not new infrastructure.

## The canonical lifecycle

A media item moves through ten phases. Handoffarr does not control any of them —
the request manager, Radarr, the indexer, and qBittorrent do the work. Handoffarr
*observes* the phases and reconstructs the path after the fact.

| # | Phase | Owner | What Handoffarr observes | Source in code |
|---|-------|-------|--------------------------|----------------|
| 1 | **request** | Seerr/Jellyseerr/Overseerr | The user asked for a title. | `collectors/seerr.py` |
| 2 | **search** | Radarr → indexer | Implicit. Handoffarr does not see the query; it only sees the result of a search in Radarr history. | (not directly observed) |
| 3 | **candidate discovery** | indexer | Implicit. Only the *chosen* candidate's metadata survives into Radarr history (`reported_seeds`, `indexer`). | (partially observed via `radarr` `data` blob) |
| 4 | **release decision** | Radarr | Radarr grabbed a specific release and reported what it knew about it. | `collectors/radarr.py` (`GRAB_EVENT_TYPES`) |
| 5 | **handoff** | Radarr → qBittorrent | The grabbed release is passed to the download client, identified by torrent hash / download id. | correlation match in `correlation.py` |
| 6 | **queueing** | qBittorrent | The torrent waits for a download slot (`queuedDL`, slot accounting). | `collectors/qbittorrent.py` `queue_report` |
| 7 | **runtime execution** | qBittorrent | The torrent actively downloads: state, peers, seeds, speed. | `collectors/qbittorrent.py` `collect` |
| 8 | **import** | Radarr | Radarr imports the completed download into the library. | `radarr` `downloadfolderimported` / `movieFileImported` |
| 9 | **diagnosis** | Handoffarr | A plain-language label is derived from the stitched-together state. | `correlation.diagnose`, `qbittorrent.diagnose_queue` |
| 10 | **outcome** | — | The terminal interpretation: healthy, completed/seeding, or a specific failure class. | `handoff_traces.diagnosis` |

Phases 2 and 3 are **inferred, not seen**. This is the single most important fact
about the model: Handoffarr cannot watch the indexer search or the candidate set.
It learns about the search only through the one release Radarr decided to grab.
This is the root of several observability gaps — see
[telemetry.md](telemetry.md).

## Canonical entities

These are the nouns the system reasons about. Some are concrete database rows;
others are conceptual roles played by fields inside a `raw_events` payload. Use
these names in code, comments, and future docs.

### Request
The user's ask, captured from Seerr/Jellyseerr/Overseerr.

- Stored as a `raw_events` row with `source = "seerr"`.
- Normalized shape: `id`, `status`, `title`, `requested_at`
  (`collectors/seerr.py` `_normalize_request`).
- `requested_at` is load-bearing: it anchors the title-window correlation to
  Radarr (`title_time_window_minutes`).

### Candidate
A discoverable release for a request. Conceptually there are many candidates per
search; Handoffarr only ever sees the **selected** one, reflected through Radarr.

- Not a standalone table. Its surviving attributes live on the Decision:
  `reported_seeds`, `reported_indexer`, `selected_release` (sourceTitle).
- The rejected candidates and the indexer's full result set are **not observable**
  — this is a deliberate V1 limitation, not a bug.

### Decision
Radarr's choice to grab a specific release. The pivot of the whole trace.

- Stored as a `raw_events` row with `source = "radarr"`, `event_type` a grab/import
  type.
- Normalized shape: `id`, `eventType`, `sourceTitle`, `downloadId`, `indexer`,
  `reported_seeds`, `movie_title`, `torrent_hash`
  (`collectors/radarr.py` `_normalize_record`).
- `reported_seeds` is a **point-in-time claim** scraped from the nested `data`
  blob under varying keys (`seeders` / `Seeders` / `seedCount`). If absent at grab
  time it is gone forever.

### Handoff
The reconstructed passthrough linking a Request → Decision → RuntimeState. This is
the central artifact Handoffarr produces.

- Stored in the `handoff_traces` table; rebuilt from scratch each correlation pass
  (`db.replace_traces` deletes and re-inserts — traces are derived state).
- Carries the dashboard columns plus in-memory correlation diagnostics
  (`match_source`, `match_confidence`, `match_reasons`, `normalized_title`) that
  the debug endpoints consume but the DB does not persist.
- See [handoffs.md](handoffs.md) for what survives each link.

### Rule
A configurable or hard-coded predicate that turns observed state into a judgment.

- Thresholds and matching toggles live in `config.yaml`
  (`thresholds`, `matching`); queue/runtime/tracker/operational heuristics live in
  `correlation.diagnose` and `qbittorrent.diagnose_queue`.
- Categories are defined in [interpreter-model.md](interpreter-model.md).

### RuntimeState
What qBittorrent is actually doing with the torrent right now.

- Stored as `raw_events` rows with `source = "qbittorrent"`.
- Normalized shape: `hash`, `name`, `state`, `num_seeds`, `num_leechs`, `seeds`
  (`num_complete`), `peers` (`num_incomplete`), `dlspeed`, `progress`
  (`collectors/qbittorrent.py` `_normalize_torrent`).
- The raw `state` string is mapped to a coarse category by `app/states.py`
  (`downloading`, `queued`, `stalled`, `completed`, `uploading`, `paused`,
  `error`, `other`).

### Interpretation
The output of applying Rules to a Handoff and its RuntimeState — a single
plain-language label plus, for queue/torrent reports, a list of findings.

- For per-item traces: the `diagnosis` string.
- For queue health: `(primary_label, severity, findings)` from `diagnose_queue`.
- Categories are enumerated in [interpreter-model.md](interpreter-model.md).

### Outcome
The terminal state of the lifecycle as Handoffarr understands it. Outcome is
simply the Interpretation once the item has reached a stable end — completed and
seeding, healthy, or parked in a specific failure class. Handoffarr has no
separate "closed" record; the latest Interpretation *is* the outcome.

## Entity relationships

```
Request (seerr)
   │  matched by normalized title within title_time_window_minutes
   ▼
Decision (radarr)  ──carries──▶ Candidate attributes (reported_seeds, indexer, sourceTitle)
   │  matched by torrent_hash → download_id → normalized title
   ▼
RuntimeState (qbittorrent)
   │  classified by app/states.py, judged by Rules
   ▼
Interpretation ──stabilizes into──▶ Outcome
   (all three persisted as a Handoff row in handoff_traces)
```

Correlation is rebuilt on every poll from the latest snapshot of each entity
within the lookback window (`lookback_minutes`). Handoffarr does not maintain a
durable per-item timeline; see the observability gaps in
[telemetry.md](telemetry.md).
