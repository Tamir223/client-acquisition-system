import os
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import anthropic
from auth import auth_bp
from portal import portal_bp
from stripe_webhook import stripe_bp
from database import init_db, close_db
from extensions import limiter

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

ROOT_DIR = os.path.join(os.path.dirname(__file__), "..")
PORTAL_DIR = os.path.join(ROOT_DIR, "portal")

app = Flask(__name__, static_folder=ROOT_DIR, static_url_path="")
CORS(app)
limiter.init_app(app)

app.register_blueprint(auth_bp)
app.register_blueprint(portal_bp)
app.register_blueprint(stripe_bp)
app.teardown_appcontext(close_db)


@app.errorhandler(429)
def rate_limit_exceeded(e):
    return jsonify({
        "error": "Too many attempts. Please wait 15 minutes and try again."
    }), 429

with app.app_context():
    init_db()

MAILERLITE_API_KEY  = os.getenv("MAILERLITE_API_KEY")
TELEGRAM_BOT_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID    = os.getenv("TELEGRAM_CHAT_ID")
PARTNER_CHAT_ID     = os.getenv("PARTNER_CHAT_ID")
CLAUDE_API_KEY      = os.getenv("CLAUDE_API_KEY")

claude = anthropic.Anthropic(api_key=CLAUDE_API_KEY) if CLAUDE_API_KEY else None


# ─── Helpers ───────────────────────────────────────────────────────────────────

def send_telegram(chat_id, text):
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=5)


def notify_both(text):
    send_telegram(TELEGRAM_CHAT_ID, text)
    if PARTNER_CHAT_ID and PARTNER_CHAT_ID != TELEGRAM_CHAT_ID:
        send_telegram(PARTNER_CHAT_ID, text)


MAILERLITE_GROUP_ID = "186460124187985711"  # "CAS Leads" group


def add_to_mailerlite(data):
    if not MAILERLITE_API_KEY:
        return
    headers = {
        "Authorization": f"Bearer {MAILERLITE_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "email": data["email"],
        "fields": {
            "name":      data.get("first_name", ""),
            "last_name": data.get("last_name", ""),
            "company":   data.get("company", ""),
            "phone":     data.get("phone", ""),
        },
        "groups": [MAILERLITE_GROUP_ID],
    }
    resp = requests.post("https://connect.mailerlite.com/api/subscribers", json=payload, headers=headers, timeout=10)
    resp.raise_for_status()


def score_lead(data):
    if not claude:
        return None, "Claude API not configured"

    prompt = (
        f"Score this lead 1-10 based on fit for local service business ICP.\n"
        f"Lead: {data.get('first_name')} {data.get('last_name')}, "
        f"Company: {data.get('company')}, "
        f"Niche: {data.get('niche') or 'unknown'}.\n"
        f"ICP: local service business, $10k-$50k monthly revenue, 1-50 employees.\n"
        f"Return format exactly: SCORE: X | REASON: one sentence"
    )

    try:
        message = claude.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        return None, f"Claude error: {e}"

    text  = message.content[0].text.strip()
    score = None

    try:
        score = int(text.split("|")[0].replace("SCORE:", "").strip())
    except (ValueError, IndexError):
        pass

    return score, text


# ─── Routes ────────────────────────────────────────────────────────────────────

@app.route("/portal")
@app.route("/portal/")
def portal_login():
    return send_from_directory(PORTAL_DIR, "index.html")


@app.route("/portal/dashboard")
def portal_dashboard():
    return send_from_directory(PORTAL_DIR, "dashboard.html")


@app.route("/portal/admin")
def portal_admin():
    return send_from_directory(PORTAL_DIR, "admin.html")


@app.route("/portal/intake")
def portal_intake():
    return send_from_directory(PORTAL_DIR, "intake.html")


@app.route("/portal/css/<path:filename>")
def portal_css(filename):
    return send_from_directory(os.path.join(PORTAL_DIR, "css"), filename)


