"""Execution Engine locking.

Only one execution may manipulate a torrent at a time.
"""
from __future__ import annotations

import threading
import time
from typing import Any

from .. import db

_lock = threading.Lock()
_active_locks: dict[str, dict[str, Any]] = {}


def acquire_torrent_lock(torrent_hash: str, execution_id: str, timeout_seconds: float = 30.0) -> bool:
    """Try to acquire an exclusive lock on a torrent.

    Returns True if the lock was acquired, False if another execution
    already holds it.
    """
    key = str(torrent_hash or "").strip().lower()
    if not key:
        return False
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        with _lock:
            holder = _active_locks.get(key)
            if holder is None or holder["execution_id"] == execution_id:
                _active_locks[key] = {
                    "execution_id": execution_id,
                    "acquired_at": time.monotonic(),
                }
                return True
        time.sleep(0.1)
    return False


def release_torrent_lock(torrent_hash: str, execution_id: str) -> bool:
    """Release the lock held by execution_id on torrent_hash.

    Returns True if the lock was released, False if not held.
    """
    key = str(torrent_hash or "").strip().lower()
    with _lock:
        holder = _active_locks.get(key)
        if holder and holder["execution_id"] == execution_id:
            del _active_locks[key]
            return True
    return False


def is_locked(torrent_hash: str) -> bool:
    key = str(torrent_hash or "").strip().lower()
    with _lock:
        return key in _active_locks


def lock_holder(torrent_hash: str) -> str | None:
    key = str(torrent_hash or "").strip().lower()
    with _lock:
        holder = _active_locks.get(key)
        return holder["execution_id"] if holder else None


def force_release_all() -> None:
    """Release all locks. Used for testing and emergency recovery."""
    with _lock:
        _active_locks.clear()
