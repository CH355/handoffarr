"""On-demand, read-only release evaluation through Arr providers."""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

import httpx

from .config import Config


DEFAULT_WEIGHTS = {
    "availability": 0.35,
    "seeders": 0.25,
    "quality": 0.20,
    "age": 0.10,
    "indexer_priority": 0.05,
    "custom_format": 0.05,
}


class RecoveryProviderError(RuntimeError):
    """A provider could not resolve or retrieve release candidates."""


@dataclass(frozen=True)
class RecoveryContext:
    torrent_hash: str
    current_release: str
    provider: str
    media_id: int
    media_title: str | None = None


@dataclass
class ReplacementCandidate:
    release_name: str
    quality: str | None
    indexer: str | None
    seeders: int
    peers: int
    age_days: float | None
    size: int
    protocol: str | None
    custom_format_score: int
    rejected: bool
    rejection_reason: str | None
    score: float = 0.0
    recommended: bool = False
    availability: float | None = None
    indexer_priority: int | None = None
    quality_profile_match: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "release_name": self.release_name,
            "quality": self.quality,
            "indexer": self.indexer,
            "seeders": self.seeders,
            "peers": self.peers,
            "age_days": self.age_days,
            "size": self.size,
            "protocol": self.protocol,
            "custom_format_score": self.custom_format_score,
            "rejected": self.rejected,
            "rejection_reason": self.rejection_reason,
            "score": self.score,
            "recommended": self.recommended,
            "availability": self.availability,
        }


class RecoveryProvider(Protocol):
    name: str

    def search(
        self, config: Config, context: RecoveryContext
    ) -> list[ReplacementCandidate]:
        """Retrieve releases without grabbing or mutating Arr state."""


class ArrRecoveryProvider:
    name = ""
    media_parameter = ""

    def search(
        self, config: Config, context: RecoveryContext
    ) -> list[ReplacementCandidate]:
        if context.provider != self.name:
            raise RecoveryProviderError(
                f"{self.name.title()} cannot evaluate {context.provider} media."
            )
        if not config.service_enabled(self.name):
            raise RecoveryProviderError(
                f"{self.name.title()} is disabled or not configured."
            )

        service = config.service(self.name)
        base_url = str(service.get("base_url") or "").rstrip("/")
        endpoint = service.get("release_endpoint", "/api/v3/release")
        headers = {"Accept": "application/json"}
        if service.get("api_key"):
            headers["X-Api-Key"] = str(service["api_key"])

        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.get(
                    f"{base_url}{endpoint}",
                    headers=headers,
                    params={self.media_parameter: context.media_id},
                )
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:  # noqa: BLE001
            raise RecoveryProviderError(
                f"{self.name.title()} interactive search failed: "
                f"{type(exc).__name__}: {exc}"
            ) from exc

        if not isinstance(payload, list):
            raise RecoveryProviderError(
                f"{self.name.title()} returned an unexpected release payload."
            )
        return [
            _candidate_from_release(release)
            for release in payload
            if isinstance(release, dict)
        ]


class RadarrRecoveryProvider(ArrRecoveryProvider):
    name = "radarr"
    media_parameter = "movieId"


class SonarrRecoveryProvider(ArrRecoveryProvider):
    name = "sonarr"
    media_parameter = "episodeId"


@dataclass
class _CacheEntry:
    expires_at_monotonic: float
    evaluation: dict[str, Any]


_cache: dict[str, _CacheEntry] = {}
_cache_lock = threading.Lock()


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _rejection_text(value: Any) -> str | None:
    if not value:
        return None
    if not isinstance(value, list):
        value = [value]
    reasons: list[str] = []
    for rejection in value:
        if isinstance(rejection, dict):
            reason = rejection.get("reason") or rejection.get("message")
        else:
            reason = rejection
        if reason and str(reason) not in reasons:
            reasons.append(str(reason))
    return "; ".join(reasons) or None


