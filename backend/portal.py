# Portal routes
import csv
import io
import json
import logging
import os
import secrets
import string
import threading
import uuid
from datetime import datetime, timedelta, timezone

import psycopg2
import resend
from flask import Blueprint, request, jsonify, g, redirect
from werkzeug.security import check_password_hash, generate_password_hash

from database import get_db, seed_sequences, add_notification, add_portal_notification, DEFAULT_SEQUENCES
from auth import require_auth
from sheets import create_client_sheet, append_lead_to_sheet, update_lead_in_sheet

logger = logging.getLogger(__name__)

_RESEND_API_KEY = os.getenv("RESEND_API_KEY")


def _send_reply_notification_email(to_email, client_name, client_business,
                                    lead_first, lead_last, classification):
    if not _RESEND_API_KEY:
        return
    resend.api_key = _RESEND_API_KEY

    lead_name = f"{lead_first} {lead_last}".strip()
    first_name = client_name.split()[0] if client_name else "there"

    badge_styles = {
        "INTERESTED":    ("background:#dcfce7;color:#16a34a;border:1px solid #bbf7d0;", "INTERESTED"),
        "MEETING READY": ("background:#dcfce7;color:#16a34a;border:1px solid #bbf7d0;", "MEETING READY"),
        "QUESTION":      ("background:#dbeafe;color:#1d4ed8;border:1px solid #bfdbfe;", "QUESTION"),
        "NOT NOW":       ("background:#fff7ed;color:#c2410c;border:1px solid #fed7aa;", "NOT NOW"),
    }
    badge_style, badge_label = badge_styles.get(
        classification,
        ("background:#f1f5f9;color:#475569;border:1px solid #e2e8f0;", classification or "Replied")
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f4f6f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9;padding:40px 16px;">
    <tr><td align="center">
      <table width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;">
        <tr>
          <td style="background:#1E3A5F;border-radius:10px 10px 0 0;padding:28px 40px;text-align:center;">
            <p style="margin:0;font-size:12px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:#7aafd4;">Client Machinery</p>
            <h1 style="margin:10px 0 0;font-size:20px;font-weight:700;color:#ffffff;">You got a reply &#128226;</h1>
          </td>
        </tr>
        <tr>
          <td style="background:#ffffff;padding:36px 40px;border-left:1px solid #e2e8f0;border-right:1px solid #e2e8f0;">
            <p style="margin:0 0 20px;font-size:16px;color:#334155;">Hi {first_name},</p>
            <p style="margin:0 0 24px;font-size:15px;color:#475569;line-height:1.7;">
              Good news &#8212; <strong style="color:#1e293b;">{lead_name}</strong> from
              <strong style="color:#1e293b;">{client_business}</strong> just replied to your
              automated follow up sequence.
            </p>
            <p style="margin:0 0 28px;">
              <span style="display:inline-block;{badge_style}border-radius:5px;font-size:12px;font-weight:700;padding:4px 12px;text-transform:uppercase;letter-spacing:0.5px;">
                {badge_label}
              </span>
            </p>
            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
              <tr>
                <td align="center">
                  <a href="https://clientmachinery.com/portal/dashboard"
                     style="display:inline-block;background:#2E75B6;color:#ffffff;text-decoration:none;font-size:15px;font-weight:600;padding:13px 32px;border-radius:7px;">
                    View in Dashboard &rarr;
                  </a>
                </td>
              </tr>
            </table>
            <p style="margin:0;font-size:14px;color:#64748b;line-height:1.6;text-align:center;">
              Log in and follow up within the hour for best results.
            </p>
          </td>
        </tr>
        <tr>
          <td style="background:#f8fafc;border:1px solid #e2e8f0;border-top:none;border-radius:0 0 10px 10px;padding:18px 40px;text-align:center;">
            <p style="margin:0;font-size:12px;color:#94a3b8;">
              Client Machinery &mdash;
              <a href="mailto:support@clientmachinery.com" style="color:#64748b;text-decoration:none;">support@clientmachinery.com</a>
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
            "subject": f"{lead_name} just replied to your follow up",
            "html": html,
        })
        logger.info(f"[portal] Reply notification sent to {to_email} for lead {lead_name}")
    except Exception as e:
        logger.error(f"[portal] Reply notification failed for {to_email}: {e}")

def _send_calendly_auto_reply(client, lead_id, lead_email, lead_first, lead_last, original_subject=None):
    """Send a Calendly booking link auto-reply to a lead via Gmail or SES."""
    if not lead_email:
        return
    calendly_link = (client.get("calendly_link") or "").strip()
    if not calendly_link:
        return

    business_name = client.get("business_name", "")
    subject = f"Re: {original_subject}" if original_subject else "Re: Your inquiry"
    body = (
        f"Thanks for getting back to us.\n\n"
        f"Here is a link to book a time that works for you:\n"
        f"{calendly_link}\n\n"
        f"Looking forward to connecting.\n\n"
        f"{business_name}"
    )

    sent = False
    if client.get("gmail_connected") and client.get("gmail_access_token"):
        try:
            from gmail_oauth import send_via_gmail
            send_via_gmail(client, lead_email, subject, body)
            sent = True
        except Exception as exc:
            logger.warning(f"[calendly] Gmail send failed, falling back to SES: {exc}")

    if not sent:
        from_addr = client.get("dedicated_email") or "support@clientmachinery.com"
        try:
            from ses_client import send_email as ses_send
            ses_send(from_addr, lead_email, subject, body)
            sent = True
        except Exception as exc:
            logger.error(f"[calendly] SES send failed: {exc}")

    if sent:
        try:
            db = get_db()
            lead_name = f"{lead_first} {lead_last}".strip()
            db.execute(
                """INSERT INTO lead_replies (client_id, lead_id, from_email, subject, snippet, source)
                   VALUES (?, ?, ?, ?, ?, 'auto_reply')""",
                (client["id"], lead_id, from_addr if not client.get("gmail_connected") else client.get("gmail_email", ""),
                 subject, f"Calendly auto-reply sent to {lead_name}")
            )
            log_activity(db, client["id"], "calendly_auto_reply",
                         f"Calendly link auto-sent to {lead_name} ({lead_email})")
            add_portal_notification(
                db, client["id"], "calendly_sent",
                "Booking link sent",
                f"Booking link sent to {lead_name}"
            )
            db.commit()
        except Exception as exc:
            logger.error(f"[calendly] Failed to log auto-reply: {exc}")


portal_bp = Blueprint("portal", __name__)

SETUP_BLOCKED_MSG = (
    "Your portal is being set up. You will receive an email within 24 hours when it is ready. "
    "Contact support@clientmachinery.com with questions."
)


def log_activity(db, client_id, event_type, description):
    db.execute(
        "INSERT INTO activity_log (client_id, event_type, description) VALUES (?, ?, ?)",
        (client_id, event_type, description)
    )


PLAN_LIMITS = {"pilot": 500, "pro": 500, "enterprise": None}


def insert_lead(db, client_id, lead):
    cur = db.execute(
        """INSERT INTO lead_uploads
           (client_id, first_name, last_name, email, phone, service_requested,
            business_name, city, lead_source)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
           RETURNING id""",
        (
            client_id,
            lead.get("first_name", "").strip(),
            lead.get("last_name", "").strip(),
            lead.get("email", "").strip(),
            lead.get("phone", "").strip(),
            lead.get("service_requested", "").strip(),
            lead.get("business_name", "").strip(),
            lead.get("city", "").strip(),
            lead.get("lead_source", "Portal"),
        )
    )
    row = cur.fetchone()
    return row["id"] if row else None


def _check_duplicate(db, client_id, email):
    if not email:
        return False
    existing = db.execute(
        "SELECT id FROM lead_uploads WHERE client_id = ? AND LOWER(email) = LOWER(?)",
        (client_id, email.strip())
    ).fetchone()
    return existing is not None


def _check_usage_limit(db, client):
    plan = (client.get("plan") or "pro").lower()
    limit = PLAN_LIMITS.get(plan)
    if limit is None:
        return None
    used = (client.get("leads_this_month") or 0)
    if used >= limit:
        return limit
    return None


def _increment_monthly_count(db, client_id, count=1):
    db.execute(
        "UPDATE clients SET leads_this_month = COALESCE(leads_this_month, 0) + ? WHERE id = ?",
        (count, client_id)
    )


def _require_admin():
    admin_key = os.environ.get("ADMIN_KEY")
    return bool(admin_key and request.headers.get("X-Admin-Key") == admin_key)


def _gen_password(length=12):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


