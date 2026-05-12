# Portal routes
import csv
import io
import logging
import os
import secrets
import string
import threading

import psycopg2
from flask import Blueprint, request, jsonify, g
from werkzeug.security import check_password_hash, generate_password_hash

from database import get_db, seed_sequences, add_notification, DEFAULT_SEQUENCES
from auth import require_auth
from sheets import create_client_sheet, append_lead_to_sheet

logger = logging.getLogger(__name__)

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


def insert_lead(db, client_id, lead):
    db.execute(
        """INSERT INTO lead_uploads
           (client_id, first_name, last_name, email, phone, service_requested, lead_source)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            client_id,
            lead.get("first_name", "").strip(),
            lead.get("last_name", "").strip(),
            lead.get("email", "").strip(),
            lead.get("phone", "").strip(),
            lead.get("service_requested", "").strip(),
            lead.get("lead_source", "Portal"),
        )
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
        "SELECT COUNT(*) AS count FROM activity_log WHERE client_id = ? AND event_type = 'contacted'",
        (client_id,)
    ).fetchone()["count"]

    replied = db.execute(
        "SELECT COUNT(*) AS count FROM activity_log WHERE client_id = ? AND event_type = 'replied'",
        (client_id,)
    ).fetchone()["count"]

    booked = db.execute(
        "SELECT COUNT(*) AS count FROM activity_log WHERE client_id = ? AND event_type = 'booked'",
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

    return jsonify({
        "total_leads": total,
        "contacted": contacted,
        "replied": replied,
        "booked": booked,
        "recent_activity": recent_activity,
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
    for lead in leads:
        insert_lead(db, client_id, lead)
        lead_with_meta = {**lead, "niche": client["niche"], "target_icp": client["target_icp"]}
        append_lead_to_sheet(sheet_id, lead_with_meta)

    log_activity(db, client_id, "csv_upload", f"Uploaded {len(leads)} leads via CSV")
    add_notification(db, client_id, "csv_upload", f"Uploaded {len(leads)} leads via CSV")
    db.commit()

    return jsonify({"success": True, "count": len(leads)}), 200


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
    client_row = db.execute(
        "SELECT id, name, email, business_name, google_sheet_id, niche, target_icp, status FROM clients WHERE id = ?",
        (client_id,)
    ).fetchone()

    insert_lead(db, client_id, data)
    lead_with_meta = {**data, "niche": client_row["niche"], "target_icp": client_row["target_icp"]}
    append_lead_to_sheet(client_row["google_sheet_id"], lead_with_meta)

    name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
    log_activity(db, client_id, "manual_add", f"Manually added lead: {name}")
    add_notification(db, client_id, "manual_add", f"New lead added: {name}")
    db.commit()

    return jsonify({"success": True}), 200


@portal_bp.route("/api/portal/leads", methods=["GET"])
@require_auth
def get_leads():
    client_id = g.client["id"]
    db = get_db()

    rows = db.execute(
        """SELECT id, first_name, last_name, email, phone, service_requested,
                  lead_source, status, notes, uploaded_at
           FROM lead_uploads WHERE client_id = ?
           ORDER BY uploaded_at DESC LIMIT 200""",
        (client_id,)
    ).fetchall()

    leads = [dict(r) for r in rows]
    return jsonify({"leads": leads}), 200


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
        """SELECT id, name, email, business_name, google_sheet_id, niche, target_icp, status, created_at
           FROM clients ORDER BY created_at DESC"""
    ).fetchall()

    return jsonify({"clients": [dict(r) for r in rows]}), 200


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

    db.execute(
        """INSERT INTO clients (name, business_name, email, password_hash, google_sheet_id, niche, target_icp, status)
           VALUES (?, ?, ?, ?, '', ?, ?, 'active')""",
        (
            data["name"].strip(),
            data["business_name"].strip(),
            email,
            generate_password_hash(password),
            data["niche"].strip(),
            target_icp,
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
        """SELECT id, type, message, is_read, created_at
           FROM notifications WHERE client_id = ?
           ORDER BY created_at DESC LIMIT 20""",
        (client_id,)
    ).fetchall()
    unread = db.execute(
        "SELECT COUNT(*) AS count FROM notifications WHERE client_id = ? AND is_read = FALSE",
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
            "UPDATE notifications SET is_read = TRUE WHERE client_id = ?",
            (client_id,)
        )
    elif data.get("notification_id"):
        db.execute(
            "UPDATE notifications SET is_read = TRUE WHERE id = ? AND client_id = ?",
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
    valid_statuses = {"New", "Contacted", "Replied", "Booked", "Closed"}
    if data["status"] not in valid_statuses:
        return jsonify({"error": "Invalid status"}), 400
    db = get_db()
    db.execute(
        "UPDATE lead_uploads SET status = ? WHERE id = ? AND client_id = ?",
        (data["status"], int(data["lead_id"]), client_id)
    )
    db.commit()
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
