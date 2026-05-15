import json
import os
import secrets
import string
import threading
import time
import uuid

import psycopg2
import psycopg2.extras
import requests as http_requests
import resend
import stripe
from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash

from database import get_db, seed_sequences
from sheets import create_client_sheet, create_client_drive_folder

stripe_bp = Blueprint("stripe_webhook", __name__)

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PARTNER_CHAT_ID = os.getenv("PARTNER_CHAT_ID")

resend.api_key = RESEND_API_KEY


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
    if not RESEND_API_KEY:
        print("[stripe_webhook] RESEND_API_KEY not configured — skipping welcome email")
        return

    first_name = client_name.split()[0] if client_name else "there"

    plain_text = f"""Hi {first_name},

Your Client Machinery portal is being set up. Here's everything you need to log in once it's ready:

  Portal URL:  https://clientmachinery.com/portal
  Email:       {to_email}
  Password:    {temp_password}

You'll receive a second email when your portal is fully set up and you can start uploading leads.

While you wait, complete your intake form so we can optimize your lead scoring:
  https://clientmachinery.com/portal/intake

Reply to this email if you have any questions.

— The Client Machinery Team
support@clientmachinery.com
"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f4f6f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9;padding:40px 16px;">
    <tr><td align="center">
      <table width="100%" cellpadding="0" cellspacing="0" style="max-width:580px;">

        <tr>
          <td style="background:#1E3A5F;border-radius:10px 10px 0 0;padding:32px 40px;text-align:center;">
            <p style="margin:0;font-size:13px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:#7aafd4;">Client Machinery</p>
            <h1 style="margin:12px 0 0;font-size:22px;font-weight:700;color:#ffffff;line-height:1.3;">Welcome — Portal Setup Started</h1>
          </td>
        </tr>

        <tr>
          <td style="background:#ffffff;padding:40px 40px 32px;border-left:1px solid #e2e8f0;border-right:1px solid #e2e8f0;">
            <p style="margin:0 0 24px;font-size:16px;color:#334155;">Hi {first_name},</p>
            <p style="margin:0 0 28px;font-size:15px;color:#475569;line-height:1.7;">
              Your Client Machinery portal is being set up. Save your login credentials below — you'll receive another email when your portal is fully ready.
            </p>

            <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;margin-bottom:32px;">
              <tr>
                <td style="padding:24px 28px;">
                  <p style="margin:0 0 6px;font-size:11px;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;color:#94a3b8;">Portal URL</p>
                  <p style="margin:0 0 20px;font-size:15px;"><a href="https://clientmachinery.com/portal" style="color:#2E75B6;text-decoration:none;font-weight:600;">clientmachinery.com/portal</a></p>

                  <p style="margin:0 0 6px;font-size:11px;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;color:#94a3b8;">Email</p>
                  <p style="margin:0 0 20px;font-size:15px;color:#1e293b;font-weight:500;">{to_email}</p>

                  <p style="margin:0 0 6px;font-size:11px;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;color:#94a3b8;">Temporary Password</p>
                  <p style="margin:0;font-size:18px;font-weight:700;color:#1E3A5F;letter-spacing:2px;font-family:'Courier New',Courier,monospace;">{temp_password}</p>
                </td>
              </tr>
            </table>

            <p style="margin:0 0 16px;font-size:14px;font-weight:600;color:#1e293b;text-transform:uppercase;letter-spacing:1px;">While You Wait</p>
            <p style="margin:0 0 24px;font-size:15px;color:#475569;line-height:1.7;">
              Complete your intake form so we can optimize your lead scoring before your first leads go in.
            </p>

            <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:8px;">
              <tr>
                <td align="center">
                  <a href="https://clientmachinery.com/portal/intake"
                     style="display:inline-block;background:#2E75B6;color:#ffffff;text-decoration:none;font-size:15px;font-weight:600;padding:14px 36px;border-radius:7px;letter-spacing:0.3px;">
                    Complete Intake Form
                  </a>
                </td>
              </tr>
            </table>

            <p style="margin:32px 0 0;font-size:14px;color:#64748b;line-height:1.6;">
              Reply to this email if you have any questions.
            </p>
          </td>
        </tr>

        <tr>
          <td style="background:#f8fafc;border:1px solid #e2e8f0;border-top:none;border-radius:0 0 10px 10px;padding:24px 40px;text-align:center;">
            <p style="margin:0;font-size:13px;color:#94a3b8;">
              Client Machinery &mdash; <a href="mailto:support@clientmachinery.com" style="color:#64748b;text-decoration:none;">support@clientmachinery.com</a>
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""

    try:
        resend.Emails.send({
            "from": "Client Machinery <support@clientmachinery.com>",
            "to": to_email,
            "reply_to": "support@clientmachinery.com",
            "subject": "Welcome to Client Machinery — Your Portal is Being Set Up",
            "html": html,
            "text": plain_text,
        })
        print(f"[stripe_webhook] Welcome email sent to {to_email}")
    except Exception as e:
        print(f"[stripe_webhook] Welcome email failed: {e}")


def _send_portal_ready_email(to_email, client_name):
    if not RESEND_API_KEY:
        print("[stripe_webhook] RESEND_API_KEY not configured — skipping portal ready email")
        return

    first_name = client_name.split()[0] if client_name else "there"

    plain_text = f"""Hi {first_name},