@app.route("/")
def index():
    return send_from_directory(ROOT_DIR, "index.html")


@app.route("/sitemap.xml")
def sitemap():
    return send_from_directory(ROOT_DIR, "sitemap.xml", mimetype="application/xml")


@app.route("/robots.txt")
def robots():
    return send_from_directory(ROOT_DIR, "robots.txt", mimetype="text/plain")


@app.route("/privacy")
def privacy():
    return send_from_directory(ROOT_DIR, "privacy-policy.html")


@app.route("/terms")
def terms():
    return send_from_directory(ROOT_DIR, "terms.html")


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "Client Acquisition System"})


@app.route("/api/lead", methods=["POST"])
def capture_lead():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body required"}), 400

    for field in ["first_name", "last_name", "email", "company"]:
        if not data.get(field):
            return jsonify({"error": f"{field} is required"}), 400

    add_to_mailerlite(data)

    score, score_detail = score_lead(data)

    alert = (
        f"*New Lead — CAS*\n"
        f"Name: {data['first_name']} {data['last_name']}\n"
        f"Company: {data['company']}\n"
        f"Niche: {data.get('niche') or 'N/A'}\n"
        f"Email: {data['email']}\n"
        f"AI Score: {score if score is not None else 'N/A'}\n"
        f"Detail: {score_detail}"
    )

    notify_both(alert)

    return jsonify({"success": True, "score": score}), 200


@app.route("/api/classify-reply", methods=["POST"])
def classify_reply():
    data = request.get_json()
    reply_text = (data or {}).get("reply")

    if not reply_text:
        return jsonify({"error": "reply is required"}), 400

    if not claude:
        return jsonify({"error": "Claude API not configured"}), 503

    prompt = (
        "Classify this email reply into exactly one of these categories:\n"
        "INTERESTED / NOT NOW / QUESTION / UNSUBSCRIBE / MEETING READY\n\n"
        f"Reply: {reply_text}\n\n"
        "Return the category name only. No explanation."
    )

    message = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=20,
        messages=[{"role": "user", "content": prompt}],
    )

    classification = message.content[0].text.strip().upper()
    return jsonify({"classification": classification}), 200


@app.route("/api/score-lead", methods=["POST"])
def api_score_lead():
    data = request.get_json()

    if not data or not data.get("company"):
        return jsonify({"error": "company is required"}), 400

    score, detail = score_lead(data)
    return jsonify({"score": score, "detail": detail}), 200


@app.route("/api/reply", methods=["POST"])
def reply_received():
    data = request.get_json()
    for field in ["email", "reply_text"]:
        if not (data or {}).get(field):
            return jsonify({"error": f"{field} is required"}), 400

    preview = data["reply_text"][:200] + ("…" if len(data["reply_text"]) > 200 else "")
    alert = (
        f"*Reply Received — CAS*\n"
        f"From: {data['email']}\n"
        f"Preview: {preview}"
    )
    notify_both(alert)
    return jsonify({"success": True}), 200


@app.route("/api/booking", methods=["POST"])
def call_booked():
    data = request.get_json()
    for field in ["name", "email", "time"]:
        if not (data or {}).get(field):
            return jsonify({"error": f"{field} is required"}), 400

    alert = (
        f"*Call Booked — CAS*\n"
        f"Name: {data['name']}\n"
        f"Email: {data['email']}\n"
        f"Time: {data['time']}"
    )
    notify_both(alert)
    return jsonify({"success": True}), 200


@app.route("/api/payment", methods=["POST"])
def payment_received():
    data = request.get_json()
    for field in ["name", "email", "amount"]:
        if not (data or {}).get(field):
            return jsonify({"error": f"{field} is required"}), 400

    alert = (
        f"*Payment Received — CAS*\n"
        f"Name: {data['name']}\n"
        f"Email: {data['email']}\n"
        f"Amount: ${data['amount']}"
    )
    notify_both(alert)
    return jsonify({"success": True}), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)
