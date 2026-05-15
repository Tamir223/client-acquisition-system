import logging
import os
import random
import string
from datetime import datetime, timedelta

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


def _get_conn():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


def _send(chat_id, text):
    if not TELEGRAM_BOT_TOKEN:
        return
    import requests
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=5,
        )
    except Exception as e:
        logger.error(f"[telegram_bot] send failed: {e}")


def _gen_code():
    return "".join(random.choices(string.digits, k=6))


def handle_webhook(update):
    message = update.get("message") or {}
    chat_id = (message.get("chat") or {}).get("id")
    text = (message.get("text") or "").strip()

    if not chat_id or not text:
        return

    if text.startswith("/start"):
        _send(
            chat_id,
            "\U0001f44b Welcome to Client Machinery!\n\n"
            "Get instant alerts when your leads reply.\n\n"
            "To connect your account:\n"
            "/connect your@email.com",
        )

    elif text.startswith("/connect"):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            _send(chat_id, "Usage: /connect your@email.com")
            return
        email = parts[1].strip().lower()

        conn = _get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cur.execute("SELECT id, name FROM clients WHERE email = %s", (email,))
            client = cur.fetchone()
            if not client:
                _send(chat_id, "Email not found. Check your portal email address.")
                return

            code = _gen_code()
            expires_at = datetime.utcnow() + timedelta(minutes=10)
            cur.execute(
                """INSERT INTO telegram_verifications
                   (client_id, code, telegram_chat_id, expires_at, used)
                   VALUES (%s, %s, %s, %s, FALSE)""",
                (client["id"], code, str(chat_id), expires_at),
            )
            conn.commit()
            _send(
                chat_id,
                f"Your verification code is: {code}\n\n"
                "Enter this in your portal Settings under Telegram Notifications.\n\n"
                "Code expires in 10 minutes.",
            )
        finally:
            cur.close()
            conn.close()

    elif text.startswith("/status"):
        conn = _get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cur.execute(
                "SELECT id, name, business_name FROM clients WHERE telegram_chat_id = %s AND telegram_connected = TRUE",
                (str(chat_id),),
            )
            client = cur.fetchone()
            if not client:
                _send(chat_id, "Account not connected. Use /connect your@email.com")
                return

            cid = client["id"]
            cur.execute("SELECT COUNT(*) AS c FROM lead_uploads WHERE client_id = %s", (cid,))
            total = cur.fetchone()["c"]
            cur.execute(
                """SELECT COUNT(*) AS c FROM lead_uploads
                   WHERE client_id = %s
                   AND status IN ('Replied','INTERESTED','QUESTION','NOT NOW','MEETING READY')""",
                (cid,),
            )
            replied = cur.fetchone()["c"]
            cur.execute(
                """SELECT COUNT(*) AS c FROM lead_uploads
                   WHERE client_id = %s AND status IN ('Booked','Call Booked')""",
                (cid,),
            )
            booked = cur.fetchone()["c"]

            _send(
                chat_id,
                f"\U0001f4ca {client['business_name']} Stats\n\n"
                f"Total Leads: {total}\n"
                f"Replied: {replied}\n"
                f"Booked: {booked}\n\n"
                f"View dashboard: clientmachinery.com/portal/dashboard",
            )
        finally:
            cur.close()
            conn.close()

    elif text.startswith("/help"):
        _send(
            chat_id,
            "Client Machinery Bot Commands:\n\n"
            "/connect [email] — Link your portal account\n"
            "/status — View your current stats\n"
            "/help — Show this message",
        )