def _candidate_from_release(release: dict[str, Any]) -> ReplacementCandidate:
    quality = release.get("quality")
    if isinstance(quality, dict):
        nested = quality.get("quality")
        if isinstance(nested, dict):
            quality_name = nested.get("name")
        else:
            quality_name = quality.get("name")
    else:
        quality_name = quality

    rejection_reason = _rejection_text(release.get("rejections"))
    rejection_lower = (rejection_reason or "").lower()
    return ReplacementCandidate(
        release_name=str(release.get("title") or "Unknown release"),
        quality=str(quality_name) if quality_name else None,
        indexer=str(release.get("indexer")) if release.get("indexer") else None,
        seeders=_to_int(release.get("seeders")),
        peers=_to_int(release.get("leechers") or release.get("peers")),
        age_days=_release_age_days(release),
        size=_to_int(release.get("size")),
        protocol=str(release.get("protocol")) if release.get("protocol") else None,
        custom_format_score=_to_int(release.get("customFormatScore")),
        rejected=bool(release.get("rejected") or rejection_reason),
        rejection_reason=rejection_reason,
        availability=_normalized_availability(release.get("availability")),
        indexer_priority=_to_int(release.get("indexerPriority"))
        if release.get("indexerPriority") is not None
        else None,
        quality_profile_match=not (
            "quality" in rejection_lower or "profile" in rejection_lower
        ),
    )


def _release_age_days(release: dict[str, Any]) -> float | None:
    age = _to_float(release.get("age"))
    if age is not None:
        return max(0.0, age)
    hours = _to_float(release.get("ageHours"))
    if hours is not None:
        return max(0.0, hours / 24)
    minutes = _to_float(release.get("ageMinutes"))
    if minutes is not None:
        return max(0.0, minutes / 1440)
    published = release.get("publishDate")
    if not published:
        return None
    try:
        instant = datetime.fromisoformat(str(published).replace("Z", "+00:00"))
        if instant.tzinfo is None:
            instant = instant.replace(tzinfo=timezone.utc)
        return max(
            0.0,
            (datetime.now(timezone.utc) - instant).total_seconds() / 86400,
        )
    except (TypeError, ValueError):
        return None


def _normalized_availability(value: Any) -> float | None:
    availability = _to_float(value)
    if availability is None or availability < 0:
        return None
    if availability <= 1:
        availability *= 100
    return min(100.0, availability)


def _weights(config: Config) -> dict[str, float]:
    configured = config.section("recovery").get("weights") or {}
    values: dict[str, float] = {}
    for key, default in DEFAULT_WEIGHTS.items():
        value = _to_float(configured.get(key))
        values[key] = max(0.0, value if value is not None else default)
    total = sum(values.values())
    if total <= 0:
        return dict(DEFAULT_WEIGHTS)
    return {key: value / total for key, value in values.items()}