@portal_bp.route("/api/portal/dashboard", methods=["GET"])
@require_auth
def dashboard():
    client_id = g.client["id"]
    db = get_db()

    total = db.execute(
        "SELECT COUNT(*) AS count FROM lead_uploads WHERE client_id = ?", (client_id,)
    ).fetchone()["count"]

    contacted = db.execute(
        """SELECT COUNT(*) AS count FROM lead_uploads
           WHERE client_id = ? AND status IN ('Contacted', 'Outreach Queue')""",
        (client_id,)
    ).fetchone()["count"]

    replied = db.execute(
        """SELECT COUNT(*) AS count FROM lead_uploads
           WHERE client_id = ? AND status IN ('Replied', 'INTERESTED', 'QUESTION', 'NOT NOW', 'MEETING READY')""",
        (client_id,)
    ).fetchone()["count"]

    booked = db.execute(
        """SELECT COUNT(*) AS count FROM lead_uploads
           WHERE client_id = ? AND status IN ('Booked', 'Call Booked')""",
        (client_id,)
    ).fetchone()["count"]

    activity_rows = db.execute(
        """SELECT event_type, description, created_at
           FROM activity_log WHERE client_id = ?
           ORDER BY created_at DESC LIMIT 10""",
        (client_id,)
    ).fetchall()

    recent_activity = [
        {"event_type": r["event_type"], "description": r["description"], "created_at": r["created_at"]}
        for r in activity_rows
    ]

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    emails_today = db.execute(
        """SELECT COUNT(*) AS count FROM scheduled_emails
           WHERE client_id = ? AND status = 'sent' AND sent_at >= ?""",
        (client_id, today_start)
    ).fetchone()["count"]

    active_sequences = db.execute(
        """SELECT COUNT(DISTINCT lead_id) AS count FROM scheduled_emails
           WHERE client_id = ? AND status = 'scheduled'""",
        (client_id,)
    ).fetchone()["count"]

    next_email_row = db.execute(
        """SELECT scheduled_for FROM scheduled_emails
           WHERE client_id = ? AND status = 'scheduled'
           ORDER BY scheduled_for ASC LIMIT 1""",
        (client_id,)
    ).fetchone()
    next_email = next_email_row["scheduled_for"] if next_email_row else None

    client_row = db.execute(
        "SELECT gmail_connected, gmail_email, telegram_connected, notify_replies, notify_bookings, notify_daily, notify_weekly, plan, leads_this_month FROM clients WHERE id = ?",
        (client_id,)
    ).fetchone()

    return jsonify({
        "total_leads": total,
        "contacted": contacted,
        "replied": replied,
        "booked": booked,
        "recent_activity": recent_activity,
        "emails_today": emails_today,
        "active_sequences": active_sequences,
        "next_email": next_email,
        "gmail_connected": bool(client_row["gmail_connected"]) if client_row else False,
        "gmail_email": client_row["gmail_email"] if client_row else None,
        "telegram_connected": bool(client_row["telegram_connected"]) if client_row else False,
        "notify_replies": bool(client_row["notify_replies"]) if client_row else True,
        "notify_bookings": bool(client_row["notify_bookings"]) if client_row else True,
        "notify_daily": bool(client_row["notify_daily"]) if client_row else False,
        "notify_weekly": bool(client_row["notify_weekly"]) if client_row else True,
        "plan": client_row["plan"] if client_row else "pro",
        "leads_this_month": client_row["leads_this_month"] if client_row else 0,
        "monthly_limit": PLAN_LIMITS.get((client_row["plan"] or "pro").lower()),
    }), 200


@portal_bp.route("/api/portal/upload-csv", methods=["POST"])
@require_auth
def upload_csv():
    client = g.client
    client_id = client["id"]

    sheet_id = client["google_sheet_id"] or ""
    if not sheet_id or sheet_id == "placeholder":
        return jsonify({"error": SETUP_BLOCKED_MSG}), 400

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    f = request.files["file"]
    if not f.filename or not f.filename.lower().endswith(".csv"):
        return jsonify({"error": "File must be a CSV"}), 400

    content = f.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))

    column_map = {
        "first name": "first_name",
        "last name": "last_name",
        "email": "email",
        "phone": "phone",
        "service requested": "service_requested",
    }

    leads = []
    for row in reader:
        normalized = {column_map[k.strip().lower()]: v
                      for k, v in row.items()
                      if k.strip().lower() in column_map}
        if normalized:
            leads.append(normalized)

    if not leads:
        return jsonify({"error": "No valid rows found in CSV"}), 400

    db = get_db()

    # Usage limit check
    limit_hit = _check_usage_limit(db, client)
    if limit_hit is not None:
        return jsonify({"error": f"You have reached your monthly lead limit of {limit_hit}. Upgrade your plan to upload more leads."}), 429

    duplicates = 0
    inserted_ids = []
    for lead in leads:
        email = lead.get("email", "").strip()
        if email and _check_duplicate(db, client_id, email):
            duplicates += 1
            continue
        lead_id = insert_lead(db, client_id, lead)
        if lead_id:
            inserted_ids.append((lead_id, lead))
        lead_with_meta = {**lead, "niche": client["niche"], "target_icp": client.get("target_icp", "")}
        append_lead_to_sheet(sheet_id, lead_with_meta)

    count = len(inserted_ids)
    if count > 0:
        _increment_monthly_count(db, client_id, count)

    log_activity(db, client_id, "csv_upload", f"Imported {count} leads via CSV — {f.filename}")
    add_notification(db, client_id, "csv_upload", f"Uploaded {count} leads via CSV")
    db.commit()

    # Schedule sequences in background
    def _schedule_all(inserted_ids, client_id, niche):
        from sequence_engine import SequenceEngine
        for lead_id, lead in inserted_ids:
            lead_data = {**lead, "niche": niche}
            SequenceEngine.schedule_sequence(client_id, lead_id, lead_data)

    threading.Thread(
        target=_schedule_all,
        args=(inserted_ids, client_id, client.get("niche", "")),
        daemon=True,
    ).start()

    result = {"success": True, "count": count}
    if duplicates:
        result["duplicates_skipped"] = duplicates
        result["warning"] = f"{duplicates} duplicate email(s) skipped"
    return jsonify(result), 200


@portal_bp.route("/api/portal/add-lead", methods=["POST"])
@require_auth
def add_lead():
    client = g.client
    client_id = client["id"]

    sheet_id = client["google_sheet_id"] or ""
    if not sheet_id or sheet_id == "placeholder":
        return jsonify({"error": SETUP_BLOCKED_MSG}), 400

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    db = get_db()

    # Usage limit check
    limit_hit = _check_usage_limit(db, client)
    if limit_hit is not None:
        return jsonify({"error": f"You have reached your monthly lead limit of {limit_hit}. Upgrade your plan to upload more leads."}), 429

    # Duplicate detection
    email = data.get("email", "").strip()
    if email and _check_duplicate(db, client_id, email):
        return jsonify({
            "warning": "Lead with this email already exists",
            "duplicate": True,
        }), 200

    client_row = db.execute(
        "SELECT id, name, email, business_name, google_sheet_id, niche, target_icp, status FROM clients WHERE id = ?",
        (client_id,)
    ).fetchone()

    new_lead_id = insert_lead(db, client_id, data)
    lead_with_meta = {**data, "niche": client_row["niche"], "target_icp": client_row.get("target_icp", "")}
    append_lead_to_sheet(client_row["google_sheet_id"], lead_with_meta)

    name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
    log_activity(db, client_id, "manual_add", f"Manually added lead: {name}")
    add_notification(db, client_id, "manual_add", f"New lead added: {name}")
    _increment_monthly_count(db, client_id)
    db.commit()

    # Schedule sequence in background
    if new_lead_id:
        lead_data = {
            "first_name": data.get("first_name"),
            "last_name": data.get("last_name"),
            "email": data.get("email"),
            "service_requested": data.get("service_requested"),
            "niche": client_row.get("niche", ""),
        }
        threading.Thread(
            target=lambda: __import__("sequence_engine").SequenceEngine.schedule_sequence(
                client_id, new_lead_id, lead_data
            ),
            daemon=True,
        ).start()

    return jsonify({"success": True}), 200


@portal_bp.route("/api/portal/leads", methods=["GET"])
@require_auth
def get_leads():
    client_id = g.client["id"]
    db = get_db()

    rows = db.execute(
        """SELECT id, first_name, last_name, email, phone, service_requested,
                  lead_source, status, notes, uploaded_at, lead_score, pain_point
           FROM lead_uploads WHERE client_id = ?
           ORDER BY uploaded_at DESC LIMIT 200""",
        (client_id,)
    ).fetchall()

    leads = [dict(r) for r in rows]
    return jsonify({"leads": leads}), 200


@portal_bp.route("/api/portal/leads/all", methods=["GET"])
@require_auth
def get_all_leads():
    client_id = g.client["id"]
    db = get_db()
    rows = db.execute(
        """SELECT id, first_name, last_name, email, phone, service_requested,
                  lead_source, status, notes, uploaded_at
           FROM lead_uploads WHERE client_id = ?
           ORDER BY uploaded_at DESC""",
        (client_id,)
    ).fetchall()
    return jsonify({"leads": [dict(r) for r in rows]}), 200


