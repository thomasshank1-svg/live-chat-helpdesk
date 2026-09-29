import sqlite3
import unittest

import domain


class ChatDomainTest(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        domain.init(self.db)

    def test_create_conversation_and_reply(self):
        result = domain.handle("POST", "/api/conversations", {"visitor": "Alex", "topic": "Shipping", "body": "Where is my order?"}, self.db)
        domain.handle("POST", "/api/messages", {"conversation_id": result["id"], "author": "agent", "body": "Checking now."}, self.db)
        messages = domain.messages(self.db, result["id"])
        self.assertEqual(len(messages), 2)

    def test_invalid_status_rejected(self):
        with self.assertRaises(ValueError):
            domain.handle("POST", "/api/status", {"id": 1, "status": "Archived"}, self.db)


if __name__ == "__main__":
    unittest.main()