def score_candidates(
    candidates: list[ReplacementCandidate], config: Config
) -> tuple[list[ReplacementCandidate], list[str]]:
    if not candidates:
        return [], []

    weights = _weights(config)
    max_seeders = max(candidate.seeders for candidate in candidates)
    priorities = [
        candidate.indexer_priority
        for candidate in candidates
        if candidate.indexer_priority is not None
    ]
    min_priority = min(priorities) if priorities else None
    max_priority = max(priorities) if priorities else None
    custom_scores = [candidate.custom_format_score for candidate in candidates]
    min_custom = min(custom_scores)
    max_custom = max(custom_scores)
    component_scores: dict[int, dict[str, float]] = {}

    for candidate in candidates:
        availability = candidate.availability
        if availability is None:
            swarm_total = candidate.seeders + candidate.peers
            availability = (
                candidate.seeders / swarm_total * 100 if swarm_total else 0.0
            )
        seeders = candidate.seeders / max_seeders * 100 if max_seeders else 0.0
        quality = 100.0 if candidate.quality_profile_match else 0.0
        age = (
            max(0.0, 100.0 - min(candidate.age_days, 365.0) / 365 * 100)
            if candidate.age_days is not None
            else 50.0
        )
        if candidate.indexer_priority is None or min_priority is None:
            indexer = 50.0
        elif max_priority == min_priority:
            indexer = 100.0
        else:
            indexer = (
                (max_priority - candidate.indexer_priority)
                / (max_priority - min_priority)
                * 100
            )
        if max_custom == min_custom:
            custom = 50.0 if max_custom == 0 else 100.0
        else:
            custom = (
                (candidate.custom_format_score - min_custom)
                / (max_custom - min_custom)
                * 100
            )
        components = {
            "availability": availability,
            "seeders": seeders,
            "quality": quality,
            "age": age,
            "indexer_priority": indexer,
            "custom_format": custom,
        }
        component_scores[id(candidate)] = components
        candidate.score = round(
            sum(components[key] * weights[key] for key in weights), 1
        )
        candidate.recommended = False

    candidates.sort(
        key=lambda candidate: (
            candidate.rejected,
            -candidate.score,
            -candidate.seeders,
            candidate.age_days if candidate.age_days is not None else float("inf"),
            candidate.release_name.lower(),
        )
    )
    recommended = next(
        (candidate for candidate in candidates if not candidate.rejected), None
    )
    if recommended is None:
        return candidates, []
    recommended.recommended = True

    eligible = [candidate for candidate in candidates if not candidate.rejected]
    recommended_components = component_scores[id(recommended)]
    reasons: list[str] = []
    if recommended_components["availability"] == max(
        component_scores[id(candidate)]["availability"] for candidate in eligible
    ):
        reasons.append("highest availability")
    if recommended.quality_profile_match:
        reasons.append("matches quality profile")
    if recommended.seeders == max(candidate.seeders for candidate in eligible):
        reasons.append("most seeders")
    known_ages = [
        candidate.age_days for candidate in eligible if candidate.age_days is not None
    ]
    if recommended.age_days is not None and (
        recommended.age_days <= 7
        or (known_ages and recommended.age_days == min(known_ages))
    ):
        reasons.append("recent upload")
    if (
        recommended.indexer_priority is not None
        and min_priority is not None
        and recommended.indexer_priority == min_priority
    ):
        reasons.append("preferred indexer")
    if (
        recommended.custom_format_score > 0
        and recommended.custom_format_score == max_custom
    ):
        reasons.append("strongest custom format score")
    return candidates, reasons[:4]


def resolve_context(
    torrent: dict[str, Any], events: list[dict[str, Any]]
) -> RecoveryContext:
    torrent_hash = str(torrent.get("hash") or "").lower()
    current_release = str(torrent.get("name") or "")
    preferred = _preferred_provider(torrent)

    for event in events:
        source = str(event.get("source") or "").lower()
        if source not in {"radarr", "sonarr"}:
            continue
        payload = _parse_payload(event)
        if not _event_matches(event, payload, torrent_hash, current_release):
            continue
        media_id = _media_id(source, payload)
        if media_id is None:
            continue
        if preferred and source != preferred:
            continue
        return RecoveryContext(
            torrent_hash=torrent_hash,
            current_release=current_release,
            provider=source,
            media_id=media_id,
            media_title=_media_title(source, payload) or event.get("title"),
        )

    provider_label = preferred.title() if preferred else "Radarr/Sonarr"
    raise RecoveryProviderError(
        f"No stored {provider_label} movie or episode ID could be matched to "
        "this torrent yet."
    )


def _parse_payload(event: dict[str, Any]) -> dict[str, Any]:
    try:
        payload = json.loads(event.get("payload_json") or "{}")
        return payload if isinstance(payload, dict) else {}
    except (TypeError, ValueError):
        return {}


def _preferred_provider(torrent: dict[str, Any]) -> str | None:
    source = " ".join(
        str(torrent.get(key) or "") for key in ("media_type", "category", "tags")
    ).lower()
    if "radarr" in source or "movie" in source:
        return "radarr"
    if "sonarr" in source or "series" in source or "episode" in source:
        return "sonarr"
    return None


