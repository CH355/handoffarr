import sqlite3
import unittest

from app import db


class DedupAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        with db._audit_lock:
            db._DEDUP_AUDIT.clear()

    def tearDown(self) -> None:
        with db._audit_lock:
            db._DEDUP_AUDIT.clear()

    def test_inserted_diff_sample_includes_deep_diff(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("CREATE TABLE raw_events (id INTEGER)")
        conn.execute("INSERT INTO raw_events (id) VALUES (42)")
        previous_row = conn.execute("SELECT id FROM raw_events").fetchone()

        db._dedup_audit_inserted(
            source="qbittorrent",
            event_type="torrent",
            identity=("external_id", "abc123"),
            previous_row=previous_row,
            previous_normalized_payload={"name": "Example", "peers": 4},
            new_normalized_payload={"name": "Example", "peers": 5},
            new_observed_at="2026-06-22T00:00:00+00:00",
            previous_had_fingerprint=True,
            fingerprint_changed=True,
        )

        sample = db.raw_event_dedup_audit_snapshot()["event_types"][
            "qbittorrent/torrent"
        ]["diff_samples"][0]

        self.assertIn("changed_keys", sample)
        self.assertIn("changed_key_count", sample)
        self.assertIn("changes", sample)
        self.assertIn("deep_diff", sample)
        self.assertEqual(sample["changed_keys"], ["peers"])
        self.assertEqual(sample["changed_key_count"], 1)
        self.assertEqual(sample["deep_diff"][0]["path"], "$.peers")


if __name__ == "__main__":
    unittest.main()
