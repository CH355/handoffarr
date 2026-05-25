"""qBittorrent torrent-state classification.

Centralizes the mapping from raw qBittorrent state strings to the coarse
categories used by the diagnosis engine and the debug endpoints. qBittorrent
versions differ in naming (notably v5 uses ``stoppedDL``/``stoppedUP`` where
older builds used ``pausedDL``/``pausedUP``), so all lookups are lowercased and
unknown states fall back to ``other`` rather than crashing.
"""

from __future__ import annotations

# Coarse categories.
DOWNLOADING = "downloading"
QUEUED = "queued"
STALLED = "stalled"
COMPLETED = "completed"
UPLOADING = "uploading"
PAUSED = "paused"
ERROR = "error"
OTHER = "other"

CATEGORIES = (
    DOWNLOADING,
    QUEUED,
    STALLED,
    COMPLETED,
    UPLOADING,
    PAUSED,
    ERROR,
    OTHER,
)

# Raw qBittorrent state (lowercased) -> coarse category.
STATE_CLASSIFICATION: dict[str, str] = {
    # Actively downloading.
    "downloading": DOWNLOADING,
    "forceddl": DOWNLOADING,
    "metadl": DOWNLOADING,
    "allocating": DOWNLOADING,
    "checkingdl": DOWNLOADING,
    "checkingresumedata": DOWNLOADING,
    "moving": DOWNLOADING,
    # Waiting in the download queue.
    "queueddl": QUEUED,
    "queuedup": QUEUED,
    # Stalled mid-download (no transfer, still trying).
    "stalleddl": STALLED,
    # Finished downloading, seeding actively.
    "uploading": UPLOADING,
    "forcedup": UPLOADING,
    # Finished downloading, idle / not actively transferring.
    "stalledup": COMPLETED,
    "checkingup": COMPLETED,
    "pausedup": COMPLETED,
    "stoppedup": COMPLETED,
    # Download paused / stopped before completion.
    "pauseddl": PAUSED,
    "stoppeddl": PAUSED,
    # Error states.
    "error": ERROR,
    "missingfiles": ERROR,
    # Explicitly unknown.
    "unknown": OTHER,
}

# States where the torrent has finished downloading and is seeding or idle.
# Swarm-failure diagnosis never applies to these.
SEEDING_STATES = {
    "uploading",
    "forcedup",
    "stalledup",
    "checkingup",
    "pausedup",
    "stoppedup",
    "queuedup",
}

# States where the torrent is actively trying to download. Dead-swarm /
# zero-peer heuristics only make sense for these.
ACTIVE_DOWNLOAD_STATES = {
    "downloading",
    "forceddl",
    "metadl",
    "allocating",
    "stalleddl",
    "queueddl",
}


def classify(state: str | None) -> str:
    """Return the coarse category for a raw qBittorrent state string."""
    return STATE_CLASSIFICATION.get((state or "").lower(), OTHER)


def is_seeding_state(state: str | None) -> bool:
    """True for completed/seeding torrents (UP-suffix family)."""
    return (state or "").lower() in SEEDING_STATES


def is_active_download_state(state: str | None) -> bool:
    """True for torrents actively attempting to download."""
    return (state or "").lower() in ACTIVE_DOWNLOAD_STATES
