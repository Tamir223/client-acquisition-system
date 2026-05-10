import json
import os
import secrets
import smtplib
import string
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests as http_requests
import stripe
from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash

from database import get_db, seed_sequences

stripe_bp = Blueprint("stripe_webhook", __name__)

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PARTNER_CHAT_ID = os.getenv("PARTNER_CHAT_ID")


def _gen_password(length=12):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _send_telegram(chat_id, text):
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        return
    try:
        http_requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=5,
        )
    except Exception:
        pass


def _notify_both(text):
    _send_telegram(TELEGRAM_CHAT_ID, text)
    if PARTNER_CHAT_ID and PARTNER_CHAT_ID != TELEGRAM_CHAT_ID:
        _send_telegram(PARTNER_CHAT_ID, text)


def _send_welcome_email(to_email, client_name, temp_password):
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        print("[stripe_webhook] Gmail credentials not configured — skipping welcome email")
        return

    first_name = client_name.split()[0] if client_name else "there"

    body = f"""Hi {first_name},

Your Client Machinery portal is ready. Here's everything you need to log in:

  Portal URL:  https://clientmachinery.com/portal
  Email:       {to_email}
  Password:    {temp_password}

Once you're inside:
  1. Click "Upload CSV" to drop in your existing lead list
  2. Or use "Add Manually" to add leads one at a time
  3. Your 5-touch automated follow-up sequence is already active and ready to go

Each lead you upload flows directly into the sequence — no extra setup needed.

Reply to this email if you have any questions and we'll get you sorted.

— The Client Machinery Team
support@clientmachinery.com
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Welcome to Client Machinery — Your Portal is Ready"
    msg["From"] = GMAIL_USER
    msg["To"] = to_email
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, to_email, msg.as_string())
    except Exception as e:
        print(f"[stripe_webhook] Welcome email failed: {e}")


@stripe_bp.route("/api/stripe/webhook", methods=["POST"])
def stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")

    if STRIPE_WEBHOOK_SECRET:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        except stripe.errors.SignatureVerificationError:
            return jsonify({"error": "Invalid signature"}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    else:
        try:
            event = json.loads(payload)
        except Exception:
            return jsonify({"error": "Invalid payload"}), 400

    if event.get("type") != "checkout.session.completed":
        return jsonify({"received": True}), 200

    session = event["data"]["object"]
    customer_details = session.get("customer_details") or {}
    customer_name = (customer_details.get("name") or "").strip() or "New Client"
    customer_email = (customer_details.get("email") or "").strip().lower()
    amount_total = session.get("amount_total") or 0
    amount_dollars = amount_total / 100

    if not customer_email:
        return jsonify({"received": True}), 200

    db = get_db()

    existing = db.execute(
        "SELECT id FROM clients WHERE email = ?", (customer_email,)
    ).fetchone()

    if existing:
        _notify_both(
            f"*Stripe Payment — Existing Client*\n"
            f"Name: {customer_name}\n"
            f"Email: {customer_email}\n"
            f"Amount: ${amount_dollars:,.0f}"
        )
        return jsonify({"received": True}), 200

    temp_password = _gen_password()

    db.execute(
        """INSERT INTO clients (name, business_name, email, password_hash, google_sheet_id, niche, status)
           VALUES (?, ?, ?, ?, '', '', 'active')""",
        (
            customer_name,
            customer_name,
            customer_email,
            generate_password_hash(temp_password),
        ),
    )
    db.commit()

    new_client = db.execute(
        "SELECT id FROM clients WHERE email = ?", (customer_email,)
    ).fetchone()
    client_id = new_client["id"]

    seed_sequences(db, client_id)
    db.commit()

    _send_welcome_email(customer_email, customer_name, temp_password)

    _notify_both(
        f"*New Client — Stripe Payment*\n"
        f"Name: {customer_name}\n"
        f"Email: {customer_email}\n"
        f"Amount: ${amount_dollars:,.0f}\n"
        f"Portal account + sequences created ✓"
    )

    return jsonify({"received": True}), 200
