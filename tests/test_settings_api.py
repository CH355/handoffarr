from __future__ import annotations

import os
import tempfile
import unittest

import yaml
from fastapi.testclient import TestClient

from app import main
from app.config import load_config


class SettingsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.temp.name, "config.yaml")
        with open(self.path, "w", encoding="utf-8") as handle:
            yaml.safe_dump(
                {
                    "cleanup_execution": {
                        "enabled": False,
                        "allow_single_item_execution": False,
                        "allow_batch_execution": False,
                        "require_confirmation_phrase": True,
                        "require_batch_dry_run": True,
                        "max_items_per_request": 1,
                        "max_batch_items": 5,
                    },
                    "storage": {
                        "thresholds": {
                            "critical_free_bytes": 100,
                            "warning_free_bytes": 200,
                            "completed_torrent_count": 25,
                            "retained_bytes": 1000,
                        }
                    },
                    "services": {"radarr": {"api_key": "secret"}},
                },
                handle,
                sort_keys=False,
            )
        main._config = load_config(self.path)
        self.client = TestClient(main.app)

    def tearDown(self) -> None:
        self.temp.cleanup()
        main._config = None

    def test_get_settings_never_returns_secrets(self) -> None:
        response = self.client.get("/api/settings")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("secret", response.text)
        self.assertEqual(set(response.json()), {"cleanup", "storage", "restart_required"})

    def test_put_requires_expert_header(self) -> None:
        payload = self.client.get("/api/settings").json()["cleanup"]
        response = self.client.put("/api/settings/cleanup", json=payload)
        self.assertEqual(response.status_code, 403)

    def test_put_updates_runtime_and_persisted_config(self) -> None:
        payload = self.client.get("/api/settings").json()["cleanup"]
        payload["allow_batch_execution"] = True
        response = self.client.put(
            "/api/settings/cleanup",
            json=payload,
            headers={"X-Handoffarr-Expert-Mode": "true"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["cleanup"]["allow_batch_execution"])
        self.assertTrue(main.get_config().section("cleanup_execution")["allow_batch_execution"])
        with open(self.path, "r", encoding="utf-8") as handle:
            self.assertTrue(yaml.safe_load(handle)["cleanup_execution"]["allow_batch_execution"])


if __name__ == "__main__":
    unittest.main()
