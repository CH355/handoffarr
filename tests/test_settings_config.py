from __future__ import annotations

import os
import tempfile
import unittest

import yaml
from pydantic import ValidationError

from app.config import load_config
from app.settings_config import (
    CleanupExecutionSettings,
    StorageThresholdSettings,
    settings_response,
    update_cleanup,
    update_storage,
)


class SettingsConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.temp.name, "config.yaml")
        self.raw = {
            "cleanup_execution": {
                "enabled": False,
                "allow_single_item_execution": False,
                "allow_batch_execution": False,
                "require_confirmation_phrase": True,
                "require_batch_dry_run": True,
                "max_items_per_request": 1,
                "max_batch_items": 5,
                "allowed_review_class": "Safe Review Candidate",
            },
            "storage": {
                "enabled": True,
                "volumes": [{"label": "downloads", "path": "/downloads"}],
                "thresholds": {
                    "critical_free_bytes": 100,
                    "warning_free_bytes": 200,
                    "completed_torrent_count": 25,
                    "retained_bytes": 1000,
                },
            },
            "services": {
                "radarr": {"api_key": "secret", "base_url": "http://radarr:7878"}
            },
        }
        self._write(self.raw)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _write(self, value: dict) -> None:
        with open(self.path, "w", encoding="utf-8") as handle:
            yaml.safe_dump(value, handle, sort_keys=False)

    def _read(self) -> dict:
        with open(self.path, "r", encoding="utf-8") as handle:
            return yaml.safe_load(handle)

    def test_response_contains_only_allowlisted_settings(self) -> None:
        response = settings_response(load_config(self.path))
        self.assertEqual(set(response), {"cleanup", "storage", "restart_required"})
        self.assertNotIn("services", response)
        self.assertNotIn("allowed_review_class", response["cleanup"])

    def test_cleanup_update_preserves_protected_values(self) -> None:
        updated = update_cleanup(
            load_config(self.path),
            CleanupExecutionSettings(
                enabled=True,
                allow_single_item_execution=True,
                allow_batch_execution=True,
                require_confirmation_phrase=True,
                require_batch_dry_run=True,
                max_items_per_request=1,
                max_batch_items=10,
            ),
        )
        raw = self._read()
        self.assertTrue(raw["cleanup_execution"]["allow_batch_execution"])
        self.assertEqual(raw["cleanup_execution"]["allowed_review_class"], "Safe Review Candidate")
        self.assertEqual(raw["services"]["radarr"]["api_key"], "secret")
        self.assertTrue(settings_response(updated)["cleanup"]["allow_batch_execution"])

    def test_storage_update_preserves_paths_and_services(self) -> None:
        update_storage(
            load_config(self.path),
            StorageThresholdSettings(
                critical_free_bytes=500,
                warning_free_bytes=1000,
                completed_torrent_count=50,
                retained_bytes=2000,
            ),
        )
        raw = self._read()
        self.assertEqual(raw["storage"]["volumes"][0]["path"], "/downloads")
        self.assertEqual(raw["services"]["radarr"]["api_key"], "secret")

    def test_storage_warning_must_exceed_critical(self) -> None:
        with self.assertRaises(ValidationError):
            StorageThresholdSettings(
                critical_free_bytes=1000,
                warning_free_bytes=1000,
                completed_torrent_count=1,
                retained_bytes=1,
            )

    def test_single_item_request_limit_is_fixed(self) -> None:
        with self.assertRaises(ValidationError):
            CleanupExecutionSettings(
                enabled=True,
                allow_single_item_execution=True,
                allow_batch_execution=True,
                require_confirmation_phrase=True,
                require_batch_dry_run=True,
                max_items_per_request=2,
                max_batch_items=10,
            )


if __name__ == "__main__":
    unittest.main()