@portal_bp.route("/api/portal/leads/timeline", methods=["GET"])
@require_auth
def get_lead_timeline():
    client_id = g.client["id"]
    lead_id = request.args.get("lead_id")
    if not lead_id:
        return jsonify({"error": "lead_id is required"}), 400

    db = get_db()
    lead = db.execute(
        """SELECT id, first_name, last_name, email, phone, service_requested,
                  lead_source, status, notes, uploaded_at
           FROM lead_uploads WHERE id = ? AND client_id = ?""",
        (int(lead_id), client_id)
    ).fetchone()

    if not lead:
        return jsonify({"error": "Lead not found"}), 404

    lead_dict = dict(lead)

    # Calculate email schedule from uploaded_at
    try:
        added = datetime.fromisoformat(str(lead_dict["uploaded_at"]).replace(" ", "T").rstrip("Z"))
        if added.tzinfo is None:
            added = added.replace(tzinfo=timezone.utc)
    except Exception:
        added = datetime.now(timezone.utc)

    now = datetime.now(timezone.utc)
    email_days = [0, 2, 5, 10, 14]
    timeline = []

    # Upload event
    timeline.append({
        "type": "uploaded",
        "icon": "upload",
        "description": "Lead uploaded",
        "date": added.isoformat(),
        "state": "done",
    })

    # Email touch events
    for i, day in enumerate(email_days, 1):
        send_date = added + timedelta(days=day)
        state = "sent" if send_date <= now else "scheduled"
        timeline.append({
            "type": "email",
            "icon": "envelope",
            "description": f"Touch {i} — automated follow up",
            "date": send_date.isoformat(),
            "state": state,
        })

    # Status event (if not New)
    status = lead_dict.get("status") or "New"
    if status not in ("New",):
        timeline.append({
            "type": "status",
            "icon": "bell",
            "description": f"Status changed to {status}",
            "date": now.isoformat(),
            "state": "done",
        })

    timeline.sort(key=lambda e: e["date"])
    return jsonify({"lead": lead_dict, "timeline": timeline}), 200


@portal_bp.route("/api/portal/sequences", methods=["GET"])
@require_auth
def get_sequences():
    client_id = g.client["id"]
    db = get_db()

    rows = db.execute(
        """SELECT id, touch_number, send_day, subject, body, status
           FROM sequences WHERE client_id = ?
           ORDER BY touch_number ASC""",
        (client_id,)
    ).fetchall()

    return jsonify({"sequences": [dict(r) for r in rows]}), 200


@portal_bp.route("/api/portal/intake", methods=["POST"])
@require_auth
def intake():
    client_id = g.client["id"]
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    ideal_customer = (data.get("ideal_customer") or "").strip()
    if not ideal_customer:
        return jsonify({"error": "ideal_customer is required"}), 400

    db = get_db()
    db.execute(
        "UPDATE clients SET target_icp = ? WHERE id = ?",
        (ideal_customer, client_id),
    )
    log_activity(db, client_id, "intake", "Completed intake form")
    db.commit()

    return jsonify({"success": True}), 200


@portal_bp.route("/api/portal/settings", methods=["POST"])
@require_auth
def settings():
    client_id = g.client["id"]
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    target_icp = (data.get("target_icp") or "").strip()

    db = get_db()
    db.execute(
        "UPDATE clients SET target_icp = ? WHERE id = ?",
        (target_icp, client_id),
    )
    db.commit()

    return jsonify({"success": True}), 200


@portal_bp.route("/api/portal/settings/calendly", methods=["PATCH"])
@require_auth
def settings_calendly():
    client_id = g.client["id"]
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    link = (data.get("calendly_link") or "").strip()
    if link and not link.startswith("https://calendly.com/"):
        return jsonify({"error": "Calendly URL must start with https://calendly.com/"}), 400

    db = get_db()
    db.execute(
        "UPDATE clients SET calendly_link = ? WHERE id = ?",
        (link or None, client_id)
    )
    db.commit()
    return jsonify({"success": True}), 200


@portal_bp.route("/api/portal/admin/update-sheet", methods=["GET", "PUT"])
def admin_update_sheet():
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(force=True, silent=True)
    if data is None:
        return jsonify({"error": "Invalid JSON body"}), 400
    if not data.get("email") or not data.get("google_sheet_id"):
        return jsonify({"error": "email and google_sheet_id are required"}), 400

    db = get_db()
    target_icp = data.get("target_icp")
    if target_icp is not None:
        result = db.execute(
            "UPDATE clients SET google_sheet_id = ?, target_icp = ? WHERE email = ?",
            (data["google_sheet_id"], target_icp, data["email"]),
        )
    else:
        result = db.execute(
            "UPDATE clients SET google_sheet_id = ? WHERE email = ?",
            (data["google_sheet_id"], data["email"]),
        )
    db.commit()

    if result.rowcount == 0:
        return jsonify({"error": "No client found with that email"}), 404

    return jsonify({"success": True}), 200


@portal_bp.route("/api/portal/admin/check-client", methods=["GET"])
def admin_check_client():
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(force=True, silent=True)
    if not data or not data.get("email"):
        return jsonify({"error": "email is required"}), 400

    db = get_db()
    client = db.execute(
        "SELECT id, name, email, business_name, google_sheet_id, niche, target_icp, status FROM clients WHERE email = ?",
        (data["email"].strip().lower(),)
    ).fetchone()

    if not client:
        return jsonify({"error": "No client found with that email"}), 404

    return jsonify(dict(client)), 200


@portal_bp.route("/api/portal/admin/clients", methods=["GET"])
def admin_list_clients():
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 401

    db = get_db()
    rows = db.execute(
        """SELECT c.id, c.name, c.email, c.business_name, c.google_sheet_id, c.niche,
                  c.target_icp, c.status, c.created_at,
                  (SELECT COUNT(*) FROM lead_uploads l WHERE l.client_id = c.id) AS lead_count,
                  (SELECT COUNT(*) FROM notifications n WHERE n.client_id = c.id AND n.is_read = FALSE) AS unread_notifications
           FROM clients c ORDER BY c.created_at DESC"""
    ).fetchall()

    return jsonify({"clients": [dict(r) for r in rows]}), 200


@portal_bp.route("/api/portal/admin/stats", methods=["GET"])
def admin_stats():
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 401

    db = get_db()
    total_clients  = db.execute("SELECT COUNT(*) AS c FROM clients").fetchone()["c"]
    active_clients = db.execute("SELECT COUNT(*) AS c FROM clients WHERE status = 'active'").fetchone()["c"]
    sheet_connected = db.execute(
        "SELECT COUNT(*) AS c FROM clients WHERE google_sheet_id IS NOT NULL AND google_sheet_id != '' AND google_sheet_id != 'placeholder'"
    ).fetchone()["c"]
    icp_set = db.execute(
        "SELECT COUNT(*) AS c FROM clients WHERE target_icp IS NOT NULL AND target_icp != ''"
    ).fetchone()["c"]
    total_leads = db.execute("SELECT COUNT(*) AS c FROM lead_uploads").fetchone()["c"]

    return jsonify({
        "total_clients":   total_clients,
        "active_clients":  active_clients,
        "sheet_connected": sheet_connected,
        "icp_set":         icp_set,
        "total_leads":     total_leads,
    }), 200


ADMIN_EVENT_TYPES = (
    'client_created', 'sheet_created', 'sheet_triggered',
    'ready_email_sent', 'client_updated', 'admin_login',
    'system_startup', 'test_run',
)

@portal_bp.route("/api/portal/admin/activity", methods=["GET"])
def admin_activity():
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 401

    db = get_db()
    placeholders = ", ".join("?" for _ in ADMIN_EVENT_TYPES)
    rows = db.execute(
        f"""SELECT a.event_type, a.description, a.created_at,
                  c.name AS client_name, c.business_name
           FROM activity_log a
           JOIN clients c ON a.client_id = c.id
           WHERE a.event_type IN ({placeholders})
           ORDER BY a.created_at DESC LIMIT 50""",
        ADMIN_EVENT_TYPES
    ).fetchall()

    return jsonify({"activity": [dict(r) for r in rows]}), 200


@portal_bp.route("/api/portal/admin/update-client", methods=["PATCH"])
def admin_update_client():
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(force=True, silent=True)
    if not data or data.get("client_id") is None:
        return jsonify({"error": "client_id is required"}), 400

    updates = {}
    if "target_icp" in data:
        updates["target_icp"] = (data["target_icp"] or "").strip()
    if "google_sheet_id" in data:
        updates["google_sheet_id"] = (data["google_sheet_id"] or "").strip()

    if not updates:
        return jsonify({"error": "No fields to update"}), 400

    db = get_db()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [int(data["client_id"])]
    db.execute(f"UPDATE clients SET {set_clause} WHERE id = ?", values)
    db.commit()

    return jsonify({"success": True}), 200


