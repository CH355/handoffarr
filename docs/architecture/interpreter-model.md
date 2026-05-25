# Interpreter Model

Handoffarr turns observed state into plain-language judgments. This document
defines the rule categories that drive those judgments, the interpretation
categories they produce, and the strict architectural separation between the four
kinds of component in the system.

The whole interpreter layer is built from **pure functions over already-collected
data**. There is no engine, no DSL, no plugin system — just classification and
threshold logic in `correlation.py`, `qbittorrent.py`, and `states.py`. Keep it
that way. New diagnoses should be new pure functions or new branches in the
existing ones, not new infrastructure.

## The four-layer separation

Every part of Handoffarr falls into exactly one of these layers. Respect the
boundaries: a collector must not interpret, an interpreter must not do I/O, and
the dashboard must not compute health.

### 1. Collectors — `app/collectors/`
Read-only API clients. They log in, fetch, normalize raw payloads into our shapes,
and append `raw_events`. They never modify the upstream service and never decide
what state *means*.

- `seerr.py` → Requests
- `radarr.py` → Decisions (and the Candidate attributes that ride along)
- `qbittorrent.py` → RuntimeState (plus live queue/torrent inspection)

A collector's only judgment is *extraction* (which key held the value) and
*missing-field warnings* — never *diagnosis*.

### 2. Persistence — `app/db.py`
A single local SQLite file. Two tables:

- `raw_events` — append-only snapshots from collectors (the historical record).
- `handoff_traces` — the derived correlation result, fully **replaced** every
  pass (`replace_traces`), because traces are computed state, not a log.

Persistence stores; it does not fetch and does not interpret. No Redis, no
external store.

### 3. Interpreters — `correlation.py`, `qbittorrent.py` (diagnose_*), `states.py`
Pure functions mapping collected data → labels and findings:

- `states.classify` / `is_seeding_state` / `is_active_download_state` — raw
  qBittorrent state → coarse category.
- `correlation.build_traces` — stitch entities into Handoffs, choosing a
  `match_source` and confidence.
- `correlation.diagnose` — per-item swarm/handoff health → one label.
- `qbittorrent.diagnose_queue` — fleet/queue health → primary label + findings.
- `qbittorrent._diagnose_torrent` — single-torrent deep dive → reasons.

Interpreters take data in and return judgments out. They do no network I/O and
write nothing to the database (the debug interpreters recompute live for
inspection and persist nothing).

### 4. Dashboard / visualization — `app/main.py`, `app/templates/dashboard.html`
The FastAPI routes and the server-rendered HTML table, plus the JSON and debug
endpoints. This layer reads persisted traces and calls interpreters on demand; it
performs no correlation logic of its own. It is presentation only.

```
Upstream APIs ──▶ Collectors ──▶ Persistence ──▶ Interpreters ──▶ Dashboard
 (read-only)      normalize       SQLite          pure funcs       HTML/JSON
                  + warn          (raw_events,     (labels,         (read-only
                                   traces)          findings)        views)
```

## Rule categories

Rules are the predicates interpreters apply. They group into five categories.
Thresholds and matching behavior are configurable in `config.yaml`; the rest are
heuristics in code.

### Selection rules
Judge whether the *release Radarr chose* was a good pick, by comparing the
indexer's claimed seeds against reality.

- `thresholds.low_reported_seeds` (default 5) and
  `thresholds.healthy_reported_seeds` (default 20).
- The `matching.*` toggles that decide how a Decision is joined to a RuntimeState
  (`prefer_torrent_hash`, `fallback_to_download_id`,
  `fallback_to_normalized_title`, `title_time_window_minutes`).
- Live in `correlation.diagnose` (reported-vs-actual seed logic) and
  `correlation.build_traces` (match selection).

### Queue rules
Judge qBittorrent's *queue and slot accounting*.

- Slot occupancy vs `max_active_downloads`, `queueing_enabled`,
  `dont_count_slow_torrents`.
- Live in `qbittorrent.diagnose_queue` (`queue_saturated`, `slots_exhausted`,
  `slots_full`).

### Runtime rules
Judge the *live transfer health* of a torrent.

- State classification (`states.py`): active-download vs seeding vs paused vs
  error vs other.