def _event_matches(
    event: dict[str, Any],
    payload: dict[str, Any],
    torrent_hash: str,
    current_release: str,
) -> bool:
    raw = payload.get("raw") if isinstance(payload.get("raw"), dict) else {}
    data = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    identities = {
        event.get("torrent_hash"),
        event.get("download_id"),
        payload.get("torrent_hash"),
        payload.get("download_id"),
        data.get("torrentInfoHash"),
        data.get("torrentHash"),
        data.get("downloadHash"),
    }
    if torrent_hash and torrent_hash in {
        str(identity).lower() for identity in identities if identity
    }:
        return True
    titles = {
        event.get("title"),
        payload.get("sourceTitle"),
        raw.get("sourceTitle"),
    }
    return bool(
        current_release
        and current_release.lower()
        in {str(title).lower() for title in titles if title}
    )


def _media_id(source: str, payload: dict[str, Any]) -> int | None:
    raw = payload.get("raw") if isinstance(payload.get("raw"), dict) else {}
    if source == "radarr":
        movie = raw.get("movie") if isinstance(raw.get("movie"), dict) else {}
        values = (
            payload.get("movie_id"),
            payload.get("media_id"),
            movie.get("id"),
            raw.get("movieId"),
        )
    else:
        episode = (
            raw.get("episode") if isinstance(raw.get("episode"), dict) else {}
        )
        values = (
            payload.get("episode_id"),
            episode.get("id"),
            raw.get("episodeId"),
        )
    for value in values:
        try:
            if value is not None:
                return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _media_title(source: str, payload: dict[str, Any]) -> str | None:
    raw = payload.get("raw") if isinstance(payload.get("raw"), dict) else {}
    if source == "radarr":
        media = raw.get("movie")
    else:
        media = raw.get("series")
    if isinstance(media, dict) and media.get("title"):
        return str(media["title"])
    value = payload.get("movie_title") or payload.get("media_title")
    return str(value) if value else None


def evaluate_torrent(
    config: Config,
    torrent: dict[str, Any],
    events: list[dict[str, Any]],
    *,
    force: bool = False,
    providers: list[RecoveryProvider] | None = None,
) -> dict[str, Any]:
    torrent_hash = str(torrent.get("hash") or "").lower()
    if not torrent_hash:
        raise RecoveryProviderError("Torrent hash is missing.")
    now = time.monotonic()
    if not force:
        with _cache_lock:
            cached = _cache.get(torrent_hash)
            if cached and cached.expires_at_monotonic > now:
                return {**cached.evaluation, "cached": True}

    context = resolve_context(torrent, events)
    available = providers or [
        RadarrRecoveryProvider(),
        SonarrRecoveryProvider(),
    ]
    provider = next(
        (candidate for candidate in available if candidate.name == context.provider),
        None,
    )
    if provider is None:
        raise RecoveryProviderError(
            f"No recovery provider supports {context.provider}."
        )
    candidates, reasons = score_candidates(provider.search(config, context), config)
    evaluated_at = datetime.now(timezone.utc).isoformat()
    recommended = next(
        (candidate for candidate in candidates if candidate.recommended), None
    )
    evaluation = {
        "torrent_hash": torrent_hash,
        "provider": provider.name,
        "media_id": context.media_id,
        "media_title": context.media_title,
        "candidates": [candidate.to_dict() for candidate in candidates],
        "recommended_candidate": recommended.to_dict() if recommended else None,
        "recommendation_reasons": reasons,
        "recommendation_explanation": (
            "Recommended because " + ", ".join(reasons) + "."
            if recommended and reasons
            else (
                "No acceptable alternative release is currently available."
                if candidates
                else "No alternative releases were returned."
            )
        ),
        "evaluated_at": evaluated_at,
        "cached": False,
    }
    ttl = max(1, _to_int(config.section("recovery").get("cache_seconds") or 60))
    with _cache_lock:
        _cache[torrent_hash] = _CacheEntry(now + ttl, evaluation)
    return evaluation


def cached_evaluation(torrent_hash: str) -> dict[str, Any] | None:
    key = str(torrent_hash or "").lower()
    with _cache_lock:
        entry = _cache.get(key)
        if not entry:
            return None
        if entry.expires_at_monotonic <= time.monotonic():
            _cache.pop(key, None)
            return None
        return {**entry.evaluation, "cached": True}


def clear_recovery_cache() -> None:
    with _cache_lock:
        _cache.clear()
