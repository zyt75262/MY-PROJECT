import base64
import tempfile
import unittest
from pathlib import Path

from community.errors import ValidationError
from community.storage import RecordError, Storage, media_value


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "test.sqlite3"
        self.store = Storage(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_full_ticket_lifecycle(self):
        ticket = self.store.create_ticket({"category": "手机操作", "body": "模拟：不会视频通话"})
        identifier = ticket["id"]
        self.assertEqual(ticket["status"], "pending")
        with self.assertRaises(RecordError):
            self.store.transition_ticket(identifier, "reply", {"body": "先认领"})
        self.assertEqual(self.store.transition_ticket(identifier, "claim", {})["status"], "active")
        with self.assertRaises(RecordError):
            self.store.transition_ticket(identifier, "resolve", {})
        self.store.transition_ticket(identifier, "reply", {"body": "打开家人的聊天窗口。"})
        self.assertEqual(self.store.transition_ticket(identifier, "resolve", {})["status"], "done")
        self.assertEqual(self.store.transition_ticket(identifier, "reopen", {})["status"], "active")
        restored = Storage(self.path).get_ticket(identifier)
        self.assertEqual(len(restored["replies"]), 1)
        self.assertIsNone(restored["resolved_at"])

    def test_invalid_transition_does_not_change_record(self):
        ticket = self.store.create_ticket({"category": "其他问题", "body": "模拟问题"})
        with self.assertRaises(RecordError):
            self.store.transition_ticket(ticket["id"], "reopen", {})
        self.assertEqual(self.store.get_ticket(ticket["id"])["status"], "pending")

    def test_sql_like_user_text_remains_text(self):
        body = "'); DROP TABLE tickets; -- <script>alert(1)</script>"
        ticket = self.store.create_ticket({"category": "其他问题", "body": body})
        self.assertEqual(self.store.get_ticket(ticket["id"])["body"], body)
        self.assertEqual(len(self.store.tickets()), 1)


    def test_media_limits_and_types(self):
        # This is a real 1x1 PNG fixture, not a user's image.
        image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jR3sAAAAASUVORK5CYII="
        self.assertEqual(media_value(image, "image"), image)
        for value in ("data:image/svg+xml;base64,PHN2Zz4=", "file:///etc/passwd", "data:image/png;base64,###"):
            with self.assertRaises(ValidationError):
                media_value(value, "image")
        oversized = "data:image/png;base64," + base64.b64encode(b"a" * 800001).decode()
        with self.assertRaises(ValidationError):
            media_value(oversized, "image")

    def test_empty_ticket_and_missing_record(self):
        with self.assertRaises(ValidationError):
            self.store.create_ticket({"category": "手机操作", "body": " "})
        with self.assertRaises(RecordError) as context:
            self.store.get_ticket(999)
        self.assertEqual(context.exception.status, 404)


if __name__ == "__main__":
    unittest.main()