- Zero-peers / zero-speed logic: dead swarm, choking (`dlspeed == 0` with peers
  present).
- Live in `correlation.diagnose` and `qbittorrent._diagnose_torrent`.

### Tracker rules
Judge *peer-discovery health* from tracker and DHT signals.

- qBittorrent tracker `status` enum (working / not working / …), "no working
  trackers," DHT node count == 0.
- Live in `qbittorrent._diagnose_torrent` and `diagnose_queue` (`dht_no_nodes`).

### Operational rules
Judge the *environment* around the download, independent of any single release.

- Disk space (`DISK_CRITICAL_BYTES`, `DISK_LOW_BYTES`), error/missing-files
  states, alternative speed limits, global rate throttle, scheduler, paused
  queues, network/VPN connection status.
- Live in `qbittorrent.diagnose_queue`.

## Interpretation categories

Every judgment Handoffarr emits maps to one of these eight categories. Use these
canonical names; the strings below show how they surface today.

### Stale swarm metadata
The indexer claimed plenty of seeds but qBittorrent sees zero peers while
stalled — the metadata is stale or qBittorrent connectivity is broken.
- Surfaces as: *"Possible stale indexer/tracker metadata or qBittorrent
  connectivity issue."*
- Triggered by: selection + runtime rules (reported ≥ healthy, peers == 0, state
  contains `stall`).

### Queue saturation
All download slots are occupied and more torrents are waiting behind them; work
is serialized.
- Surfaces as: *"Queue saturated."*
- Triggered by: queue rules (`slots_full and queued > 0`).

### Slot exhaustion
All download slots are in use but nothing is backed up behind them yet — new
downloads will wait.
- Surfaces as: *"Download slots exhausted."*
- Triggered by: queue rules (`slots_full` without a queued backlog).

### Dead swarm
The release simply has no one to download from: zero seeds and zero peers, or a
low-availability pick that never found peers.
- Surfaces as: *"Likely bad low-availability release selected upstream"* /
  per-torrent *"Zero seeds and zero peers — dead swarm or unreachable network."*
- Triggered by: selection + runtime rules.

### Metadata deadlock
Torrents stuck fetching metadata (`metaDL`) hold download slots while moving no
data; if they can't reach peers they block real downloads from starting.
- Surfaces as: *"Metadata acquisition bottleneck."*
- Triggered by: runtime + queue rules (`metadata_bottleneck`).

### Network degradation
The problem is fleet-wide, not release-specific: many active torrents show zero
peers/throughput, DHT is unreachable, or qBittorrent reports disconnected.
- Surfaces as: *"Possible qBittorrent/VPN/network issue"* (per item) /
  *"Possible network/VPN issue"* (queue).
- Triggered by: runtime + tracker + operational rules
  (`network_wide_zero_peers`, `widespread_stall`, `connection_disconnected`).

### Operational bottleneck
The environment is the constraint: low/critical disk, error states, global
throttle or alt-speed limits, or everything paused.
- Surfaces as: queue findings such as *"Possible queue, disk, or peer choking
  issue,"* `disk_critical`, `all_downloads_paused`, `global_download_throttled`.
- Triggered by: operational rules.

### Healthy lifecycle
No problem detected, or the item has legitimately finished.
- Surfaces as: *"Healthy / no issue detected,"* *"Completed / seeding state,"*
  *"Healthy queue."*
- Triggered by: the fall-through case once seeding/completed states short-circuit
  the failure rules.

## How a per-item diagnosis is decided

`correlation.diagnose` evaluates in priority order, most-specific cause first:

1. No Radarr decision yet → *request not handed off / correlation failed.*
2. Decision but no matching RuntimeState → *Radarr grabbed but qBittorrent has
   nothing.*
3. Seeding/completed state → short-circuit to *Completed / seeding* (failure rules
   never apply to finished torrents — this guard is deliberate).
4. Active download → run selection, runtime, and network rules in order.
5. Fall through → *Healthy.*

`qbittorrent.diagnose_queue` mirrors this: it collects **all** findings (so the
report explains everything it saw) but elects a single primary label by priority:
network → metadata deadlock → excessive stalled → queue saturated → slots
exhausted → healthy.

This priority ordering is the contract. When adding a rule, decide where it sits
in the priority chain rather than letting two diagnoses compete for the headline.
