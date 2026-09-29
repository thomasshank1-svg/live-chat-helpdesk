"""Live-chat style support inbox with canned replies and conversation status."""
from datetime import datetime, timezone

STATUSES = ["Open", "Waiting", "Resolved"]
CANNED = [
    "Thanks for reaching out. I am checking this now.",
    "Could you share the order number or account email?",
    "This is resolved on our side. Please confirm it works for you.",
]


def init(db):
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS conversations(
            id INTEGER PRIMARY KEY,
            visitor TEXT NOT NULL,
            topic TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Open',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY,
            conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            author TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    if not db.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]:
        now = datetime.now(timezone.utc).isoformat()
        row = db.execute(
            "INSERT INTO conversations(visitor,topic,status,created_at) VALUES(?,?,?,?)",
            ("Maya Visitor", "Refund question", "Open", now),
        )
        db.executemany(
            "INSERT INTO messages(conversation_id,author,body,created_at) VALUES(?,?,?,?)",
            [(row.lastrowid, "visitor", "Can I return a digital template?", now), (row.lastrowid, "agent", CANNED[0], now)],
        )


def conversations(db):
    return [dict(row) for row in db.execute("SELECT * FROM conversations ORDER BY id DESC")]


def messages(db, conversation_id):
    return [dict(row) for row in db.execute("SELECT * FROM messages WHERE conversation_id=? ORDER BY id", (conversation_id,))]


def handle(method, path, data, db):
    if method == "GET" and path == "/api/state":
        convos = conversations(db)
        active_id = convos[0]["id"] if convos else None
        return {"statuses": STATUSES, "canned": CANNED, "conversations": convos, "messages": messages(db, active_id) if active_id else []}

    if method == "POST" and path == "/api/conversations":
        visitor = str(data.get("visitor", "")).strip()
        topic = str(data.get("topic", "")).strip()
        body = str(data.get("body", "")).strip()
        if not 2 <= len(visitor) <= 80 or not 2 <= len(topic) <= 120 or not 2 <= len(body) <= 1000:
            raise ValueError("Enter visitor, topic, and message.")
        now = datetime.now(timezone.utc).isoformat()
        row = db.execute("INSERT INTO conversations(visitor,topic,created_at) VALUES(?,?,?)", (visitor, topic, now))
        db.execute("INSERT INTO messages(conversation_id,author,body,created_at) VALUES(?,?,?,?)", (row.lastrowid, "visitor", body, now))
        return {"id": row.lastrowid}

    if method == "POST" and path == "/api/messages":
        conversation_id = data.get("conversation_id")
        body = str(data.get("body", "")).strip()
        author = str(data.get("author", "agent")).strip()
        if author not in {"agent", "visitor"} or not 1 <= len(body) <= 1000:
            raise ValueError("Message must be 1 to 1,000 characters.")
        if not db.execute("SELECT 1 FROM conversations WHERE id=?", (conversation_id,)).fetchone():
            raise LookupError()
        db.execute(
            "INSERT INTO messages(conversation_id,author,body,created_at) VALUES(?,?,?,?)",
            (conversation_id, author, body, datetime.now(timezone.utc).isoformat()),
        )
        return {"ok": True}

    if method == "POST" and path == "/api/status":
        status = str(data.get("status", "")).strip()
        if status not in STATUSES:
            raise ValueError("Choose a listed status.")
        row = db.execute("UPDATE conversations SET status=? WHERE id=?", (status, data.get("id")))
        if not row.rowcount:
            raise LookupError()
        return {"ok": True}

    if method == "POST" and path == "/api/messages-for":
        return {"messages": messages(db, data.get("conversation_id"))}

    raise LookupError()
