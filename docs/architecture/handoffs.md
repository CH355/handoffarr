# Handoff Semantics

A *handoff* is the moment one service passes responsibility for an item to the
next. Handoffarr exists to reconstruct these handoffs and to point at whichever
one dropped the ball — "who passed the bad torrent."

This document defines, for each handoff in the lifecycle (see
[pipeline-model.md](pipeline-model.md)):

- **Survives** — information that reliably crosses the boundary and can be
  recovered later.
- **May be lost** — telemetry that crosses unreliably or only sometimes, so
  diagnoses degrade gracefully when it is absent.
- **Must capture immediately** — point-in-time telemetry that cannot be recovered
  after the moment passes, so the collector must record it on the poll that sees
  it.

The guiding principle: **a handoff narrows information.** Each service forgets
most of what the previous one knew and keeps only what it needs. Handoffarr's job
is to grab the disappearing facts at the boundary before they are gone.

## Handoff 1: Request → Search

Owner of the boundary: Seerr/Jellyseerr/Overseerr hands a title to Radarr, which
launches a search.

- **Survives:** the title (normalized for matching), the request `id`, and the
  request `status`. The title is the only durable join key all the way down the
  chain, because hashes do not exist yet at request time.
- **May be lost:** the exact search query Radarr builds, quality-profile
  intent, and any user note. Handoffarr never sees the search itself (lifecycle
  phase 2 is inferred).
- **Must capture immediately:** `requested_at`. It is the anchor for the
  title-time-window correlation back from a Radarr grab
  (`title_time_window_minutes`). If the request scrolls out of the API window
  before it is polled, the link to the Decision is permanently weaker.

## Handoff 2: Search → Candidate discovery

Owner of the boundary: the indexer returns a set of candidate releases to Radarr.

- **Survives:** nothing directly. Handoffarr cannot see the candidate set.
- **May be lost:** effectively all of it — every rejected candidate, every
  competing release's seed count, the ranking Radarr applied.
- **Must capture immediately:** not applicable; this boundary is opaque in V1.
  The only thing Handoffarr ever learns about candidate discovery is the single
  attribute set that rides along on the chosen release (next handoff).

This opacity is why Handoffarr cannot answer "was a better release available?" —
only "did the release that *was* chosen behave badly?" See the observability gaps
in [telemetry.md](telemetry.md).

## Handoff 3: Candidate discovery → Release decision

Owner of the boundary: Radarr selects one candidate and records a grab in its
history.

- **Survives:** the selected release's `sourceTitle`, the `indexer` name, the
  `downloadId`, and the `torrent_hash` when Radarr exposes one. These are read
  from the Radarr history record and its nested `data` blob
  (`collectors/radarr.py`).
- **May be lost:** the torrent hash. Radarr does not always populate it, and the
  key name varies (`torrentInfoHash` / `torrentHash` / `downloadHash`). When the
  hash is missing, the downstream handoff falls back to weaker join keys.
- **Must capture immediately:** `reported_seeds`. This is the indexer's seed
  claim *at the instant of the grab*, pulled from `seeders` / `Seeders` /
  `seedCount`. It is the headline number for "was this a good release," and it is
  not retrievable later — Radarr history reflects the value seen at grab time, and
  the live swarm will have moved on. Capture it on the poll that sees the grab.

## Handoff 4: Release decision → Handoff (Radarr → qBittorrent)

Owner of the boundary: Radarr passes the release to the download client.

- **Survives:** the `torrent_hash` and/or `downloadId`, which are the strong join
  keys linking the Decision to a RuntimeState. Correlation tries them in priority
  order (`correlation.py`):
  1. torrent hash (confidence 1.0)
  2. download id (confidence 0.8)
  3. normalized title within the time window (confidence 0.5)
- **May be lost:** the hash linkage, when Radarr never exposed a hash or
  qBittorrent reports a different one. The system then degrades to fuzzy title
  matching, which can mis-match or miss entirely. The chosen `match_source` and
  `match_confidence` are recorded so the uncertainty is visible.
- **Must capture immediately:** the torrent hash on **both** sides. qBittorrent
  hashes are normalized to lowercase at collection time so the two sides compare
  cleanly. A hash captured late is no worse than one captured early — but a hash
  *not* captured forces the lossy title path.

## Handoff 5: Handoff → Queueing

Owner of the boundary: qBittorrent accepts the torrent and places it in its
download queue.

- **Survives:** the torrent's presence in the qBittorrent list, its `state`
  (`queuedDL`, etc.), and queue accounting (slot usage, `max_active_downloads`).
- **May be lost:** *why* it is queued rather than active. Queue settings
  (`queueing_enabled`, `dont_count_slow_torrents`) are only visible through the
  live debug endpoint (`queue_report`) and are **not persisted**, so a past
  queueing decision cannot be reconstructed after the fact.
- **Must capture immediately:** the runtime snapshot every poll —
  `state`, `peers`, `seeds`, `dlspeed`. These change continuously; each poll is
  the only durable record of that instant.

## Handoff 6: Queueing → Runtime execution

Owner of the boundary: qBittorrent promotes the torrent to actively downloading.

- **Survives:** live `state`, `num_complete` (seeds), `num_incomplete` (peers),
  `dlspeed`, `progress`, and optionally trackers (fetched per-torrent during
  collection).
- **May be lost:** the moment-to-moment transitions between polls. Handoffarr
  samples at `poll_interval_seconds`; anything that happens and resolves between
  two polls is never seen.
- **Must capture immediately:** all runtime counters, every poll. They are
  ephemeral by nature — peers and speed are meaningless a minute later. This is
  the highest-churn telemetry in the system.

## Handoff 7: Runtime execution → Import

Owner of the boundary: the download completes and Radarr imports it.

- **Survives:** the import event in Radarr history
  (`downloadfolderimported` / `movieFileImported`) and the torrent flipping to a
  seeding/completed state in qBittorrent.
- **May be lost:** the link between the completed torrent and the originating grab
  if the import event carries a different hash than the grab did. Completed,
  seeding torrents legitimately show zero download peers, so they are explicitly
  excluded from swarm-failure heuristics (`states.is_seeding_state`).
- **Must capture immediately:** nothing time-critical; completion is a stable
  fact. The collector simply records the seeding/completed state on the next poll.

## Handoff 8: Import → Outcome

Owner of the boundary: Handoffarr (this is an internal handoff, not a service
boundary).

- **Survives:** the final `diagnosis` stored on the `handoff_traces` row.
- **May be lost:** the *history* of how the item got there. Traces are rebuilt
  from scratch each pass (`db.replace_traces`), so the Outcome reflects only the
  latest snapshot, not the path through earlier interpretations.
- **Must capture immediately:** not applicable — the Outcome is derived, and is
  recomputed deterministically on every correlation pass.

## Summary table

| Handoff | Strong key that survives | Most likely loss | Must grab at the boundary |
|---------|--------------------------|------------------|---------------------------|
| Request → Search | normalized title | search query | `requested_at` |
| Search → Candidates | (none) | the whole candidate set | (opaque in V1) |
| Candidates → Decision | sourceTitle, indexer | torrent hash | `reported_seeds` |
| Decision → Handoff | torrent hash / download id | hash linkage | torrent hash, both sides |
| Handoff → Queueing | torrent presence + state | why it queued | runtime snapshot |
| Queueing → Runtime | live counters | inter-poll transitions | peers / seeds / dlspeed / state |
| Runtime → Import | import event + seeding state | grab↔completion link | (nothing time-critical) |
| Import → Outcome | final diagnosis | the interpretation history | (derived, recomputed) |
