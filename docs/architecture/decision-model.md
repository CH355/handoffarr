# Decision Visibility Model

Phase 8 of Handoffarr. Builds on the existing pipeline:

```
Collectors -> Persistence -> Interpreters -> Dashboard
```

No microservice, Redis, Kafka, Celery, worker, message bus, websocket, or
AI/LLM call is part of this model. Everything reads from local SQLite.

## Purpose

Handoffarr already explains *what* happened (runtime, import, library,
cleanup, responsibility, recommendations, timeline). It does not yet explain
*why a specific torrent was selected*, *which alternatives existed*, *whether
the selection was reasonable*, or *whether the indexer misrepresented
availability*.

The decision model is the read-only interpretation that connects a selected
release back to the indexer that supplied it and to the runtime evidence that
either justifies or contradicts the indexer's availability claims.

## Business Questions

| Question | Answer source |
|----------|---------------|
| Why was this torrent selected? | `selected_release` + `decision_reason` |
| Which indexer supplied it? | `source_indexer` |
| What alternatives existed? | `candidate_count` + `evidence.candidates` |
| Was the selection reasonable? | `decision_quality` + `confidence` |
| Did availability claims match reality? | reported seeds vs observed peers in `evidence` |
| Who passed the bad torrent? | `source_application` + `source_indexer` |

## Canonical Entity: DecisionAssessment

| Field | Meaning |
|-------|---------|
| `decision_id` | Stable id derived from media id, torrent hash, history id. |
| `media_id` | Correlated media identifier (import media id, normalized title, torrent hash, or history id, in that order). |
| `media_title` | Human-readable title for dashboard display. |
| `selected_release` | Release name selected by the media application (Radarr/Sonarr/Lidarr). |
| `source_application` | Media application that grabbed the release. |
| `source_indexer` | Indexer that reported the release. |
| `candidate_count` | Number of grabs Handoffarr observed for the same normalized title. |
| `decision_reason` | One-sentence explanation tied to the evidence. |
| `decision_quality` | One of Good / Acceptable / Questionable / Bad / Unknown. |
| `confidence` | Certain / High / Medium / Low. Matches responsibility model wording. |
| `evidence` | Structured observations: reported seeds, observed peers, runtime state, import status, candidate list. |
| `observed_at` | Poll time when the assessment was derived. |

## Decision Quality Vocabulary

Only five values are supported. Each requires evidence.

### Good Selection

Evidence:

- Download completed.
- Import succeeded.
- Runtime healthy or seeding.

### Acceptable Selection

Evidence:

- Runtime healthy.
- Import outcome pending or not yet observed.

The release itself looks fine, but Handoffarr cannot yet confirm full success.

### Questionable Selection

Evidence:

- Repeated stalls.
- Low peer count.
- Metadata delays.
- Runtime degraded relative to reported availability.

### Bad Selection

Evidence:

- Reported seeds high (>= configured `healthy_reported_seeds`).
- Observed peers near zero.
- Runtime failure (stalled/error or active download with zero progress).
- OR reported seeds low, peers zero, and runtime stalled (low-availability
  release selected).

### Unknown

Evidence:

- Insufficient runtime telemetry, import status, and reported-seeds data to
  judge the selection.

## Layer Placement

### Collectors

- `app/collectors/decision.py`. Read-only.
- Projects already-persisted `raw_events` (Seerr requests, Radarr/Sonarr/Lidarr
  history, qBittorrent torrents, import events) into one DecisionObservation
  per selected release.
- Captures release name, indexer, reported seeds, download id, torrent hash,
  candidate evidence (every observed grab for the same normalized title).
- Does not call indexers. Handoffarr cannot see the indexer's full rejected
  candidate set, so "candidate count" is the observable history of alternative
  selections for the same media title, not the indexer's pick list.

### Persistence

- New table: `decision_assessments`.
- Replaced as derived state on each poll (delete + insert), matching the
  pattern used by traces, responsibility, recommendations, and timeline.

### Interpreter

- `app/decision.py`.
- Applies the decision-quality rules above over the DecisionObservation rows.
- Produces `DecisionAssessment` records with evidence, reason, and confidence
  preserved.

### Dashboard / API

- `GET /api/decisions` returns a summary, the full assessment list, plus
  `bad_decisions` and `questionable_decisions` slices.
- `GET /api/decisions/{media_id}` returns the latest assessment for a media id
  with full evidence and history.
- Dashboard adds a **Decision Center** table (Selected Release, Indexer,
  Decision Quality, Candidate Count, Confidence, Reason) and a **Bad
  Decisions** table (media title, selected release, indexer, decision quality,
  evidence). Both render from `/api/decisions`.

## Success Criterion

Given a selected torrent with:

- Reported seeds: 120
- Observed peers: 0
- Repeated runtime failure

Handoffarr displays:

```
Decision Quality:   Bad Selection
Responsible:        Indexer
Reason:             Availability misrepresentation observed.
Evidence:
  Reported seeds 120.
  Observed peers 0.
  Runtime failure occurred.
```

This phase completes the original product promise: **see who passed the bad
torrent.**
