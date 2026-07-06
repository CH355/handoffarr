from typing import Any
from .. import db


class SQLiteRecoveryRepository:
    insert_job = staticmethod(db.insert_recovery_job)
    update_job = staticmethod(db.update_recovery_job)
    insert_history = staticmethod(db.insert_recovery_history)
    insert_plan = staticmethod(db.insert_recovery_plan)

    def list_jobs(self, limit: int) -> list[dict[str, Any]]:
        return db.recovery_jobs(limit)
