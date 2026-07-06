import json
from unittest import TestCase
from unittest.mock import patch

from app.config import Config
from app.recovery import (
    RadarrRecoveryProvider,
    RecoveryContext,
    ReplacementCandidate,
    SonarrRecoveryProvider,
    clear_recovery_cache,
    evaluate_torrent,
    score_candidates,
)


def recovery_config() -> Config:
    return Config(
        {
            "recovery": {"cache_seconds": 60},
            "services": {
                "radarr": {
                    "enabled": True,
                    "base_url": "http://radarr:7878",
                    "api_key": "radarr-key",
                },
                "sonarr": {
                    "enabled": True,
                    "base_url": "http://sonarr:8989",
                    "api_key": "sonarr-key",
                },
            },
        },
        "test.yaml",
        True,
    )


class RecoveryProviderTests(TestCase):
    def tearDown(self):
        clear_recovery_cache()

    def test_radarr_provider_uses_interactive_movie_search(self):
        calls = []

        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return [
                    {
                        "title": "Movie.2026.1080p",
                        "quality": {"quality": {"name": "WEBDL-1080p"}},
                        "indexer": "Indexer A",
                        "seeders": 30,
                        "leechers": 4,
                        "age": 2,
                        "size": 1_000,
                        "protocol": "torrent",
                        "customFormatScore": 10,
                        "indexerPriority": 1,
                        "rejections": [],
                    }
                ]

        class Client:
            def __init__(self, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def get(self, url, **kwargs):
                calls.append((url, kwargs))
                return Response()

        context = RecoveryContext("abc", "Old release", "radarr", 42)
        with patch("app.recovery.httpx.Client", Client):
            candidates = RadarrRecoveryProvider().search(
                recovery_config(), context
            )

        self.assertEqual(calls[0][0], "http://radarr:7878/api/v3/release")
        self.assertEqual(calls[0][1]["params"], {"movieId": 42})
        self.assertEqual(calls[0][1]["headers"]["X-Api-Key"], "radarr-key")
        self.assertEqual(candidates[0].release_name, "Movie.2026.1080p")
        self.assertEqual(candidates[0].quality, "WEBDL-1080p")

    def test_sonarr_provider_uses_interactive_episode_search(self):
        calls = []

        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return [
                    {
                        "title": "Series.S01E02.1080p",
                        "quality": {"quality": {"name": "HDTV-1080p"}},
                        "seeders": 12,
                        "leechers": 2,
                        "ageHours": 12,
                        "size": 500,
                    }
                ]

        class Client:
            def __init__(self, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def get(self, url, **kwargs):
                calls.append((url, kwargs))
                return Response()

        context = RecoveryContext("def", "Old episode", "sonarr", 84)
        with patch("app.recovery.httpx.Client", Client):
            candidates = SonarrRecoveryProvider().search(
                recovery_config(), context
            )

        self.assertEqual(calls[0][0], "http://sonarr:8989/api/v3/release")
        self.assertEqual(calls[0][1]["params"], {"episodeId": 84})
        self.assertEqual(candidates[0].age_days, 0.5)

    def test_scores_sorts_and_selects_the_best_accepted_candidate(self):
        candidates = [
            ReplacementCandidate(
                "Older release",
                "WEBDL-1080p",
                "Indexer B",
                8,
                20,
                90,
                800,
                "torrent",
                0,
                False,
                None,
                availability=40,
                indexer_priority=5,
            ),
            ReplacementCandidate(
                "Best release",
                "Bluray-1080p",
                "Indexer A",
                40,
                5,
                2,
                1_000,
                "torrent",
                15,
                False,
                None,
                availability=95,
                indexer_priority=1,
            ),
            ReplacementCandidate(
                "Rejected release",
                "Bluray-2160p",
                "Indexer A",
                100,
                1,
                1,
                2_000,
                "torrent",
                20,
                True,
                "Not wanted",
                availability=100,
                indexer_priority=1,
            ),
        ]

        scored, reasons = score_candidates(candidates, recovery_config())

        self.assertEqual(scored[0].release_name, "Best release")
        self.assertTrue(scored[0].recommended)
        self.assertEqual(sum(candidate.recommended for candidate in scored), 1)
        self.assertGreater(scored[0].score, scored[1].score)
        self.assertEqual(scored[-1].release_name, "Rejected release")
        self.assertIn("highest availability", reasons)
        self.assertIn("most seeders", reasons)

    def test_scoring_weights_are_configurable(self):
        config = Config(
            {
                "recovery": {
                    "weights": {
                        "availability": 0,
                        "seeders": 1,
                        "quality": 0,
                        "age": 0,
                        "indexer_priority": 0,
                        "custom_format": 0,
                    }
                }
            },
            "test.yaml",
            True,
        )
        candidates = [
            ReplacementCandidate(
                "More available",
                "WEBDL-1080p",
                "Indexer",
                2,
                1,
                1,
                1_000,
                "torrent",
                0,
                False,
                None,
                availability=100,
            ),
            ReplacementCandidate(
                "More seeders",
                "WEBDL-1080p",
                "Indexer",
                20,
                1,
                30,
                1_000,
                "torrent",
                0,
                False,
                None,
                availability=20,
            ),
        ]

        scored, _reasons = score_candidates(candidates, config)

        self.assertEqual(scored[0].release_name, "More seeders")
        self.assertEqual(scored[0].score, 100)

    def test_scoring_weights_are_configurable(self):
        config = Config(
            {
                "recovery": {
                    "weights": {
                        "availability": 0,
                        "seeders": 1,
                        "quality": 0,
                        "age": 0,
                        "indexer_priority": 0,
                        "custom_format": 0,
                    }
                }
            },
            "test.yaml",
            True,
        )
        candidates = [
            ReplacementCandidate(
                "More available",
                "WEBDL-1080p",
                "Indexer",
                2,
                1,
                1,
                1_000,
                "torrent",
                0,
                False,
                None,
                availability=100,
            ),
            ReplacementCandidate(
                "More seeders",
                "WEBDL-1080p",
                "Indexer",
                20,
                1,
                30,
                1_000,
                "torrent",
                0,
                False,
                None,
                availability=20,
            ),
        ]

        scored, _reasons = score_candidates(candidates, config)

        self.assertEqual(scored[0].release_name, "More seeders")
        self.assertEqual(scored[0].score, 100)

    def test_evaluation_cache_reuses_provider_results_for_sixty_seconds(self):
        class Provider:
            name = "radarr"

            def __init__(self):
                self.calls = 0

            def search(self, config, context):
                self.calls += 1
                return [
                    ReplacementCandidate(
                        "Candidate",
                        "WEBDL-1080p",
                        "Indexer",
                        10,
                        2,
                        1,
                        1_000,
                        "torrent",
                        0,
                        False,
                        None,
                        availability=80,
                        indexer_priority=1,
                    )
                ]

        provider = Provider()
        torrent = {"hash": "ABC", "name": "Old", "category": "radarr"}
        events = [
            {
                "source": "radarr",
                "torrent_hash": "abc",
                "payload_json": json.dumps(
                    {"movie_id": 42, "sourceTitle": "Old"}
                ),
            }
        ]

        first = evaluate_torrent(
            recovery_config(), torrent, events, providers=[provider]
        )
        second = evaluate_torrent(
            recovery_config(), torrent, events, providers=[provider]
        )

        self.assertFalse(first["cached"])
        self.assertTrue(second["cached"])
        self.assertEqual(provider.calls, 1)