@portal_bp.route("/api/portal/admin/create-client", methods=["POST"])
def admin_create_client():
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "Request body required"}), 400

    required = ["name", "business_name", "email", "password", "niche"]
    missing = [f for f in required if not (data.get(f) or "").strip()]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    email = data["email"].strip().lower()
    db = get_db()

    existing = db.execute("SELECT id FROM clients WHERE email = ?", (email,)).fetchone()
    if existing:
        return jsonify({"error": "A client with that email already exists"}), 409

    target_icp = (data.get("target_icp") or "").strip()
    password = data["password"]
    referral_code = str(uuid.uuid4())[:8]

    db.execute(
        """INSERT INTO clients (name, business_name, email, password_hash, google_sheet_id, niche, target_icp, status, referral_code, billing_cycle_start)
           VALUES (?, ?, ?, ?, '', ?, ?, 'active', ?, CURRENT_TIMESTAMP)""",
        (
            data["name"].strip(),
            data["business_name"].strip(),
            email,
            generate_password_hash(password),
            data["niche"].strip(),
            target_icp,
            referral_code,
        ),
    )
    db.commit()

    client_row = db.execute("SELECT id FROM clients WHERE email = ?", (email,)).fetchone()
    client_id = client_row["id"]

    seed_sequences(db, client_id)
    db.commit()

    sheet_id = create_client_sheet(data["name"].strip(), email)
    if sheet_id:
        db.execute(
            "UPDATE clients SET google_sheet_id = ? WHERE id = ?",
            (sheet_id, client_id),
        )
        db.commit()

    # Send emails in background so the response returns quickly
    from stripe_webhook import _send_welcome_email, _send_portal_ready_email
    threading.Thread(
        target=_send_welcome_email,
        args=(email, data["name"].strip(), password),
        daemon=True,
    ).start()
    if sheet_id:
        threading.Thread(
            target=_send_portal_ready_email,
            args=(email, data["name"].strip()),
            daemon=True,
        ).start()

    return jsonify({"success": True, "client_id": client_id, "sheet_id": sheet_id}), 201


@portal_bp.route("/api/portal/admin/trigger-sheet", methods=["POST"])
def admin_trigger_sheet():
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(force=True, silent=True)
    if not data or not data.get("email"):
        return jsonify({"error": "email is required"}), 400

    email = data["email"].strip().lower()
    db = get_db()

    client = db.execute(
        "SELECT id, name, email FROM clients WHERE email = ?", (email,)
    ).fetchone()
    if not client:
        return jsonify({"error": "No client found with that email"}), 404

    sheet_id = create_client_sheet(client["name"], email)
    if not sheet_id:
        return jsonify({"error": "Sheet creation failed — check GOOGLE_SERVICE_ACCOUNT_JSON"}), 500

    db.execute(
        "UPDATE clients SET google_sheet_id = ? WHERE id = ?",
        (sheet_id, client["id"]),
    )
    db.commit()

    from stripe_webhook import _send_portal_ready_email
    threading.Thread(
        target=_send_portal_ready_email,
        args=(email, client["name"]),
        daemon=True,
    ).start()

    return jsonify({"success": True, "sheet_id": sheet_id}), 200


@portal_bp.route("/api/portal/admin/send-ready-email", methods=["POST"])
def admin_send_ready_email():
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(force=True, silent=True)
    if not data or not data.get("email"):
        return jsonify({"error": "email is required"}), 400

    email = data["email"].strip().lower()
    db = get_db()

    client = db.execute(
        "SELECT name FROM clients WHERE email = ?", (email,)
    ).fetchone()
    if not client:
        return jsonify({"error": "No client found with that email"}), 404

    from stripe_webhook import _send_portal_ready_email
    threading.Thread(
        target=_send_portal_ready_email,
        args=(email, client["name"]),
        daemon=True,
    ).start()

    return jsonify({"success": True}), 200


@portal_bp.route("/api/portal/change-password", methods=["POST"])
@require_auth
def change_password():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    current_password = data.get("current_password") or ""
    new_password = data.get("new_password") or ""

    if not current_password or not new_password:
        return jsonify({"error": "Current password and new password are required"}), 400

    if len(new_password) < 8:
        return jsonify({"error": "New password must be at least 8 characters"}), 400

    client = g.client
    if not check_password_hash(client["password_hash"], current_password):
        return jsonify({"error": "Current password is incorrect"}), 401

    db = get_db()
    db.execute(
        "UPDATE clients SET password_hash = ? WHERE id = ?",
        (generate_password_hash(new_password), client["id"]),
    )
    db.commit()

    return jsonify({"success": True}), 200


@portal_bp.route("/api/portal/sequences/update", methods=["POST"])
@require_auth
def update_sequence():
    client_id = g.client["id"]
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    touch_number = data.get("touch_number")
    if not touch_number:
        return jsonify({"error": "touch_number is required"}), 400

    db = get_db()
    db.execute(
        """UPDATE sequences
           SET subject = ?, body = ?, send_day = ?, status = ?
           WHERE client_id = ? AND touch_number = ?""",
        (
            (data.get("subject") or "").strip(),
            (data.get("body") or "").strip(),
            int(data.get("send_day", 1)),
            data.get("status", "active"),
            client_id,
            int(touch_number),
        ),
    )
    db.commit()
    return jsonify({"success": True}), 200


@portal_bp.route("/api/portal/sequences/reset", methods=["POST"])
@require_auth
def reset_sequences():
    client_id = g.client["id"]
    db = get_db()
    db.execute("DELETE FROM sequences WHERE client_id = ?", (client_id,))
    seed_sequences(db, client_id)
    db.commit()
    return jsonify({"success": True}), 200


@portal_bp.route("/api/portal/notifications", methods=["GET"])
@require_auth
def get_notifications():
    client_id = g.client["id"]
    db = get_db()
    rows = db.execute(
        """SELECT id, type, title, message, read AS is_read, created_at
           FROM portal_notifications WHERE client_id = ?
           ORDER BY created_at DESC LIMIT 50""",
        (client_id,)
    ).fetchall()
    unread = db.execute(
        "SELECT COUNT(*) AS count FROM portal_notifications WHERE client_id = ? AND read = FALSE",
        (client_id,)
    ).fetchone()["count"]
    return jsonify({"notifications": [dict(r) for r in rows], "unread_count": unread}), 200


@portal_bp.route("/api/portal/notifications/read", methods=["POST"])
@require_auth
def mark_notifications_read():
    client_id = g.client["id"]
    data = request.get_json() or {}
    db = get_db()
    if data.get("all"):
        db.execute(
            "UPDATE portal_notifications SET read = TRUE WHERE client_id = ?",
            (client_id,)
        )
    elif data.get("notification_id"):
        db.execute(
            "UPDATE portal_notifications SET read = TRUE WHERE id = ? AND client_id = ?",
            (int(data["notification_id"]), client_id)
        )
    db.commit()
    return jsonify({"success": True}), 200


