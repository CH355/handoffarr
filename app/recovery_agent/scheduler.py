from datetime import datetime, timedelta, timezone


class RecoveryScheduler:
    ALLOWED_INTERVALS = {5, 10, 15, 30, 60}

    def due(self, settings: dict, now: datetime | None = None) -> bool:
        if not settings.get("enabled"):
            return False
        if not settings.get("next_evaluation_at"):
            return True
        current = now or datetime.now(timezone.utc)
        try:
            return current >= datetime.fromisoformat(
                str(settings["next_evaluation_at"]).replace("Z", "+00:00")
            )
        except ValueError:
            return True

    def next(self, minutes: int, now: datetime | None = None) -> str:
        minutes = minutes if minutes in self.ALLOWED_INTERVALS else 15
        return ((now or datetime.now(timezone.utc)) + timedelta(minutes=minutes)).isoformat()
