# Import Model

This is the canonical V2 model for observing what happens after qBittorrent has
downloaded content and Radarr attempts to move it into the media library.
Handoffarr remains read-only and lightweight: Collectors gather facts,
Persistence stores snapshots, Interpreters correlate those facts, and the
Dashboard renders the resulting health.

V2 extends the observed lifecycle:

```
Request -> Decision -> Handoff -> Queue -> Runtime -> Import -> Library -> Cleanup -> Storage -> Outcome
```

The new import-facing stages are:

| Stage | Owner | Meaning |
|-------|-------|---------|
| Import | Radarr | A completed download is accepted, rejected, or still waiting to be imported. |
| Library | Radarr / filesystem | The imported media file exists at the managed library path. |
| Cleanup | Radarr / qBittorrent policy | The download copy is removed, retained intentionally, or left behind. |
| Storage | Host filesystem | Library and download artifacts consume disk space. |

Import and Library are distinct. Import is the event that says Radarr processed a
download. Library is the durable evidence that the media is present where Radarr
expects it to live.

## Canonical entity: ImportEvent

`ImportEvent` is the normalized observation that Radarr attempted or completed an
import for a downloaded item.

It is conceptual until implemented; it does not require a new service or a new
store. It can be represented as normalized rows inside the existing SQLite-backed
event model.

Minimum canonical fields:

| Field | Meaning |
|-------|---------|
| `import_id` | Stable Radarr history or event id when available. |
| `movie_id` | Radarr movie id. |
| `movie_title` | Human-readable title. |
| `download_id` | Download client id from Radarr history. |
| `torrent_hash` | Torrent hash when Radarr exposes it. |
| `source_title` | Release name Radarr imported from. |
| `imported_at` | Time Radarr reported the import. |
| `import_status` | `success`, `failed`, or `pending`. |
| `library_path` | Destination file path when known. |
| `download_path` | Source download folder or file path when known. |
| `reason` | Radarr-provided failure or pending reason when available. |
| `raw` | Original payload for debugging mismatches. |

## Import diagnosis categories

### Import Success

Radarr reports a successful import and Handoffarr can correlate it to the
torrent or decision.

Evidence may include:

- Radarr history event such as `downloadFolderImported` or `movieFileImported`.
- A movie file record pointing at a library path.
- Matching `download_id`, `torrent_hash`, or normalized release title.

### Import Failed

Radarr attempted import and reported a failure, rejection, or blocked state.

Evidence may include:

- Radarr import failure event.
- Radarr queue item with tracked download state and an import error.
- Missing or invalid destination, quality rejection, unpacking error, permission
  error, or download client path mapping failure.

### Import Pending

The download appears complete but no successful import event or library file can
yet be correlated.

Evidence may include:

- qBittorrent progress is complete or state is seeding/uploading.
- Radarr decision exists.
- No matching ImportEvent has appeared inside the import lookback window.
- Radarr queue still shows the item as waiting, checking, or unable to import.

Pending is not automatically failure. It becomes risky only after a threshold or
when Radarr reports a specific blocker.

## Correlation inputs

Import correlation joins five facts:

| Fact | Source | Strong keys | Weak keys |
|------|--------|-------------|-----------|
| Torrent | qBittorrent | `hash` | name, save path |
| Imported Media | Radarr history | `download_id`, `torrent_hash`, `movie_id` | source title |
| Library File | Radarr movie file / filesystem view | `movie_id`, path | normalized title, size |
| Download File | qBittorrent content / save path | torrent hash, path | normalized release folder |
| Cleanup State | Cleanup interpreter | artifact path, torrent hash | size and title |

Correlation priority:

1. `torrent_hash` match between Radarr and qBittorrent.
2. `download_id` match between Radarr history and Radarr tracked download state.
3. `movie_id` plus successful import event.
4. Exact normalized `source_title` / torrent name match inside the time window.
5. Path relationship between known download path and known library path.

Weak matches must carry confidence and reasons. They can explain likely state,
but dashboard actions such as "safe to remove" should prefer strong evidence.

## Determining import state

### Imported and present in library

Handoffarr determines this when:

- An ImportEvent is `success`.
- A correlated Radarr movie file exists.
- The library path is known or can be inferred from Radarr movie file metadata.

This answers: "Did Radarr get the content into the library?"

### Import failed

Handoffarr determines this when:

- Radarr exposes an explicit failure event or tracked download import error.
- The download is complete, import is overdue, and Radarr reports a blocker.

The diagnosis should preserve the upstream reason whenever possible. Handoffarr
does not invent a more specific reason than the APIs provide.

### Import pending

Handoffarr determines this when:

- The torrent is complete or seeding.
- No correlated successful import exists.
- No explicit import failure exists.

Pending becomes a dashboard concern when it exceeds a configurable age threshold,
because complete-but-unimported downloads are likely consuming storage without
serving the library.

## Layer placement

Collectors may add read-only Radarr observations for history, queue, and movie
files. Persistence stores the normalized observations in SQLite. Interpreters
derive Import Success, Import Failed, and Import Pending. The Dashboard only
renders those derived labels and drill-down evidence.

No microservice, Redis, Kafka, Celery, event bus, or external database is part of
this model.
