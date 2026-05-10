import os
import re
import jwt
from datetime import datetime, timezone, timedelta
from functools import wraps
from flask import Blueprint, request, jsonify, g
from werkzeug.security import check_password_hash, generate_password_hash
from database import get_db

auth_bp = Blueprint("auth", __name__)

JWT_SECRET = os.getenv("PORTAL_JWT_SECRET", "dev-secret-change-in-production-key")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 7


def create_token(client_id):
    payload = {
        "sub": str(client_id),
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRY_DAYS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Authorization required"}), 401
        token = auth_header[7:]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        db = get_db()
        client = db.execute(
            "SELECT * FROM clients WHERE id = ? AND status = 'active'",
            (int(payload["sub"]),)
        ).fetchone()
        if not client:
            return jsonify({"error": "Client not found"}), 401

        g.client = client
        return f(*args, **kwargs)
    return decorated


@auth_bp.route("/api/portal/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    db = get_db()
    client = db.execute(
        "SELECT * FROM clients WHERE email = ? AND status = 'active'",
        (email,)
    ).fetchone()

    if not client or not check_password_hash(client["password_hash"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    token = create_token(client["id"])
    return jsonify({
        "token": token,
        "client_name": client["name"],
        "business_name": client["business_name"],
    }), 200


@auth_bp.route("/api/portal/logout", methods=["POST"])
def logout():
    return jsonify({"success": True}), 200


@auth_bp.route("/api/portal/me", methods=["GET"])
@require_auth
def me():
    c = g.client
    return jsonify({
        "id": c["id"],
        "name": c["name"],
        "business_name": c["business_name"],
        "email": c["email"],
        "niche": c["niche"],
    }), 200


# SETUP_ROUTE_START
@auth_bp.route("/api/portal/setup", methods=["POST"])
def setup():
    db = get_db()
    if db.execute("SELECT COUNT(*) AS count FROM clients").fetchone()["count"] > 0:
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    required = ["name", "business_name", "email", "password", "niche", "google_sheet_id"]
    missing = [f for f in required if not (data.get(f) or "").strip()]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    db.execute(
        "INSERT INTO clients (name, business_name, email, password_hash, google_sheet_id, niche) VALUES (?, ?, ?, ?, ?, ?)",
        (
            data["name"].strip(),
            data["business_name"].strip(),
            data["email"].strip().lower(),
            generate_password_hash(data["password"]),
            data["google_sheet_id"].strip(),
            data["niche"].strip(),
        ),
    )
    db.commit()

    path = os.path.abspath(__file__)
    with open(path, "r") as fh:
        source = fh.read()
    source = re.sub(
        r"\n\n# SETUP_ROUTE_START\n.*?# SETUP_ROUTE_END\n",
        "",
        source,
        flags=re.DOTALL,
    )
    with open(path, "w") as fh:
        fh.write(source)

    return jsonify({"success": True, "message": "Client created. Setup route removed."}), 201
# SETUP_ROUTE_END
