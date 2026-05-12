import os
import psycopg2
import psycopg2.extras
from flask import g

DATABASE_URL = os.environ.get("DATABASE_URL")

DEFAULT_SEQUENCES = [
    {
        "touch_number": 1,
        "send_day": 1,
        "subject": "Quick question {{First Name}}",
        "body": (
            "Hi {{First Name}},\n\n"
            "Wanted to make sure we didn't miss your inquiry. Are you still looking for help?\n\n"
            "Just reply here and we'll get something set up quickly."
        ),
    },
    {
        "touch_number": 2,
        "send_day": 2,
        "subject": "Following up {{First Name}}",
        "body": (
            "{{First Name}} —\n\n"
            "Following up from yesterday. We have availability this week if you want to move forward.\n\n"
            "What does your schedule look like?"
        ),
    },
    {
        "touch_number": 3,
        "send_day": 5,
        "subject": "Something worth knowing {{First Name}}",
        "body": (
            "{{First Name}},\n\n"
            "Something worth knowing — most clients who reach out and then wait end up paying "
            "more or waiting longer when they circle back.\n\n"
            "If you're still interested, now is a good time. Just reply and I'll take care of the rest."
        ),
    },
    {
        "touch_number": 4,
        "send_day": 10,
        "subject": "Still relevant {{First Name}}?",
        "body": (
            "{{First Name}} —\n\n"
            "Still relevant for you? We help people in similar situations all the time. "
            "Happy to answer any questions if that's what's holding you back.\n\n"
            "Just reply to this email."
        ),
    },
    {
        "touch_number": 5,
        "send_day": 14,
        "subject": "Closing your file {{First Name}}",
        "body": (
            "{{First Name}},\n\n"
            "This will be my last follow-up. If you've found someone else, no problem at all.\n\n"
            "If you're still open to it, we're here. Just reply and we can pick up where we left off."
        ),
    },
]


class _DB:
    """Wraps a psycopg2 connection to expose sqlite3-style db.execute() shorthand."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        # psycopg2 uses %s placeholders; convert ? for compatibility
        sql = sql.replace("?", "%s")
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        return cur

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


def get_db():
    if "db" not in g:
        g.db = _DB(psycopg2.connect(DATABASE_URL))
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            business_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            google_sheet_id TEXT,
            niche TEXT,
            target_icp TEXT DEFAULT '',
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS target_icp TEXT DEFAULT ''")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS lead_uploads (
            id SERIAL PRIMARY KEY,
            client_id INTEGER NOT NULL REFERENCES clients(id),
            first_name TEXT,
            last_name TEXT,
            email TEXT,
            phone TEXT,
            service_requested TEXT,
            lead_source TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id SERIAL PRIMARY KEY,
            client_id INTEGER NOT NULL REFERENCES clients(id),
            event_type TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sequences (
            id SERIAL PRIMARY KEY,
            client_id INTEGER REFERENCES clients(id),
            touch_number INTEGER,
            send_day INTEGER,
            subject TEXT,
            body TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id SERIAL PRIMARY KEY,
            client_id INTEGER NOT NULL REFERENCES clients(id),
            type TEXT,
            message TEXT,
            is_read BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("ALTER TABLE lead_uploads ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'New'")
    cur.execute("ALTER TABLE lead_uploads ADD COLUMN IF NOT EXISTS notes TEXT DEFAULT ''")
    conn.commit()
    cur.close()
    conn.close()


def add_notification(db, client_id, notif_type, message):
    db.execute(
        "INSERT INTO notifications (client_id, type, message) VALUES (?, ?, ?)",
        (client_id, notif_type, message)
    )


def seed_sequences(db, client_id):
    for seq in DEFAULT_SEQUENCES:
        db.execute(
            """INSERT INTO sequences (client_id, touch_number, send_day, subject, body, status)
               VALUES (?, ?, ?, ?, ?, 'active')""",
            (client_id, seq["touch_number"], seq["send_day"], seq["subject"], seq["body"]),
        )
