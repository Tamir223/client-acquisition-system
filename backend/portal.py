import csv
import io
import os
from flask import Blueprint, request, jsonify, g
from werkzeug.security import check_password_hash, generate_password_hash
from database import get_db
from auth import require_auth
from sheets import append_lead_to_sheet

portal_bp = Blueprint("portal", __name__)


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
        lead_with_meta = {**lead, "niche": client["niche"]}
        append_lead_to_sheet(client["google_sheet_id"], lead_with_meta)

    log_activity(db, client_id, "csv_upload", f"Uploaded {len(leads)} leads via CSV")
    db.commit()

    return jsonify({"success": True, "count": len(leads)}), 200


@portal_bp.route("/api/portal/add-lead", methods=["POST"])
@require_auth
def add_lead():
    client = g.client
    client_id = client["id"]
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body required"}), 400

    db = get_db()
    insert_lead(db, client_id, data)
    lead_with_meta = {**data, "niche": client["niche"]}
    append_lead_to_sheet(client["google_sheet_id"], lead_with_meta)

    name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
    log_activity(db, client_id, "manual_add", f"Manually added lead: {name}")
    db.commit()

    return jsonify({"success": True}), 200


@portal_bp.route("/api/portal/leads", methods=["GET"])
@require_auth
def get_leads():
    client_id = g.client["id"]
    db = get_db()

    rows = db.execute(
        """SELECT id, first_name, last_name, email, phone, service_requested, lead_source, uploaded_at
           FROM lead_uploads WHERE client_id = ?
           ORDER BY uploaded_at DESC LIMIT 100""",
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
        """SELECT touch_number, send_day, subject, status
           FROM sequences WHERE client_id = ?
           ORDER BY touch_number ASC""",
        (client_id,)
    ).fetchall()

    return jsonify({"sequences": [dict(r) for r in rows]}), 200


@portal_bp.route("/api/portal/admin/update-sheet", methods=["GET", "PUT"])
def admin_update_sheet():
    admin_key = os.environ.get("ADMIN_KEY")
    if not admin_key or request.headers.get("X-Admin-Key") != admin_key:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    if not data or not data.get("email") or not data.get("google_sheet_id"):
        return jsonify({"error": "email and google_sheet_id are required"}), 400

    db = get_db()
    result = db.execute(
        "UPDATE clients SET google_sheet_id = ? WHERE email = ?",
        (data["google_sheet_id"], data["email"]),
    )
    db.commit()

    if result.rowcount == 0:
        return jsonify({"error": "No client found with that email"}), 404

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
