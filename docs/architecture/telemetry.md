# Telemetry Model

This document classifies the telemetry Handoffarr handles, defines how each class
is captured and retained, and records the observability gaps discovered building
V1. It complements the capture rules in [handoffs.md](handoffs.md) and the
layer separation in [interpreter-model.md](interpreter-model.md).

Telemetry policy follows the same constraint as the rest of the system: stay
lightweight. One SQLite file is the only store. There is no metrics backend, no
time-series database, no Prometheus, no log shipping. If a telemetry need seems to
require that, reconsider the need first.

## Telemetry classes

Handoffarr's data falls into four classes, distinguished by *how long it is true*
and *whether it is persisted*.

### Runtime telemetry
High-churn, live measurements of what qBittorrent is doing right now.

- Examples: `state`, `peers` (`num_incomplete`), `seeds` (`num_complete`),
  `dlspeed`, `progress`.
- Lifetime: valid only at the instant of the poll; meaningless minutes later.
- Capture: every poll (`poll_interval_seconds`), via `qbittorrent.collect`, stored
  as `raw_events`.
- This is the telemetry the "must capture immediately" rule in
  [handoffs.md](handoffs.md) is mostly about.

### Decision telemetry
Point-in-time facts recorded when Radarr grabs a release.

- Examples: `reported_seeds`, `indexer`, `selected_release` (sourceTitle),
  `downloadId`, `torrent_hash`.
- Lifetime: fixed at grab time and never updated upstream; if not captured on the
  poll that sees the grab, the *as-of-grab* value is lost (Radarr history shows
  the value as it was, the live swarm does not).
- Capture: `radarr.collect`, stored as `raw_events`.

### Historical telemetry
The accumulated `raw_events` table — every snapshot every collector has stored.

- Lifetime: persistent (subject to whatever retention the operator applies to the
  SQLite file; V1 does not prune).
- Use: correlation reads a recent slice (`lookback_minutes`) to rebuild traces;
  the `/api/events` endpoint exposes recent rows.
- This is the only durable history Handoffarr keeps, and it is per-snapshot, not
  per-item-timeline.

### Ephemeral telemetry
Live inspection data computed on demand and **never persisted**.

- Examples: queue diagnostics (`queue_report`), per-torrent deep dives
  (`torrent_report`: trackers, peers, properties, queue position), state reports,
  field discovery, recomputed correlation reports.
- Lifetime: exists only inside the HTTP response to a `/api/debug/*` call.
- Use: diagnosing real-world payload mismatches and root-causing the *current*
  state. Because it is not stored, you cannot see how any of it evolved.

| Class | Persisted? | Lifetime | Captured by |
|-------|-----------|----------|-------------|
| Runtime | yes (`raw_events`) | one poll | `qbittorrent.collect` |
| Decision | yes (`raw_events`) | fixed at grab | `radarr.collect`, `seerr.collect` |
| Historical | yes (`raw_events`) | until pruned | all collectors (accumulated) |
| Ephemeral | no | one HTTP response | `/api/debug/*` interpreters |

## Known observability gaps (discovered during V1)

These are deliberate limitations or known blind spots, not TODOs to be fixed by
re-architecting. Document them so diagnoses are read with the right caveats and so
future work targets the real gaps.

1. **The candidate set is invisible.** Handoffarr only ever sees the release
   Radarr *chose*. The search query and every rejected candidate are unobservable
   (lifecycle phases 2–3 are inferred). Handoffarr can say "the chosen release
   behaved badly," never "a better release was available."

2. **`reported_seeds` is a single fragile point.** It is scraped from a nested
   Radarr `data` blob under varying keys (`seeders` / `Seeders` / `seedCount`) and
   is frequently missing. When absent, selection-rule diagnoses degrade to "no
   seed count." It reflects only the grab instant, never the live swarm.

3. **No per-item timeline.** `handoff_traces` is fully replaced every correlation
   pass (`db.replace_traces`), and correlation keeps only the latest snapshot per
   entity within the lookback window. State *transitions* over time are not
   retained — only the current interpretation.

4. **Correlation can mis-match or miss.** When Radarr exposes no torrent hash, the
   join falls back to download id, then to fuzzy normalized-title matching
   (confidence 0.5) within a time window. This can link the wrong items or fail to
   link at all. The `match_source`/`match_confidence` are surfaced so the
   uncertainty is at least visible — but they are **not persisted** to the traces
   table, only available live via `/api/debug/correlation`.

5. **Queue / tracker / peer telemetry is live-only.** The richest diagnostics
   (`queue_report`, `torrent_report`) are ephemeral. There is no record of how
   queue health, tracker status, or peer counts evolved, so post-mortem analysis
   of a past incident is impossible — you can only inspect the present.

6. **Fleet heuristics under-trigger on small libraries.** The network-wide
   zero-peer signal requires at least 3 active torrents (and `widespread_stall`
   similarly). On a small or quiet instance, a genuine network problem affecting
   one or two torrents won't trip the fleet-level diagnosis.

7. **Search-side and playback-side blind spots.** No Sonarr (TV), no Prowlarr
   (indexer-level visibility into the actual search), no Jellyfin (playback /
   library confirmation). The chain begins at the Seerr request and ends at the
   qBittorrent runtime / Radarr import.

8. **Trace persistence is lossy by design.** `handoff_traces` stores only the
   dashboard columns. The correlation diagnostics (`match_source`,
   `match_confidence`, `match_reasons`, `normalized_title`) live in memory and are
   recomputed for the debug endpoints rather than saved.

9. **Single-host, unauthenticated.** One container, one SQLite file, no auth (V1
   targets trusted local networks). This bounds Handoffarr to a single deployment
   and a single trust domain — accepted, not a defect.

## Where each requirement is satisfied in code

| Telemetry concern | Code |
|-------------------|------|
| Runtime capture | `app/collectors/qbittorrent.py` `collect` / `_normalize_torrent` |
| Decision capture | `app/collectors/radarr.py` `collect` / `_normalize_record` |
| Request capture | `app/collectors/seerr.py` `collect` / `_normalize_request` |
| Historical store | `app/db.py` `raw_events`, `recent_events`, `events_for_source_since` |
| Derived traces | `app/db.py` `handoff_traces`, `replace_traces`, `all_traces` |
| Ephemeral inspection | `app/main.py` `/api/debug/*` → `inspect` / `queue_report` / `torrent_report` |
| State classification | `app/states.py` |
| Interpretation | `app/correlation.py`, `qbittorrent.diagnose_queue` |
