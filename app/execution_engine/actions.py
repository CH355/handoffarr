"""Execution Engine action abstraction and concrete implementations.

Actions are the units of work in an execution pipeline.
Each action is observable, verifiable, and retryable.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, Protocol

from .. import db
from ..config import Config
from .models import ExecutionActionResult


class ActionVerifier(Protocol):
    """Protocol for action verification strategies."""

    def verify(self, action_type: str, params: dict[str, Any], output: dict[str, Any]) -> tuple[bool, str | None]:
        ...


class ExecutionAction(ABC):
    """Base class for all execution actions.

    Subclasses must implement execute() and may override verify().
    """

    action_type: str = ""

    def __init__(self, config: Config, verifier: ActionVerifier | None = None):
        self.config = config
        self.verifier = verifier

    @abstractmethod
    def execute(self, torrent_hash: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute the action and return output dict.

        Must not raise — errors are returned in the output dict.
        """
        ...

    def run(
        self,
        torrent_hash: str,
        step_number: int,
        params: dict[str, Any],
    ) -> ExecutionActionResult:
        """Run execute + verification and return a structured result."""
        started = time.perf_counter()
        try:
            output = self.execute(torrent_hash, params)
            error = output.get("error")
            success = error is None
        except Exception as exc:  # noqa: BLE001
            output = {}
            error = f"{type(exc).__name__}: {exc}"
            success = False

        duration_ms = round((time.perf_counter() - started) * 1000, 2)

        verification_passed = False
        verification_msg: str | None = None
        if self.verifier and success:
            verification_passed, verification_msg = self.verifier.verify(
                self.action_type, params, output
            )
            success = verification_passed
            if not verification_passed:
                error = error or f"Verification failed: {verification_msg}"

        return ExecutionActionResult(
            action_type=self.action_type,
            step_number=step_number,
            success=success,
            duration_ms=duration_ms,
            output=output,
            error=error,
            verification_passed=verification_passed,
        )


class RemoveTorrentAction(ExecutionAction):
    """Remove a torrent from qBittorrent."""

    action_type = "RemoveTorrent"

    def execute(self, torrent_hash: str, params: dict[str, Any]) -> dict[str, Any]:
        from ..collectors import qbittorrent

        delete_files = params.get("delete_files", False)
        result = qbittorrent.delete_torrents(
            self.config,
            [torrent_hash],
            delete_files=delete_files,
        )
        if not result.get("ok"):
            return {"error": result.get("error", "qBittorrent removal failed")}
        db.remove_qbittorrent_torrents([torrent_hash])
        return {"removed": torrent_hash, "delete_files": delete_files}


class RefreshAlternativesAction(ExecutionAction):
    """Refresh alternative release evaluation for a torrent."""

    action_type = "RefreshAlternatives"

    def execute(self, torrent_hash: str, params: dict[str, Any]) -> dict[str, Any]:
        from .. import recovery as recovery_module

        torrent = next(
            (
                t
                for t in db.all_qbittorrent_torrents()
                if str(t.get("hash") or "").lower() == torrent_hash
            ),
            None,
        )
        if torrent is None:
            return {"error": "Torrent not found in current snapshot"}
        try:
            evaluation = recovery_module.evaluate_torrent(
                self.config,
                torrent,
                db.events_for_torrent(torrent_hash),
                force=True,
            )
        except recovery_module.RecoveryProviderError as exc:
            return {"error": str(exc)}
        return {"evaluation": evaluation}


class VerifyTorrentRemovedAction(ExecutionAction):
    """Verify that a torrent no longer exists in qBittorrent."""

    action_type = "VerifyTorrentRemoved"

    def execute(self, torrent_hash: str, params: dict[str, Any]) -> dict[str, Any]:
        from ..collectors import qbittorrent

        report = qbittorrent.torrent_report(self.config, torrent_hash)
        if report.get("ok") and "no torrent found" not in (report.get("error") or "").lower():
            return {"error": "Torrent still exists in qBittorrent"}
        return {"verified": True, "torrent_hash": torrent_hash}


class WaitAction(ExecutionAction):
    """Pause execution for a configured duration."""

    action_type = "Wait"

    def execute(self, torrent_hash: str, params: dict[str, Any]) -> dict[str, Any]:
        seconds = int(params.get("seconds", 30))
        time.sleep(seconds)
        return {"waited_seconds": seconds}


class VerifyPipelineStateAction(ExecutionAction):
    """Verify that the overall pipeline is healthy after execution."""

    action_type = "VerifyPipelineState"

    def execute(self, torrent_hash: str, params: dict[str, Any]) -> dict[str, Any]:
        from ..collectors import qbittorrent

        status = qbittorrent.states_report(self.config)
        if not status.get("ok"):
            return {"error": "Could not retrieve pipeline state"}
        return {"pipeline_state": status, "verified": True}


class ActionRegistry:
    """Registry of all available execution actions.

    Future actions (GrabAlternativeAction, ImportVerificationAction,
    NotifyUserAction, RollbackAction) can be registered here without
    redesigning the pipeline.
    """

    _actions: dict[str, type[ExecutionAction]] = {}

    @classmethod
    def register(cls, action_type: str, action_class: type[ExecutionAction]) -> None:
        cls._actions[action_type] = action_class

    @classmethod
    def get(cls, action_type: str) -> type[ExecutionAction] | None:
        return cls._actions.get(action_type)

    @classmethod
    def create(
        cls,
        action_type: str,
        config: Config,
        verifier: ActionVerifier | None = None,
    ) -> ExecutionAction | None:
        action_class = cls.get(action_type)
        if action_class is None:
            return None
        return action_class(config, verifier)

    @classmethod
    def list_actions(cls) -> list[str]:
        return sorted(cls._actions.keys())


# Register built-in actions
ActionRegistry.register(RemoveTorrentAction.action_type, RemoveTorrentAction)
ActionRegistry.register(RefreshAlternativesAction.action_type, RefreshAlternativesAction)
ActionRegistry.register(VerifyTorrentRemovedAction.action_type, VerifyTorrentRemovedAction)
ActionRegistry.register(WaitAction.action_type, WaitAction)
ActionRegistry.register(VerifyPipelineStateAction.action_type, VerifyPipelineStateAction)
