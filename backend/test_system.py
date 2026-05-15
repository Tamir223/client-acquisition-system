"""
End-to-end system tests for Client Machinery.
Callable via: GET /api/admin/run-tests (X-Admin-Key required)
or directly:  python test_system.py
"""
import os
import traceback
from datetime import datetime, timedelta

import psycopg2
import psycopg2.extras


def _conn():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


def _run(name, fn):
    try:
        fn()
        return {"name": name, "status": "pass", "error": None}
    except Exception as e:
        return {"name": name, "status": "fail", "error": str(e), "trace": traceback.format_exc()}


# ── DB connectivity ───────────────────────────────────────────────────────────

def test_db_connection():
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT 1")
    assert cur.fetchone()[0] == 1
    cur.close()
    conn.close()


def test_tables_exist():
    expected = [
        "clients", "lead_uploads", "activity_log", "sequences",
        "notifications", "scheduled_emails", "telegram_verifications",
        "email_events", "suppression_list", "password_reset_tokens",
        "lead_replies",
    ]
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
    )
    existing = {r[0] for r in cur.fetchall()}
    cur.close()
    conn.close()
    missing = [t for t in expected if t not in existing]
    assert not missing, f"Missing tables: {missing}"


def test_clients_columns():
    required = [
        "gmail_access_token", "gmail_connected", "telegram_chat_id",
        "telegram_connected", "notify_replies", "plan", "leads_this_month",
        "referral_code", "lead_score",
    ]
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT column_name FROM information_schema.columns
           WHERE table_name IN ('clients','lead_uploads')"""
    )
    cols = {r[0] for r in cur.fetchall()}
    cur.close()
    conn.close()
    missing = [c for c in required if c not in cols]
    assert not missing, f"Missing columns: {missing}"


# ── Sequence engine ───────────────────────────────────────────────────────────

def test_sequence_import():
    from sequence_engine import SequenceEngine
    assert hasattr(SequenceEngine, "schedule_sequence")
    assert hasattr(SequenceEngine, "send_due_emails")
    assert hasattr(SequenceEngine, "check_gmail_replies")
    assert hasattr(SequenceEngine, "cancel_sequence")


def test_telegram_alerts_import():
    from telegram_alerts import (
        send_telegram, alert_partners, alert_client,
        alert_reply, alert_email_sent, alert_booking, alert_sequence_started,
    )
    assert callable(send_telegram)


def test_suppression_list_check():
    """schedule_sequence should skip leads on suppression list."""
    from sequence_engine import SequenceEngine
    conn = _conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT id FROM clients LIMIT 1")
    client_row = cur.fetchone()
    if not client_row:
        cur.close()
        conn.close()
        return  # nothing to test without a client
    cid = client_row["id"]

    test_email = "suppression-test@example.invalid"
    cur.execute(
        "INSERT INTO suppression_list (client_id, email, reason) VALUES (%s, %s, 'test') ON CONFLICT DO NOTHING",
        (cid, test_email)
    )
    conn.commit()

    result = SequenceEngine.schedule_sequence(cid, -1, {"email": test_email})
    assert result == 0, f"Expected 0 (suppressed), got {result}"

    cur.execute("DELETE FROM suppression_list WHERE client_id=%s AND email=%s", (cid, test_email))
    conn.commit()
    cur.close()
    conn.close()


# ── Auth ──────────────────────────────────────────────────────────────────────

def test_auth_import():
    from auth import auth_bp, require_auth
    assert auth_bp is not None
    assert callable(require_auth)


def test_jwt_secret_set():
    secret = os.getenv("PORTAL_JWT_SECRET")
    assert secret and len(secret) >= 16, "PORTAL_JWT_SECRET too short or not set"


# ── Portal routes ─────────────────────────────────────────────────────────────

def test_portal_import():
    from portal import portal_bp
    from flask import Flask
    test_app = Flask(__name__)
    test_app.register_blueprint(portal_bp)
    rules = [r.rule for r in test_app.url_map.iter_rules()]
    required_routes = [
        '/api/portal/login',
        '/api/portal/leads',
        '/api/portal/dashboard',
        '/api/portal/inbox',
        '/api/portal/notifications',
        '/api/webhooks/reply-detected',
        '/api/portal/leads/update-score',
    ]
    for route in required_routes:
        assert any(route in r for r in rules), f"Missing route: {route}"


def test_plan_limits():
    from portal import PLAN_LIMITS
    assert PLAN_LIMITS["pilot"] == 500
    assert PLAN_LIMITS["enterprise"] is None


# ── Gmail OAuth ───────────────────────────────────────────────────────────────

def test_gmail_oauth_import():
    from gmail_oauth import get_oauth_url, send_via_gmail, get_unread_replies
    assert callable(get_oauth_url)


def test_gmail_env_vars():
    cid = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    cs = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    assert cid, "GOOGLE_OAUTH_CLIENT_ID not set"
    assert cs, "GOOGLE_OAUTH_CLIENT_SECRET not set"


# ── Telegram ──────────────────────────────────────────────────────────────────

def test_telegram_env():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    assert token, "TELEGRAM_BOT_TOKEN not set"


def test_telegram_bot_import():
    from telegram_bot import handle_webhook
    assert callable(handle_webhook)


# ── Scheduler ─────────────────────────────────────────────────────────────────

def test_scheduler_import():
    from scheduler import start_scheduler
    assert callable(start_scheduler)


# ── Stripe ────────────────────────────────────────────────────────────────────

def test_stripe_env():
    key = os.getenv("STRIPE_SECRET_KEY")
    assert key, "STRIPE_SECRET_KEY not set"


# ── Database indexes ──────────────────────────────────────────────────────────

def test_indexes_exist():
    required_indexes = [
        "idx_lead_uploads_client",
        "idx_scheduled_status",
        "idx_replies_client",
        "idx_notifications_client",
    ]
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT indexname FROM pg_indexes WHERE schemaname='public'"
    )
    existing = {r[0] for r in cur.fetchall()}
    cur.close()
    conn.close()
    missing = [i for i in required_indexes if i not in existing]
    assert not missing, f"Missing indexes: {missing}"


# ── Inbox ─────────────────────────────────────────────────────────────────────

def test_lead_replies_table():
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'lead_replies'"
    )
    cols = {r[0] for r in cur.fetchall()}
    cur.close()
    conn.close()
    required = {"client_id", "lead_id", "from_email", "snippet", "is_read", "source"}
    missing = required - cols
    assert not missing, f"lead_replies missing columns: {missing}"


# ── Run all ───────────────────────────────────────────────────────────────────

ALL_TESTS = [
    ("DB connection", test_db_connection),
    ("Tables exist", test_tables_exist),
    ("Required columns", test_clients_columns),
    ("Sequence engine import", test_sequence_import),
    ("Telegram alerts import", test_telegram_alerts_import),
    ("Suppression list check", test_suppression_list_check),
    ("Auth import", test_auth_import),
    ("JWT secret set", test_jwt_secret_set),
    ("Portal import", test_portal_import),
    ("Plan limits", test_plan_limits),
    ("Gmail OAuth import", test_gmail_oauth_import),
    ("Gmail env vars", test_gmail_env_vars),
    ("Telegram env", test_telegram_env),
    ("Telegram bot import", test_telegram_bot_import),
    ("Scheduler import", test_scheduler_import),
    ("Stripe env", test_stripe_env),
    ("DB indexes", test_indexes_exist),
    ("lead_replies table", test_lead_replies_table),
]


def run_all_tests():
    results = [_run(name, fn) for name, fn in ALL_TESTS]
    passed = sum(1 for r in results if r["status"] == "pass")
    failed = sum(1 for r in results if r["status"] == "fail")
    return {
        "summary": {"total": len(results), "passed": passed, "failed": failed},
        "results": results,
        "timestamp": datetime.utcnow().isoformat(),
    }


if __name__ == "__main__":
    import json
    output = run_all_tests()
    print(json.dumps(output, indent=2))