@portal_bp.route("/api/portal/leads/status", methods=["PATCH"])
@require_auth
def update_lead_status():
    client_id = g.client["id"]
    data = request.get_json()
    if not data or not data.get("lead_id") or not data.get("status"):
        return jsonify({"error": "lead_id and status are required"}), 400
    valid_statuses = {"New", "Contacted", "Replied", "Booked", "Closed", "Not Interested",
                      "Unsubscribed", "INTERESTED", "MEETING READY", "QUESTION", "NOT NOW"}
    reply_statuses = {"Replied", "INTERESTED", "MEETING READY", "QUESTION"}
    calendly_trigger_statuses = {"INTERESTED", "MEETING READY"}
    if data["status"] not in valid_statuses:
        return jsonify({"error": "Invalid status"}), 400
    db = get_db()
    lead = db.execute(
        "SELECT first_name, last_name, email FROM lead_uploads WHERE id = ? AND client_id = ?",
        (int(data["lead_id"]), client_id)
    ).fetchone()
    db.execute(
        "UPDATE lead_uploads SET status = ? WHERE id = ? AND client_id = ?",
        (data["status"], int(data["lead_id"]), client_id)
    )
    if lead:
        full_name = f"{lead['first_name'] or ''} {lead['last_name'] or ''}".strip()
        if data["status"] == "Booked":
            add_notification(db, client_id, "booked", f"Lead {full_name} marked as Booked")
        elif data["status"] in reply_statuses:
            add_notification(db, client_id, "replied", f"Lead {full_name} replied")
        elif data["status"] == "Unsubscribed":
            lead_email = lead.get("email", "")
            if lead_email:
                db.execute(
                    "INSERT INTO suppression_list (client_id, email, reason) VALUES (?, ?, 'unsubscribed')",
                    (client_id, lead_email.lower())
                )
            db.execute(
                "UPDATE scheduled_emails SET status='cancelled' WHERE lead_id=? AND status='scheduled'",
                (int(data["lead_id"]),)
            )
    db.commit()

    if lead and data["status"] in reply_statuses:
        client = g.client
        threading.Thread(
            target=_send_reply_notification_email,
            args=(client["email"], client["name"], client["business_name"],
                  lead["first_name"] or "", lead["last_name"] or "",
                  data["status"]),
            daemon=True,
        ).start()

    if lead and data["status"] in calendly_trigger_statuses and g.client.get("calendly_link"):
        last_subject_row = db.execute(
            """SELECT subject FROM scheduled_emails
               WHERE lead_id = ? AND status = 'sent'
               ORDER BY sent_at DESC LIMIT 1""",
            (int(data["lead_id"]),)
        ).fetchone()
        original_subject = last_subject_row["subject"] if last_subject_row else None
        client_snap = dict(g.client)
        threading.Thread(
            target=_send_calendly_auto_reply,
            args=(client_snap, int(data["lead_id"]), lead["email"] or "",
                  lead["first_name"] or "", lead["last_name"] or "", original_subject),
            daemon=True,
        ).start()

    # Return updated stats so the UI can refresh without a second round-trip
    try:
        total = db.execute(
            "SELECT COUNT(*) AS c FROM lead_uploads WHERE client_id = ?", (client_id,)
        ).fetchone()["c"]
        contacted = db.execute(
            "SELECT COUNT(*) AS c FROM lead_uploads WHERE client_id = ? AND status IN ('Contacted','Outreach Queue')",
            (client_id,)
        ).fetchone()["c"]
        replied = db.execute(
            "SELECT COUNT(*) AS c FROM lead_uploads WHERE client_id = ? AND status IN ('Replied','INTERESTED','QUESTION','NOT NOW','MEETING READY')",
            (client_id,)
        ).fetchone()["c"]
        booked = db.execute(
            "SELECT COUNT(*) AS c FROM lead_uploads WHERE client_id = ? AND status IN ('Booked','Call Booked')",
            (client_id,)
        ).fetchone()["c"]
        return jsonify({"success": True, "stats": {"total_leads": total, "contacted": contacted, "replied": replied, "booked": booked}}), 200
    except Exception:
        return jsonify({"success": True}), 200


@portal_bp.route("/api/portal/leads/delete", methods=["DELETE"])
@require_auth
def delete_lead():
    client_id = g.client["id"]
    data = request.get_json()
    if not data or not data.get("lead_id"):
        return jsonify({"error": "lead_id is required"}), 400

    lead_id = int(data["lead_id"])
    print(f"[delete] client_id from token: {client_id}")
    print(f"[delete] lead_id requested: {lead_id}")

    db = get_db()
    lead = db.execute(
        """SELECT id, first_name, last_name, email, lead_score, pain_point, ai_first_line
        FROM lead_uploads WHERE id = %s AND client_id = %s""",
        (lead_id, client_id)
    ).fetchone()

    print(f"[delete] lead found: {lead}")

    if not lead:
        return jsonify({"error": "Lead not found"}), 404

    conn = db._conn
    cur = conn.cursor()
    cur.execute("DELETE FROM email_events WHERE lead_id = %s", (lead["id"],))
    cur.execute("DELETE FROM scheduled_emails WHERE lead_id = %s", (lead["id"],))
    cur.execute("DELETE FROM lead_replies WHERE lead_id = %s", (lead["id"],))
    cur.execute("DELETE FROM lead_uploads WHERE id = %s AND client_id = %s", (lead["id"], client_id))
    conn.commit()
    cur.close()

    full_name = f"{lead['first_name'] or ''} {lead['last_name'] or ''}".strip()
    log_activity(db, client_id, "lead_deleted", f"Deleted lead: {full_name}")
    db.commit()

    sheet_id = g.client.get("google_sheet_id") or ""
    lead_email = lead["email"] or ""
    if sheet_id and sheet_id != "placeholder" and lead_email:
        try:
            update_lead_in_sheet(
                sheet_id,
                lead_email,
                lead["lead_score"] or "",
                "Deleted",
                lead["pain_point"] or "",
                lead["ai_first_line"] or "",
            )
        except Exception as e:
            logger.error(f"[portal] Failed to update sheet on lead delete: {e}")

    return jsonify({"success": True}), 200


@portal_bp.route("/api/portal/leads/notes", methods=["PATCH"])
@require_auth
def update_lead_notes():
    client_id = g.client["id"]
    data = request.get_json()
    if not data or data.get("lead_id") is None:
        return jsonify({"error": "lead_id is required"}), 400
    db = get_db()
    db.execute(
        "UPDATE lead_uploads SET notes = ? WHERE id = ? AND client_id = ?",
        ((data.get("notes") or "").strip(), int(data["lead_id"]), client_id)
    )
    db.commit()
    return jsonify({"success": True}), 200


@portal_bp.route("/api/portal/refresh-token", methods=["POST"])
@require_auth
def refresh_token():
    import datetime
    import jwt as pyjwt
    client = g.client
    secret = os.environ.get("PORTAL_JWT_SECRET", "dev-secret")
    payload = {
        "client_id": client["id"],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7),
    }
    new_token = pyjwt.encode(payload, secret, algorithm="HS256")
    if isinstance(new_token, bytes):
        new_token = new_token.decode("utf-8")
    return jsonify({"token": new_token}), 200


# ─── Gmail OAuth ────────────────────────────────────────────────────────────

