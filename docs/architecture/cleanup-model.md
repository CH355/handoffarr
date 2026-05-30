# Cleanup Model

This is the canonical V2 model for deciding whether downloaded content has been
cleaned up, is intentionally retained, or is still occupying qBittorrent download
storage after a successful import.

The triggering real-world case was:

- Content was successfully imported into the media library.
- The original qBittorrent download copies remained in download storage.
- The retained completed torrents consumed 535 GB across 352 torrents.

V2 makes that state observable without changing Handoffarr's architecture:

```
Collectors -> Persistence -> Interpreters -> Dashboard
```

Handoffarr still reads. It does not delete torrents, remove files, pause seeding,
or mutate Radarr/qBittorrent.

## Canonical entity: CleanupEvent

`CleanupEvent` is the normalized interpretation of whether the download-side
artifact was removed, retained, or left behind after import.

It may be derived from qBittorrent state, Radarr import state, and storage
artifact state. It does not require a dedicated upstream event.

Minimum canonical fields:

| Field | Meaning |
|-------|---------|
| `cleanup_id` | Stable derived id, usually based on torrent hash plus path. |
| `torrent_hash` | qBittorrent torrent hash. |
| `download_id` | Radarr download id when known. |
| `movie_id` | Radarr movie id when known. |
| `download_path` | Path to the download-side file or folder. |
| `library_path` | Path to the imported library file. |
| `cleanup_status` | `cleaned`, `pending`, `failed`, or `retained`. |
| `retention_reason` | Why retained storage appears intentional. |
| `evidence` | Correlation keys and observations supporting the status. |
| `observed_at` | Poll time when the status was derived. |

## Cleanup diagnosis categories

### Cleanup Success

The imported media is present in the library and the download-side artifact is no
longer present or no longer consuming meaningful storage.

Evidence may include:

- The torrent is absent from qBittorrent after successful import.
- The download path no longer exists.
- The remaining artifact is zero-sized or below an ignored threshold.

### Cleanup Pending

The content was imported, but the download-side artifact still exists and no
clear retention intent or cleanup failure has been identified.

This is the important category for "my disk is filling up quietly." It is not
yet an accusation; it means the lifecycle has not reached a clean terminal state.

### Cleanup Failure

The content was imported, the download-side artifact remains, and evidence shows
cleanup should have happened or cleanup cannot happen.

Evidence may include:

- Radarr reports failed remove/import cleanup behavior.
- The torrent is in a missing files, error, permission, or path mapping state.
- The artifact age exceeds the cleanup grace period without seeding or policy
  evidence explaining the retention.

### Retention Intentional

The content was imported and remains in download storage because current policy
or live qBittorrent state suggests it is meant to remain there.

Evidence may include:

- Torrent is actively seeding.
- Ratio or seeding time has not met the configured target.
- Category/tag/save path is configured as long-term seeding.
- qBittorrent or Radarr settings indicate remove-on-import is not expected.

Intentional retention is not a storage defect, but it still contributes to disk
usage and should appear in storage totals separately from reclaimable waste.

## Correlation logic

Cleanup correlation is downstream of import correlation. The interpreter should
only claim cleanup state after it knows whether the item was imported.

Canonical relationship:

```
Torrent
  -> Imported Media
  -> Library File
  -> Download File
  -> Cleanup State
```

Rules:

1. A torrent is linked to imported media by `torrent_hash`, then `download_id`,
   then normalized release title within the import time window.
2. Imported media is linked to a library file by Radarr `movie_id` and movie file
   metadata.
3. A download file is linked to a torrent by qBittorrent content path, save path,
   torrent name, and hash.
4. Cleanup state compares the library file and download file after import.
5. The same bytes should not be counted twice unless both a library artifact and
   a download artifact are confirmed to exist.

## Determining cleanup outcomes

### Imported but retained

Handoffarr determines this when:

- Import is successful.
- A library file is present.
- A correlated download file or torrent save path still exists.
- The retained artifact has non-trivial size.

The next question is whether retention is intentional or reclaimable.

### Imported and cleaned

Handoffarr determines this when:

- Import is successful.
- A library file is present.
- The correlated torrent/download artifact is gone, or the remaining artifact is
  below the ignored-size threshold.

This is the desired terminal state when seeding retention is not required.

### Active seeding retention

Handoffarr determines this when:

- Import is successful.
- The torrent remains in qBittorrent.
- qBittorrent reports a seeding/uploading/completed state.
- Retention policy evidence says continued presence is expected.

This should be labeled Retention Intentional rather than Cleanup Failure.

### Reclaimable storage

Handoffarr determines this when:

- Import is successful and the library file exists.
- The download-side artifact still consumes storage.
- The torrent is not actively required for seeding, or it has met configured
  ratio/time goals, or no retention policy explains the artifact.
- The correlation confidence is high enough to avoid suggesting unsafe removal.

Reclaimable storage means "safe candidate for operator review," not "Handoffarr
will delete it." Handoffarr remains read-only.

## Dashboard concepts

### Cleanup Health

Fleet-level summary of cleanup outcomes:

- Count and size of Cleanup Success.
- Count and size of Cleanup Pending.
- Count and size of Cleanup Failure.
- Count and size of Retention Intentional.

### Cleanup Candidates

A review list of imported items whose download artifacts appear reclaimable.

Each row should show:

- Title / release name.
- Download size.
- Library path evidence.
- Download path evidence.
- Torrent state.
- Retention reason, or why no retention reason was found.
- Correlation confidence.

The dashboard should make uncertainty visible. Weakly correlated candidates
belong below strongly correlated candidates and should avoid strong language such
as "safe to remove."

## Layer placement

Collectors gather import, torrent, path, size, and policy observations.
Persistence stores snapshots in local SQLite. Interpreters derive cleanup status
and reclaimability. The Dashboard presents Cleanup Health and Cleanup Candidates.

No microservice, Redis, Kafka, Celery, event bus, or external database is part of
this model.