Great news — your Client Machinery portal is fully set up and ready to go.

Getting started:
  1. Log in at https://clientmachinery.com/portal
  2. Upload your existing leads via CSV or add them manually
  3. The 5-touch follow-up sequence runs automatically from there

Complete your intake form to optimize your lead scoring:
  https://clientmachinery.com/portal/intake

Questions? Reply to this email or contact support@clientmachinery.com.

— The Client Machinery Team
"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f4f6f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9;padding:40px 16px;">
    <tr><td align="center">
      <table width="100%" cellpadding="0" cellspacing="0" style="max-width:580px;">

        <tr>
          <td style="background:#1E3A5F;border-radius:10px 10px 0 0;padding:32px 40px;text-align:center;">
            <p style="margin:0;font-size:13px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:#7aafd4;">Client Machinery</p>
            <h1 style="margin:12px 0 0;font-size:22px;font-weight:700;color:#ffffff;line-height:1.3;">Your Portal is Ready ✓</h1>
          </td>
        </tr>

        <tr>
          <td style="background:#ffffff;padding:40px 40px 32px;border-left:1px solid #e2e8f0;border-right:1px solid #e2e8f0;">
            <p style="margin:0 0 24px;font-size:16px;color:#334155;">Hi {first_name},</p>
            <p style="margin:0 0 28px;font-size:15px;color:#475569;line-height:1.7;">
              Your Client Machinery portal is fully set up. Log in and upload your leads to get the 5-touch follow-up sequence running automatically.
            </p>

            <p style="margin:0 0 16px;font-size:14px;font-weight:600;color:#1e293b;text-transform:uppercase;letter-spacing:1px;">Getting Started</p>
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="padding:0 0 16px;">
                  <table cellpadding="0" cellspacing="0">
                    <tr>
                      <td style="width:28px;height:28px;background:#1E3A5F;border-radius:50%;text-align:center;vertical-align:middle;">
                        <span style="font-size:13px;font-weight:700;color:#ffffff;">1</span>
                      </td>
                      <td style="padding-left:14px;font-size:15px;color:#475569;line-height:1.5;">
                        <strong style="color:#1e293b;">Log in</strong> at clientmachinery.com/portal using your credentials.
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
              <tr>
                <td style="padding:0 0 16px;">
                  <table cellpadding="0" cellspacing="0">
                    <tr>
                      <td style="width:28px;height:28px;background:#1E3A5F;border-radius:50%;text-align:center;vertical-align:middle;">
                        <span style="font-size:13px;font-weight:700;color:#ffffff;">2</span>
                      </td>
                      <td style="padding-left:14px;font-size:15px;color:#475569;line-height:1.5;">
                        <strong style="color:#1e293b;">Upload your leads</strong> via CSV or add them one at a time manually.
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
              <tr>
                <td style="padding:0 0 8px;">
                  <table cellpadding="0" cellspacing="0">
                    <tr>
                      <td style="width:28px;height:28px;background:#1E3A5F;border-radius:50%;text-align:center;vertical-align:middle;">
                        <span style="font-size:13px;font-weight:700;color:#ffffff;">3</span>
                      </td>
                      <td style="padding-left:14px;font-size:15px;color:#475569;line-height:1.5;">
                        <strong style="color:#1e293b;">The system takes over.</strong> Your 5-touch follow-up sequence activates automatically for every lead you upload.
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>

            <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:32px;margin-bottom:24px;">
              <tr>
                <td align="center">
                  <a href="https://clientmachinery.com/portal"
                     style="display:inline-block;background:#2E75B6;color:#ffffff;text-decoration:none;font-size:15px;font-weight:600;padding:14px 36px;border-radius:7px;letter-spacing:0.3px;">
                    Log In to Your Portal
                  </a>
                </td>
              </tr>
            </table>

            <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:8px;margin-bottom:24px;">
              <tr>
                <td style="padding:20px 24px;">
                  <p style="margin:0 0 8px;font-size:14px;font-weight:600;color:#0369a1;">Optimize Your Lead Scoring</p>
                  <p style="margin:0 0 12px;font-size:14px;color:#475569;line-height:1.6;">
                    Complete the intake form to tell us about your ideal customer — this helps our AI score and prioritize your leads automatically.
                  </p>
                  <a href="https://clientmachinery.com/portal/intake"
                     style="font-size:14px;font-weight:600;color:#2E75B6;text-decoration:none;">
                    Complete Intake Form &rarr;
                  </a>
                </td>
              </tr>
            </table>

            <p style="margin:0;font-size:14px;color:#64748b;line-height:1.6;">
              Questions? Reply to this email or contact <a href="mailto:support@clientmachinery.com" style="color:#2E75B6;">support@clientmachinery.com</a>
            </p>
          </td>
        </tr>

        <tr>
          <td style="background:#f8fafc;border:1px solid #e2e8f0;border-top:none;border-radius:0 0 10px 10px;padding:24px 40px;text-align:center;">
            <p style="margin:0;font-size:13px;color:#94a3b8;">
              Client Machinery &mdash; <a href="mailto:support@clientmachinery.com" style="color:#64748b;text-decoration:none;">support@clientmachinery.com</a>
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""

    try:
        resend.Emails.send({
            "from": "Client Machinery <support@clientmachinery.com>",
            "to": to_email,
            "reply_to": "support@clientmachinery.com",
            "subject": "Your Client Machinery portal is ready",
            "html": html,
            "text": plain_text,
        })
        print(f"[stripe_webhook] Portal ready email sent to {to_email}")
    except Exception as e:
        print(f"[stripe_webhook] Portal ready email failed: {e}")