@portal_bp.route("/api/portal/auth/gmail", methods=["GET"])
@require_auth
def gmail_oauth_start():
    try:
        from gmail_oauth import get_oauth_url
        url = get_oauth_url(g.client["id"])
        return jsonify({"oauth_url": url}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@portal_bp.route("/api/portal/auth/gmail/callback", methods=["GET"])
def gmail_oauth_callback():
    code = request.args.get("code")
    client_id = request.args.get("state")
    if not code or not client_id:
        return redirect("/portal/dashboard?gmail=error")
    try:
        from gmail_oauth import exchange_code
        exchange_code(code, int(client_id))
        return redirect("/portal/dashboard?gmail=connected")
    except Exception as e:
        logger.error(f"[portal] Gmail callback error: {e}")
        return redirect("/portal/dashboard?gmail=error")


@portal_bp.route("/api/portal/auth/gmail/disconnect", methods=["DELETE"])
@require_auth
def gmail_disconnect():
    db = get_db()
    db.execute(
        """UPDATE clients SET
               gmail_connected = FALSE,
               gmail_access_token = NULL,
               gmail_refresh_token = NULL,
               gmail_email = NULL
           WHERE id = ?""",
        (g.client["id"],)
    )
    add_portal_notification(
        db, g.client["id"], "gmail_disconnected",
        "Gmail disconnected",
        "Gmail disconnected — emails are paused until you reconnect"
    )
    db.commit()
    return jsonify({"success": True}), 200


# ─── Telegram ───────────────────────────────────────────────────────────────

@portal_bp.route("/api/telegram/webhook", methods=["POST"])
def telegram_webhook():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    provided = request.args.get("token", "")
    if token and provided != token:
        return jsonify({"error": "Unauthorized"}), 401
    update = request.get_json(force=True, silent=True) or {}
    try:
        from telegram_bot import handle_webhook
        handle_webhook(update)
    except Exception as e:
        logger.error(f"[portal] Telegram webhook error: {e}")
    return jsonify({"ok": True}), 200


@portal_bp.route("/api/portal/telegram/connect", methods=["POST"])
@require_auth
def telegram_connect():
    client_id = g.client["id"]
    data = request.get_json() or {}
    code = (data.get("verification_code") or "").strip()
    if not code:
        return jsonify({"error": "verification_code is required"}), 400

    db = get_db()
    now = datetime.utcnow()
    row = db.execute(
        """SELECT id, telegram_chat_id FROM telegram_verifications
           WHERE client_id = ? AND code = ? AND expires_at > ? AND used = FALSE""",
        (client_id, code, now)
    ).fetchone()

    if not row:
        return jsonify({"error": "Invalid or expired code"}), 400

    db.execute(
        "UPDATE telegram_verifications SET used = TRUE WHERE id = ?",
        (row["id"],)
    )
    db.execute(
        "UPDATE clients SET telegram_chat_id = ?, telegram_connected = TRUE WHERE id = ?",
        (row["telegram_chat_id"], client_id)
    )
    db.commit()

    from telegram_bot import _send
    _send(row["telegram_chat_id"],
        "✅ Connected! You will now receive instant alerts when leads reply.")

    return jsonify({"success": True}), 200


@portal_bp.route("/api/portal/telegram/preferences", methods=["POST"])
@require_auth
def telegram_preferences():
    client_id = g.client["id"]
    data = request.get_json() or {}
    db = get_db()
    db.execute(
        """UPDATE clients SET
               notify_replies = ?,
               notify_bookings = ?,
               notify_daily = ?,
               notify_weekly = ?
           WHERE id = ?""",
        (
            bool(data.get("notify_replies", True)),
            bool(data.get("notify_bookings", True)),
            bool(data.get("notify_daily", False)),
            bool(data.get("notify_weekly", True)),
            client_id,
        )
    )
    db.commit()
    return jsonify({"success": True}), 200


@portal_bp.route("/api/portal/telegram/disconnect", methods=["DELETE"])
@require_auth
def telegram_disconnect():
    db = get_db()
    db.execute(
        "UPDATE clients SET telegram_connected = FALSE, telegram_chat_id = NULL WHERE id = ?",
        (g.client["id"],)
    )
    db.commit()
    return jsonify({"success": True}), 200


# ─── Active Sequences ───────────────────────────────────────────────────────

@portal_bp.route("/api/portal/sequences/active", methods=["GET"])
@require_auth
def get_active_sequences():
    client_id = g.client["id"]
    db = get_db()

    rows = db.execute(
        """SELECT se.lead_id, se.touch_number, se.status, se.scheduled_for, se.sent_at,
                  l.first_name, l.last_name, l.email AS lead_email, l.status AS lead_status
           FROM scheduled_emails se
           JOIN lead_uploads l ON se.lead_id = l.id
           WHERE se.client_id = ?
           ORDER BY se.lead_id, se.touch_number""",
        (client_id,)
    ).fetchall()

    sequences_by_lead = {}
    for r in rows:
        lid = r["lead_id"]
        if lid not in sequences_by_lead:
            sequences_by_lead[lid] = {
                "lead_id": lid,
                "first_name": r["first_name"],
                "last_name": r["last_name"],
                "lead_email": r["lead_email"],
                "lead_status": r["lead_status"],
                "emails": [],
            }
        sequences_by_lead[lid]["emails"].append({
            "touch_number": r["touch_number"],
            "status": r["status"],
            "scheduled_for": r["scheduled_for"],
            "sent_at": r["sent_at"],
        })

    return jsonify({"active_sequences": list(sequences_by_lead.values())}), 200


# ─── Billing ────────────────────────────────────────────────────────────────

@portal_bp.route("/api/portal/billing", methods=["GET"])
@require_auth
def billing_portal():
    stripe_key = os.environ.get("STRIPE_SECRET_KEY")
    if not stripe_key:
        return jsonify({"error": "Billing not configured"}), 503
    try:
        import stripe
        stripe.api_key = stripe_key
        client = g.client
        customer_id = client.get("stripe_customer_id")
        if not customer_id:
            return jsonify({"error": "No billing account found"}), 404
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url="https://clientmachinery.com/portal/dashboard",
        )
        return jsonify({"portal_url": session.url}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Password Reset ─────────────────────────────────────────────────────────

@portal_bp.route("/api/portal/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "email is required"}), 400

    db = get_db()
    client = db.execute(
        "SELECT id, name FROM clients WHERE email = ? AND status = 'active'", (email,)
    ).fetchone()

    if client:
        token = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(hours=1)
        db.execute(
            "INSERT INTO password_reset_tokens (client_id, token, expires_at) VALUES (?, ?, ?)",
            (client["id"], token, expires_at)
        )
        db.commit()

        reset_url = f"https://clientmachinery.com/portal/reset-password?token={token}"
        first_name = (client["name"] or "there").split()[0]
        api_key = os.environ.get("RESEND_API_KEY")
        if api_key:
            resend.api_key = api_key
            try:
                resend.Emails.send({
                    "from": "Client Machinery <support@clientmachinery.com>",
                    "to": email,
                    "subject": "Reset your Client Machinery password",
                    "html": f"""<div style="font-family:sans-serif;max-width:480px;margin:40px auto;padding:32px;border:1px solid #e2e8f0;border-radius:10px;">
                        <h2 style="color:#1E3A5F;">Reset your password</h2>
                        <p>Hi {first_name},</p>
                        <p>Click the button below to reset your password. This link expires in 1 hour.</p>
                        <a href="{reset_url}" style="display:inline-block;background:#2E75B6;color:#fff;text-decoration:none;padding:12px 28px;border-radius:7px;font-weight:600;margin:16px 0;">
                            Reset Password
                        </a>
                        <p style="color:#64748b;font-size:13px;">If you didn't request this, you can ignore this email.</p>
                    </div>""",
                })
            except Exception as e:
                logger.error(f"[portal] Password reset email failed: {e}")

    return jsonify({"success": True}), 200


@portal_bp.route("/api/portal/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json() or {}
    token = (data.get("token") or "").strip()
    new_password = (data.get("new_password") or "")
    if not token or not new_password:
        return jsonify({"error": "token and new_password are required"}), 400
    if len(new_password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    db = get_db()
    now = datetime.utcnow()
    row = db.execute(
        "SELECT id, client_id FROM password_reset_tokens WHERE token = ? AND expires_at > ? AND used = FALSE",
        (token, now)
    ).fetchone()

    if not row:
        return jsonify({"error": "Invalid or expired reset link"}), 400

    db.execute(
        "UPDATE clients SET password_hash = ? WHERE id = ?",
        (generate_password_hash(new_password), row["client_id"])
    )
    db.execute(
        "UPDATE password_reset_tokens SET used = TRUE WHERE id = ?",
        (row["id"],)
    )
    db.commit()
    return jsonify({"success": True}), 200


# ─── Resend Webhook (email open tracking) ──────────────────────────────────

@portal_bp.route("/api/webhooks/resend", methods=["POST"])
def resend_webhook():
    data = request.get_json(force=True, silent=True) or {}
    event_type = data.get("type") or data.get("event_type", "")
    try:
        if "opened" in event_type:
            email_id = (data.get("data") or {}).get("email_id") or data.get("email_id")
            if email_id:
                db = get_db()
                se = db.execute(
                    "SELECT id, client_id, lead_id FROM scheduled_emails WHERE id::text = ?",
                    (str(email_id),)
                ).fetchone()
                if se:
                    db.execute(
                        """INSERT INTO email_events (client_id, lead_id, scheduled_email_id, event_type)
                           VALUES (?, ?, ?, 'opened')""",
                        (se["client_id"], se["lead_id"], se["id"])
                    )
                    db.commit()
    except Exception as e:
        logger.error(f"[portal] Resend webhook error: {e}")
    return jsonify({"ok": True}), 200


# ─── Referral ───────────────────────────────────────────────────────────────

@portal_bp.route("/api/portal/referral", methods=["GET"])
@require_auth
def get_referral():
    client = g.client
    db = get_db()
    ref_code = client.get("referral_code")
    if not ref_code:
        ref_code = str(uuid.uuid4())[:8]
        db.execute("UPDATE clients SET referral_code = ? WHERE id = ?", (ref_code, client["id"]))
        db.commit()
    referral_url = f"https://clientmachinery.com?ref={ref_code}"
    return jsonify({"referral_code": ref_code, "referral_url": referral_url}), 200


# ─── Reply-Detected Webhook (Make.com integration) ──────────────────────────

@portal_bp.route("/api/webhooks/reply-detected", methods=["POST"])
def reply_detected_webhook():
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(force=True, silent=True) or {}
    from_email = (data.get("from_email") or data.get("email") or "").strip().lower()
    client_id = data.get("client_id")
    snippet = (data.get("snippet") or data.get("body") or "")[:500]
    subject = (data.get("subject") or "")[:255]

    if not from_email:
        return jsonify({"error": "from_email is required"}), 400

    db = get_db()
    try:
        if client_id:
            lead = db.execute(
                """SELECT lu.id, lu.first_name, lu.last_name, lu.email,
                          c.id AS cid, c.name, c.email AS client_email, c.business_name,
                          c.telegram_connected, c.notify_replies, c.telegram_chat_id
                   FROM lead_uploads lu
                   JOIN clients c ON lu.client_id = c.id
                   WHERE lu.client_id = ? AND LOWER(lu.email) = ?
                     AND lu.status NOT IN ('Replied','INTERESTED','NOT NOW','QUESTION','MEETING READY','Unsubscribed')""",
                (int(client_id), from_email)
            ).fetchone()
        else:
            lead = db.execute(
                """SELECT lu.id, lu.first_name, lu.last_name, lu.email,
                          c.id AS cid, c.name, c.email AS client_email, c.business_name,
                          c.telegram_connected, c.notify_replies, c.telegram_chat_id
                   FROM lead_uploads lu
                   JOIN clients c ON lu.client_id = c.id
                   WHERE LOWER(lu.email) = ?
                     AND lu.status NOT IN ('Replied','INTERESTED','NOT NOW','QUESTION','MEETING READY','Unsubscribed')
                   LIMIT 1""",
                (from_email,)
            ).fetchone()

        if not lead:
            return jsonify({"error": "No matching active lead found"}), 404

        lead_id = lead["id"]
        cid = lead["cid"]
        first_name = lead["first_name"] or ""
        last_name = lead["last_name"] or ""

        db.execute(
            "UPDATE lead_uploads SET status='Replied' WHERE id = ? AND client_id = ?",
            (lead_id, cid)
        )
        db.execute(
            "UPDATE scheduled_emails SET status='cancelled' WHERE lead_id = ? AND status = 'scheduled'",
            (lead_id,)
        )
        db.execute(
            """INSERT INTO lead_replies (client_id, lead_id, from_email, snippet, subject, source)
               VALUES (?, ?, ?, ?, ?, 'make')""",
            (cid, lead_id, from_email, snippet, subject)
        )
        db.execute(
            "INSERT INTO notifications (client_id, type, message) VALUES (?, ?, ?)",
            (cid, "replied", f"{first_name} {last_name} replied to your follow up")
        )
        add_portal_notification(
            db, cid, "lead_replied",
            f"{first_name} replied",
            f"{first_name} {last_name} replied — check your notifications"
        )
        db.execute(
            "INSERT INTO activity_log (client_id, event_type, description) VALUES (?, ?, ?)",
            (cid, "reply_detected", f"Reply detected from {first_name} {last_name} via Make.com")
        )
        db.commit()

        from telegram_alerts import alert_reply
        alert_reply(
            {"business_name": lead["business_name"],
             "telegram_connected": lead["telegram_connected"],
             "notify_replies": lead["notify_replies"],
             "telegram_chat_id": lead["telegram_chat_id"]},
            first_name, last_name, from_email, snippet
        )

        api_key = os.environ.get("RESEND_API_KEY")
        if api_key and lead.get("client_email"):
            threading.Thread(
                target=_send_reply_notification_email,
                args=(lead["client_email"], lead["name"], lead["business_name"],
                      first_name, last_name, "Replied"),
                daemon=True,
            ).start()

        return jsonify({"success": True, "lead_id": lead_id}), 200

    except Exception as e:
        logger.error(f"[portal] reply-detected webhook error: {e}")
        return jsonify({"error": "Internal server error"}), 500


# ─── Inbox ───────────────────────────────────────────────────────────────────

@portal_bp.route("/api/portal/inbox", methods=["GET"])
@require_auth
def get_inbox():
    client_id = g.client["id"]
    db = get_db()
    try:
        rows = db.execute(
            """SELECT r.id, r.lead_id, r.from_email, r.snippet, r.subject,
                      r.source, r.is_read, r.created_at,
                      l.first_name, l.last_name, l.status AS lead_status
               FROM lead_replies r
               LEFT JOIN lead_uploads l ON r.lead_id = l.id
               WHERE r.client_id = ?
               ORDER BY r.created_at DESC
               LIMIT 50""",
            (client_id,)
        ).fetchall()
        return jsonify({"replies": [dict(r) for r in rows]}), 200
    except Exception as e:
        logger.error(f"[portal] get_inbox error: {e}")
        return jsonify({"error": "Failed to load inbox"}), 500


@portal_bp.route("/api/portal/inbox/unread-count", methods=["GET"])
@require_auth
def inbox_unread_count():
    client_id = g.client["id"]
    db = get_db()
    try:
        count = db.execute(
            "SELECT COUNT(*) AS c FROM lead_replies WHERE client_id = ? AND is_read = FALSE",
            (client_id,)
        ).fetchone()["c"]
        return jsonify({"unread_count": count}), 200
    except Exception as e:
        logger.error(f"[portal] inbox_unread_count error: {e}")
        return jsonify({"unread_count": 0}), 200


@portal_bp.route("/api/portal/inbox/read", methods=["POST"])
@require_auth
def mark_reply_read():
    client_id = g.client["id"]
    data = request.get_json() or {}
    db = get_db()
    try:
        if data.get("all"):
            db.execute(
                "UPDATE lead_replies SET is_read = TRUE WHERE client_id = ?",
                (client_id,)
            )
        elif data.get("reply_id"):
            db.execute(
                "UPDATE lead_replies SET is_read = TRUE WHERE id = ? AND client_id = ?",
                (int(data["reply_id"]), client_id)
            )
        db.commit()
        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error(f"[portal] mark_reply_read error: {e}")
        return jsonify({"error": "Failed to mark as read"}), 500


# ─── Lead Score (Admin) ──────────────────────────────────────────────────────

@portal_bp.route("/api/portal/leads/update-score", methods=["POST"])
def update_lead_score():
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(force=True, silent=True) or {}
    lead_id = data.get("lead_id")
    if not lead_id:
        return jsonify({"error": "lead_id is required"}), 400

    db = get_db()
    try:
        updates = {}
        if data.get("lead_score") is not None:
            updates["lead_score"] = int(data["lead_score"])
        if "pain_point" in data:
            updates["pain_point"] = (data["pain_point"] or "").strip()
        if "ai_first_line" in data:
            updates["ai_first_line"] = (data["ai_first_line"] or "").strip()

        if not updates:
            return jsonify({"error": "No fields to update"}), 400

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [int(lead_id)]
        db.execute(f"UPDATE lead_uploads SET {set_clause} WHERE id = ?", values)
        db.commit()
        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error(f"[portal] update_lead_score error: {e}")
        return jsonify({"error": "Failed to update score"}), 500


# ─── SES Webhooks ────────────────────────────────────────────────────────────
# All three routes handle SNS SubscriptionConfirmation as well as Notification.
# No admin key required — these are called directly by AWS SNS.

def _sns_confirm(payload):
    """Auto-confirm an SNS subscription by fetching the SubscribeURL."""
    import requests as _http
    url = payload.get("SubscribeURL", "")
    if url and "amazonaws.com" in url:
        try:
            _http.get(url, timeout=10)
        except Exception as exc:
            logger.error(f"[ses] SNS subscription confirm failed: {exc}")


@portal_bp.route("/api/webhooks/ses-inbound", methods=["POST"])
def ses_inbound_webhook():
    """Receive SES inbound email notifications from SNS and record replies."""
    from ses_client import parse_sns_notification, extract_inbound_fields

    msg_type = request.headers.get("x-amz-sns-message-type", "")
    raw = request.get_data()

    try:
        payload = json.loads(raw)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    if msg_type == "SubscriptionConfirmation":
        _sns_confirm(payload)
        return jsonify({"confirmed": True}), 200

    if msg_type != "Notification":
        return jsonify({"ok": True}), 200

    try:
        ses_msg = parse_sns_notification(raw)
        if (ses_msg.get("notificationType") or ses_msg.get("eventType", "")) != "Received":
            return jsonify({"ok": True}), 200

        fields = extract_inbound_fields(ses_msg)
        from_email = fields["from_email"]
        to_emails = [e.strip().lower() for e in fields["to_emails"]]
        subject = fields["subject"]
        snippet = fields["snippet"]

        db = get_db()

        # Match to_address against clients.dedicated_email
        client_row = None
        for to_addr in to_emails:
            client_row = db.execute(
                """SELECT id, name, business_name, email AS client_email,
                          telegram_connected, notify_replies, telegram_chat_id
                   FROM clients WHERE LOWER(dedicated_email) = ?""",
                (to_addr,)
            ).fetchone()
            if client_row:
                break

        if not client_row:
            return jsonify({"ok": True, "note": "No client matched"}), 200

        cid = client_row["id"]

        lead = db.execute(
            """SELECT id, first_name, last_name
               FROM lead_uploads
               WHERE client_id = ? AND LOWER(email) = ?
                 AND status NOT IN ('Replied','INTERESTED','NOT NOW','QUESTION',
                                    'MEETING READY','Unsubscribed','Bounced')""",
            (cid, from_email)
        ).fetchone()

        if not lead:
            return jsonify({"ok": True, "note": "No active lead matched"}), 200

        lead_id = lead["id"]
        first_name = lead["first_name"] or ""
        last_name = lead["last_name"] or ""

        db.execute("UPDATE lead_uploads SET status='Replied' WHERE id = ?", (lead_id,))
        db.execute(
            "UPDATE scheduled_emails SET status='cancelled' WHERE lead_id = ? AND status = 'scheduled'",
            (lead_id,)
        )
        db.execute(
            """INSERT INTO lead_replies (client_id, lead_id, from_email, snippet, subject, source)
               VALUES (?, ?, ?, ?, ?, 'ses')""",
            (cid, lead_id, from_email, snippet[:500], subject[:255])
        )
        db.execute(
            "INSERT INTO notifications (client_id, type, message) VALUES (?, ?, ?)",
            (cid, "replied", f"{first_name} {last_name} replied to your follow up")
        )
        add_portal_notification(
            db, cid, "lead_replied",
            f"{first_name} replied",
            f"{first_name} {last_name} replied — check your notifications"
        )
        db.execute(
            "INSERT INTO activity_log (client_id, event_type, description) VALUES (?, ?, ?)",
            (cid, "reply_detected", f"Reply from {first_name} {last_name} via SES inbox")
        )
        db.commit()

        from telegram_alerts import alert_reply
        alert_reply(
            {"business_name": client_row["business_name"],
             "telegram_connected": client_row["telegram_connected"],
             "notify_replies": client_row["notify_replies"],
             "telegram_chat_id": client_row["telegram_chat_id"]},
            first_name, last_name, from_email, snippet
        )

        api_key = os.environ.get("RESEND_API_KEY")
        if api_key and client_row.get("client_email"):
            threading.Thread(
                target=_send_reply_notification_email,
                args=(client_row["client_email"], client_row["name"],
                      client_row["business_name"], first_name, last_name, "Replied"),
                daemon=True,
            ).start()

        return jsonify({"success": True, "lead_id": lead_id}), 200

    except Exception as e:
        logger.error(f"[ses-inbound] webhook error: {e}")
        return jsonify({"error": "Internal error"}), 500


@portal_bp.route("/api/webhooks/ses-bounce", methods=["POST"])
def ses_bounce_webhook():
    """Receive SES bounce notifications from SNS. Suppress permanent bounces."""
    from ses_client import parse_sns_notification, extract_bounce_fields

    msg_type = request.headers.get("x-amz-sns-message-type", "")
    raw = request.get_data()

    try:
        payload = json.loads(raw)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    if msg_type == "SubscriptionConfirmation":
        _sns_confirm(payload)
        return jsonify({"confirmed": True}), 200

    if msg_type != "Notification":
        return jsonify({"ok": True}), 200

    try:
        ses_msg = parse_sns_notification(raw)
        fields = extract_bounce_fields(ses_msg)

        if fields["bounce_type"] != "Permanent":
            return jsonify({"ok": True, "note": "Transient bounce — no action"}), 200

        db = get_db()
        for email in fields["bounced_emails"]:
            email = (email or "").lower().strip()
            if not email:
                continue
            lead = db.execute(
                "SELECT id, client_id FROM lead_uploads WHERE LOWER(email) = ? LIMIT 1",
                (email,)
            ).fetchone()
            if not lead:
                continue
            lead_id, client_id = lead["id"], lead["client_id"]
            db.execute("UPDATE lead_uploads SET status='Bounced' WHERE id = ?", (lead_id,))
            db.execute(
                "UPDATE scheduled_emails SET status='cancelled' WHERE lead_id = ? AND status = 'scheduled'",
                (lead_id,)
            )
            db.execute(
                "INSERT INTO suppression_list (client_id, email, reason) VALUES (?, ?, 'bounced')",
                (client_id, email)
            )
            db.execute(
                "INSERT INTO activity_log (client_id, event_type, description) VALUES (?, ?, ?)",
                (client_id, "email_bounced",
                 f"Permanent bounce for {email} — suppressed")
            )
        db.commit()
        return jsonify({"success": True}), 200

    except Exception as e:
        logger.error(f"[ses-bounce] webhook error: {e}")
        return jsonify({"error": "Internal error"}), 500


@portal_bp.route("/api/webhooks/ses-complaint", methods=["POST"])
def ses_complaint_webhook():
    """Receive SES spam complaint notifications from SNS. Unsubscribe the lead."""
    from ses_client import parse_sns_notification, extract_complaint_fields

    msg_type = request.headers.get("x-amz-sns-message-type", "")
    raw = request.get_data()

    try:
        payload = json.loads(raw)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    if msg_type == "SubscriptionConfirmation":
        _sns_confirm(payload)
        return jsonify({"confirmed": True}), 200

    if msg_type != "Notification":
        return jsonify({"ok": True}), 200

    try:
        ses_msg = parse_sns_notification(raw)
        fields = extract_complaint_fields(ses_msg)

        db = get_db()
        for email in fields["complained_emails"]:
            email = (email or "").lower().strip()
            if not email:
                continue
            lead = db.execute(
                "SELECT id, client_id FROM lead_uploads WHERE LOWER(email) = ? LIMIT 1",
                (email,)
            ).fetchone()
            if not lead:
                continue
            lead_id, client_id = lead["id"], lead["client_id"]
            db.execute("UPDATE lead_uploads SET status='Unsubscribed' WHERE id = ?", (lead_id,))
            db.execute(
                "UPDATE scheduled_emails SET status='cancelled' WHERE lead_id = ? AND status = 'scheduled'",
                (lead_id,)
            )
            db.execute(
                "INSERT INTO suppression_list (client_id, email, reason) VALUES (?, ?, 'complaint')",
                (client_id, email)
            )
            db.execute(
                "INSERT INTO activity_log (client_id, event_type, description) VALUES (?, ?, ?)",
                (client_id, "unsubscribed",
                 f"Spam complaint from {email} — unsubscribed and suppressed")
            )
        db.commit()
        return jsonify({"success": True}), 200

    except Exception as e:
        logger.error(f"[ses-complaint] webhook error: {e}")
        return jsonify({"error": "Internal error"}), 500


# ─── Admin: Run System Tests ─────────────────────────────────────────────────

@portal_bp.route("/api/admin/run-tests", methods=["GET"])
def run_system_tests():
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 401
    try:
        from test_system import run_all_tests
        results = run_all_tests()
        return jsonify(results), 200
    except Exception as e:
        logger.error(f"[portal] run-tests error: {e}")
        return jsonify({"error": str(e)}), 500


# ─── Admin: One-time backfills ───────────────────────────────────────────────

@portal_bp.route("/api/admin/backfill-sheets", methods=["GET"])
def backfill_sheets():
    if request.headers.get("X-Admin-Key") != "casadmin2026":
        return jsonify({"error": "Unauthorized"}), 401

    from sheets import create_client_sheet

    db = get_db()
    try:
        rows = db.execute(
            "SELECT id, name, email FROM clients WHERE google_sheet_id IS NULL OR google_sheet_id = '' ORDER BY id"
        ).fetchall()

        updated = []
        for row in rows:
            client_id = row["id"]
            try:
                sheet_id = create_client_sheet(row["name"], row["email"])
                if not sheet_id:
                    continue
                db.execute(
                    "UPDATE clients SET google_sheet_id = ? WHERE id = ?",
                    (sheet_id, client_id),
                )
                db.commit()
                updated.append({
                    "client_id": client_id,
                    "sheet_id": sheet_id,
                    "sheet_url": f"https://docs.google.com/spreadsheets/d/{sheet_id}",
                })
            except Exception as e:
                logger.error(f"[backfill-sheets] client {client_id} failed: {e}")

        return jsonify({"count": len(updated), "updated": updated}), 200

    except Exception as e:
        logger.error(f"[portal] backfill-sheets error: {e}")
        return jsonify({"error": str(e)}), 500


@portal_bp.route("/api/admin/client-debug", methods=["GET"])
def client_debug():
    if request.headers.get("X-Admin-Key") != "casadmin2026":
        return jsonify({"error": "Unauthorized"}), 401

    db = get_db()
    rows = db.execute(
        "SELECT id, name, email, google_sheet_id, dedicated_email FROM clients ORDER BY id"
    ).fetchall()
    return jsonify({"clients": [dict(r) for r in rows]}), 200


@portal_bp.route("/api/admin/backfill-dedicated-emails", methods=["GET"])
def backfill_dedicated_emails():
    if request.headers.get("X-Admin-Key") != "casadmin2026":
        return jsonify({"error": "Unauthorized"}), 401

    db = get_db()
    try:
        rows = db.execute(
            "SELECT id FROM clients WHERE dedicated_email IS NULL ORDER BY id"
        ).fetchall()

        updated = []
        for row in rows:
            client_id = row["id"]
            dedicated = f"client_{client_id}@send.clientmachinery.com"
            db.execute(
                "UPDATE clients SET dedicated_email = ? WHERE id = ?",
                (dedicated, client_id),
            )
            updated.append({"client_id": client_id, "dedicated_email": dedicated})

        db.commit()
        return jsonify({"updated": updated, "count": len(updated)}), 200

    except Exception as e:
        logger.error(f"[portal] backfill-dedicated-emails error: {e}")
        return jsonify({"error": str(e)}), 500
