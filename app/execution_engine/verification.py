"""Execution Engine verification strategies.

Each action can have a verifier that checks whether the action
actually achieved its intended effect.
"""
from __future__ import annotations

from typing import Any

from .. import db


class ActionVerifier:
    """Default verifier that dispatches to action-type-specific checks."""

    def verify(self, action_type: str, params: dict[str, Any], output: dict[str, Any]) -> tuple[bool, str | None]:
        method_name = f"verify_{action_type.lower()}"
        method = getattr(self, method_name, self._verify_default)
        return method(params, output)

    def _verify_default(self, params: dict[str, Any], output: dict[str, Any]) -> tuple[bool, str | None]:
        if output.get("error"):
            return False, output["error"]
        return True, None

    def verify_removetorrent(self, params: dict[str, Any], output: dict[str, Any]) -> tuple[bool, str | None]:
        torrent_hash = output.get("removed")
        if not torrent_hash:
            return False, "No removed torrent hash in output"
        # Check local DB snapshot
        current = {
            str(t.get("hash") or "").lower() for t in db.all_qbittorrent_torrents()
        }
        if torrent_hash.lower() in current:
            return False, "Torrent still present in local snapshot"
        return True, None

    def verify_verifytorrentremoved(self, params: dict[str, Any], output: dict[str, Any]) -> tuple[bool, str | None]:
        if not output.get("verified"):
            return False, output.get("error") or "Torrent removal not verified"
        return True, None

    def verify_wait(self, params: dict[str, Any], output: dict[str, Any]) -> tuple[bool, str | None]:
        waited = output.get("waited_seconds")
        expected = int(params.get("seconds", 30))
        if waited is None or waited < expected:
            return False, f"Waited {waited}s, expected {expected}s"
        return True, None

    def verify_verifypipelinestate(self, params: dict[str, Any], output: dict[str, Any]) -> tuple[bool, str | None]:
        if not output.get("verified"):
            return False, output.get("error") or "Pipeline state not verified"
        return True, None

    def verify_refreshalternatives(self, params: dict[str, Any], output: dict[str, Any]) -> tuple[bool, str | None]:
        evaluation = output.get("evaluation")
        if not evaluation:
            return False, "No evaluation in output"
        if evaluation.get("error"):
            return False, evaluation["error"]
        return True, None