def _setup_new_client(client_id, customer_name, customer_email, temp_password):
    """Background thread: create sheet + folder, update DB, send both emails."""
    sheet_id = create_client_sheet(customer_name, customer_email)
    create_client_drive_folder(customer_name)

    if sheet_id:
        try:
            db_url = os.getenv("DATABASE_URL")
            conn = psycopg2.connect(db_url)
            cur = conn.cursor()
            cur.execute(
                "UPDATE clients SET google_sheet_id = %s WHERE id = %s",
                (sheet_id, client_id),
            )
            conn.commit()
            cur.close()
            conn.close()
            print(f"[sheets] Created sheet for {customer_email}: {sheet_id}")
        except Exception as e:
            print(f"[stripe_webhook] Failed to update sheet_id in DB: {e}")

    _send_welcome_email(customer_email, customer_name, temp_password)

    if sheet_id:
        _send_portal_ready_email(customer_email, customer_name)


def _check_onboarding_followup(client_id, customer_name, customer_email):
    """Background thread: alert via Telegram if client hasn't completed intake after 48 hours."""
    time.sleep(172800)  # 48 hours

    try:
        db_url = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(db_url)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT target_icp FROM clients WHERE id = %s", (client_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row and not (row.get("target_icp") or "").strip():
            _notify_both(
                f"⚠️ Client hasn't completed intake\n"
                f"Name: {customer_name}\n"
                f"Email: {customer_email}\n"
                f"Paid 48 hours ago\n"
                f"target\\_icp not set\n"
                f"Action: reach out directly"
            )
    except Exception as e:
        print(f"[stripe_webhook] 48h onboarding check failed: {e}")


@stripe_bp.route("/api/stripe/webhook", methods=["POST"])
def stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")

    if STRIPE_WEBHOOK_SECRET:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        except stripe.error.SignatureVerificationError as e:
            print(f"[stripe_webhook] Signature verification failed: {e}")
            try:
                event = json.loads(payload)
            except Exception:
                return jsonify({"error": "Invalid payload"}), 400
        except Exception as e:
            print(f"[stripe_webhook] Webhook parse error: {e}")
            try:
                event = json.loads(payload)
            except Exception:
                return jsonify({"error": "Invalid payload"}), 400
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
    referral_code = str(uuid.uuid4())[:8]
    stripe_customer_id = session.get("customer") or ""

    # Check referral
    ref_code = (session.get("metadata") or {}).get("ref") or ""
    referring_client_id = None
    if ref_code:
        existing_ref = db.execute(
            "SELECT id FROM clients WHERE referral_code = ?", (ref_code,)
        ).fetchone()
        if existing_ref:
            referring_client_id = existing_ref["id"]

    db.execute(
        """INSERT INTO clients (name, business_name, email, password_hash, google_sheet_id, niche, status,
                               referral_code, stripe_customer_id, billing_cycle_start, referred_by)
           VALUES (?, ?, ?, ?, '', '', 'active', ?, ?, CURRENT_TIMESTAMP, ?)""",
        (
            customer_name,
            customer_name,
            customer_email,
            generate_password_hash(temp_password),
            referral_code,
            stripe_customer_id,
            referring_client_id,
        ),
    )
    db.commit()

    new_client = db.execute(
        "SELECT id FROM clients WHERE email = ?", (customer_email,)
    ).fetchone()
    client_id = new_client["id"]

    # Credit referring client with 1 free month
    if referring_client_id:
        db.execute(
            "UPDATE clients SET free_months = COALESCE(free_months, 0) + 1 WHERE id = ?",
            (referring_client_id,)
        )
        db.commit()

    seed_sequences(db, client_id)
    db.commit()

    _notify_both(
        f"*New Client — Stripe Payment*\n"
        f"Name: {customer_name}\n"
        f"Email: {customer_email}\n"
        f"Amount: ${amount_dollars:,.0f}\n"
        f"Portal account + sequences created ✓\n"
        f"Sheet creation in progress…"
    )

    threading.Thread(
        target=_setup_new_client,
        args=(client_id, customer_name, customer_email, temp_password),
        daemon=True,
    ).start()

    threading.Thread(
        target=_check_onboarding_followup,
        args=(client_id, customer_name, customer_email),
        daemon=True,
    ).start()

    return jsonify({"received": True}), 200
