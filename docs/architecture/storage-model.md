# Storage Model

This is the canonical V2 model for answering two operational questions:

- "Why is my disk full?"
- "What content is safe to remove?"

Storage observability connects the existing request-to-runtime trace with the new
Import, Library, and Cleanup stages. It is not a replacement for Radarr or
qBittorrent policy. Handoffarr remains a read-only diagnosis layer.

## Canonical entity: StorageArtifact

`StorageArtifact` is any observed file, folder, or torrent-owned storage unit
that consumes disk space and can be related to a media lifecycle.

Minimum canonical fields:

| Field | Meaning |
|-------|---------|
| `artifact_id` | Stable derived id, usually hash plus path. |
| `artifact_type` | `library_file`, `download_file`, `download_folder`, or `torrent_payload`. |
| `path` | Filesystem path when available. |
| `size_bytes` | Observed or reported size. |
| `source` | `radarr`, `qbittorrent`, or local filesystem collector if added later. |
| `torrent_hash` | qBittorrent hash when known. |
| `download_id` | Radarr download id when known. |
| `movie_id` | Radarr movie id when known. |
| `title` | Human-readable media or release title. |
| `lifecycle_stage` | `Library`, `Cleanup`, or `Storage`. |
| `correlation_confidence` | Strength of the relationship to the media lifecycle. |
| `observed_at` | Poll time. |

StorageArtifact is a normalized observation, not a deletion instruction.

## Storage diagnosis categories

### Storage Healthy

Storage use matches expected lifecycle state.

Examples:

- Library files exist for imported media.
- Download artifacts are absent after cleanup.
- Retained download artifacts have clear seeding or retention intent.
- Free space is above warning thresholds.

### Storage Risk

Storage use is plausible but deserves attention.

Examples:

- Imported content remains in download storage without enough age to call it a
  failure.
- Retained seeding content is large and approaching disk thresholds.
- Correlation is weak, so Handoffarr can explain likely waste but cannot yet make
  a strong cleanup candidate claim.

### Storage Critical

Storage pressure is actively harmful or likely to block downloads/imports.

Examples:

- Free disk space is below the critical threshold.
- Reclaimable imported downloads exceed a configured size threshold.
- qBittorrent or Radarr reports disk, path, or permission errors.
- Completed retained downloads are large enough to explain the full disk
  condition.

## Correlation model

Storage correlation is a graph over existing lifecycle entities:

```
Request
  -> Decision
  -> Torrent
  -> ImportEvent
  -> Library File
  -> Download File
  -> CleanupEvent
  -> StorageArtifact
```

Storage interpreters should preserve both the answer and the evidence:

| Question | Required evidence |
|----------|-------------------|
| Did this get imported? | ImportEvent success or library file correlation. |
| Is there a library copy? | Radarr movie file path or filesystem evidence. |
| Is there a download copy? | qBittorrent content path, save path, or filesystem evidence. |
| Is retention intentional? | Seeding state, ratio/time goal, category/tag, or policy evidence. |
| Is space reclaimable? | Successful import, library presence, retained download artifact, no active retention need. |

## Determining storage lifecycle states

### Imported but retained

State:

- Import Success.
- Library file present.
- Download artifact present.
- Cleanup status is Pending, Failure, or Retention Intentional.

Storage interpretation:

- Retention Intentional when seeding/policy evidence exists.
- Storage Risk when retention is unexplained but recent or low confidence.
- Storage Critical when retention is unexplained, old, large, and disk pressure
  is present.

### Imported and cleaned

State:

- Import Success.
- Library file present.
- Download artifact absent or below ignored-size threshold.
- Cleanup Success.

Storage interpretation:

- Storage Healthy.

### Import failed

State:

- Import Failed, or complete download with explicit import blocker.
- Library file absent or unconfirmed.
- Download artifact present.

Storage interpretation:

- Storage Risk if disk pressure is low.
- Storage Critical if the failed import is large or disk pressure is blocking
  further downloads/imports.

This content is not automatically reclaimable because it may be the only copy.

### Active seeding retention

State:

- Import Success.
- Library file present.
- Download artifact present.
- Torrent is seeding and retention goals are unmet or policy says retain.

Storage interpretation:

- Retention Intentional.
- Storage Healthy if free space is adequate.
- Storage Risk if seeding retention is consuming enough space to approach disk
  thresholds.

### Reclaimable storage

State:

- Import Success.
- Library file present.
- Download artifact present.
- No active retention requirement.
- Correlation confidence is strong.

Storage interpretation:

- Cleanup Candidate.
- Counts toward Reclaimable Space.
- May contribute to Storage Risk or Storage Critical depending on size and free
  space.

## Dashboard concepts

### Storage Health

Top-level view explaining whether disk use is normal, risky, or critical.

Inputs:

- Free space thresholds.
- Total library bytes observed.
- Total download bytes observed.
- Retained intentional bytes.
- Reclaimable bytes.
- Failed/pending import bytes.

### Import Health

Summary of import lifecycle:

- Import Success count and size.
- Import Pending count and age.
- Import Failed count with upstream reasons.

This tells the operator whether disk pressure is caused by downloads that never
entered the library.

### Cleanup Health

Summary of post-import lifecycle:

- Cleanup Success.
- Cleanup Pending.
- Cleanup Failure.
- Retention Intentional.

This tells the operator whether disk pressure is caused by imported downloads
that were not removed.

### Reclaimable Space

Total bytes from strong-confidence artifacts where Handoffarr believes the
library already has the content and no active retention reason remains.

Reclaimable Space should be split from Retention Intentional so operators can
distinguish waste from policy-driven seeding.

### Cleanup Candidates

The itemized list behind Reclaimable Space.

Rows should include title, size, age, torrent state, library path, download path,
cleanup status, storage diagnosis, and correlation confidence.

## Explaining "Why is my disk full?"

The dashboard should answer with a ranked breakdown:

1. Critical free-space condition, if present.
2. Reclaimable imported downloads.
3. Intentional seeding retention.
4. Import failures and pending imports.
5. Uncorrelated download artifacts.
6. Healthy library growth.

This keeps the explanation operational: first show the pressure, then show the
bytes that explain it, then show what is safe to review.

## Explaining "What content is safe to remove?"

Handoffarr should only mark content as a cleanup candidate when all are true:

- The media was imported successfully.
- A library file is present or strongly correlated.
- The download artifact is still present and has size.
- The torrent is not required for active seeding retention.
- The match confidence is high.

If any condition is weak or unknown, the dashboard should downgrade language to
"needs review" rather than "cleanup candidate."

## Layer placement

Collectors gather read-only facts from Radarr, qBittorrent, and optionally the
local filesystem. Persistence stores those facts in the existing local SQLite
model. Interpreters derive storage health, cleanup candidates, and reclaimable
space. The Dashboard renders the explanation and evidence.

No microservice, Redis, Kafka, Celery, event bus, or external database is part of
this model.
