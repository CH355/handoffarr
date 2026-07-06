from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import uuid4


class QueueRepository(Protocol):
    def insert_job(self, job: dict[str, Any]) -> None: ...
    def update_job(self, job_id: str, **values: Any) -> None: ...
    def list_jobs(self, limit: int) -> list[dict[str, Any]]: ...


class RecoveryQueue:
    STATES = {"Queued", "Running", "Completed", "Failed", "Cancelled"}

    def __init__(self, repository: QueueRepository):
        self.repository = repository

    def enqueue(self, torrent_hash: str) -> dict[str, Any]:
        job = {"job_id": f"recovery-job-{uuid4()}", "torrent_hash": torrent_hash.lower(),
               "status": "Queued", "created_at": _now()}
        self.repository.insert_job(job)
        return job

    def transition(self, job_id: str, status: str, error: str | None = None) -> None:
        if status not in self.STATES:
            raise ValueError(status)
        values: dict[str, Any] = {"status": status}
        if status == "Running":
            values["started_at"] = _now()
        if status in {"Completed", "Failed", "Cancelled"}:
            values["completed_at"] = _now()
        if error:
            values["error"] = error
        self.repository.update_job(job_id, **values)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
