from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import patch

from app.collectors.qbittorrent import (
    DEAD_REASON,
    _normalize_torrent_full,
    delete_torrents,
)
from app.config import Config
from app.torrents import enrich_torrent, recommendation_for, torrent_response


class DeadTorrentDetectionTests(TestCase):
    def torrent(self, **overrides):
        torrent = {
            "hash": "abc",
            "name": "Release",
            "state": "stalledDL",
            "progress": 0,
            "availability": 0,
            "num_seeds": 0,
            "num_complete": 0,
            "num_leechs": 0,
            "total_size": 100,
        }
        torrent.update(overrides)
        return _normalize_torrent_full(torrent)

    def test_zero_progress_and_availability_is_dead(self):
        torrent = self.torrent()
        self.assertTrue(torrent["dead_torrent"])
        self.assertEqual(torrent["dead_reason"], DEAD_REASON)

    def test_nonzero_progress_is_not_dead(self):
        self.assertFalse(self.torrent(progress=0.01)["dead_torrent"])

    def test_nonzero_availability_is_not_dead(self):
        self.assertFalse(self.torrent(availability=0.5)["dead_torrent"])

    def test_completed_torrent_is_not_dead(self):
        self.assertFalse(self.torrent(state="uploading", progress=1)["dead_torrent"])

    def test_paused_torrent_is_not_dead(self):
        self.assertFalse(self.torrent(state="pausedDL")["dead_torrent"])

    def test_missing_availability_uses_seed_counts(self):
        raw = {
            "hash": "abc",
            "state": "stalledDL",
            "progress": 0,
            "num_seeds": 0,
            "num_complete": 0,
        }
        self.assertTrue(_normalize_torrent_full(raw)["dead_torrent"])

    def test_metrics_include_count_size_and_todays_additions(self):
        dead = self.torrent()
        dead["dead_since"] = "2026-07-04T12:00:00+00:00"
        live = self.torrent(
            hash="def",
            state="uploading",
            progress=1,
            availability=1,
            num_seeds=1,
        )
        response = torrent_response(
            [dead, live], now=datetime(2026, 7, 4, 18, tzinfo=timezone.utc)
        )
        self.assertEqual(response["summary"]["total_torrents"], 2)
        self.assertEqual(response["summary"]["dead_torrents"], 1)
        self.assertEqual(response["summary"]["healthy_torrents"], 1)
        self.assertEqual(response["summary"]["potentially_recoverable"], 1)
        self.assertEqual(response["summary"]["dead_torrents_size"], 100)
        self.assertEqual(response["summary"]["dead_torrents_today"], 1)
        self.assertEqual(response["health"]["severity"], "warning")

    def test_dead_torrent_recommends_recovery(self):
        recommendation, reason = recommendation_for(self.torrent())
        self.assertEqual(recommendation, "Recover")
        self.assertIn("No seeders", reason)

    def test_stalled_torrent_with_few_seeders_recommends_monitoring(self):
        torrent = self.torrent(progress=0.25, availability=0.8, num_seeds=2)
        recommendation, reason = recommendation_for(torrent)
        self.assertEqual(recommendation, "Monitor")
        self.assertIn("2 seeders", reason)

    def test_low_availability_recommends_replacement_soon(self):
        torrent = self.torrent(progress=0.25, availability=0.04, num_seeds=5)
        recommendation, reason = recommendation_for(torrent)
        self.assertEqual(recommendation, "Replace soon")
        self.assertIn("4.0%", reason)

    def test_healthy_torrent_has_no_recovery_recommendation(self):
        torrent = self.torrent(
            state="uploading", progress=1, availability=0, num_seeds=0
        )
        recommendation, reason = recommendation_for(torrent)
        self.assertIsNone(recommendation)
        self.assertIn("healthy", reason)

    def test_replacement_candidate_contract_is_present_and_empty(self):
        enriched = enrich_torrent(self.torrent())
        self.assertEqual(enriched["replacement_candidates"], [])
        self.assertEqual(enriched["recovery_status"], "dead")

    def test_remove_dead_preserves_downloaded_files(self):
        calls = []

        class Response:
            status_code = 200
            text = "Ok."

            def raise_for_status(self):
                return None

        class Client:
            def __init__(self, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def post(self, url, **kwargs):
                calls.append((url, kwargs))
                return Response()

        config = Config(
            {
                "services": {
                    "qbittorrent": {
                        "enabled": True,
                        "base_url": "http://qbit",
                        "username": "user",
                        "password": "pass",
                    }
                }
            },
            "test.yaml",
            True,
        )
        with patch("app.collectors.qbittorrent.httpx.Client", Client):
            result = delete_torrents(config, ["ABC"], delete_files=False)

        self.assertTrue(result["ok"])
        self.assertEqual(calls[-1][1]["data"]["hashes"], "abc")
        self.assertEqual(calls[-1][1]["data"]["deleteFiles"], "false")

    def test_bulk_remove_can_delete_downloaded_files(self):
        calls = []

        class Response:
            status_code = 200
            text = "Ok."

            def raise_for_status(self):
                return None

        class Client:
            def __init__(self, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def post(self, url, **kwargs):
                calls.append((url, kwargs))
                return Response()

        config = Config(
            {
                "services": {
                    "qbittorrent": {
                        "enabled": True,
                        "base_url": "http://qbit",
                        "username": "user",
                        "password": "pass",
                    }
                }
            },
            "test.yaml",
            True,
        )
        with patch("app.collectors.qbittorrent.httpx.Client", Client):
            result = delete_torrents(config, ["ABC", "def"], delete_files=True)

        self.assertTrue(result["ok"])
        self.assertEqual(calls[-1][1]["data"]["hashes"], "abc|def")
        self.assertEqual(calls[-1][1]["data"]["deleteFiles"], "true")
