import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import anthropic

load_dotenv()

app = Flask(__name__)
CORS(app)

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
        },
    }
    requests.post("https://connect.mailerlite.com/api/subscribers", json=payload, headers=headers, timeout=10)


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

    message = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}],
    )

    text  = message.content[0].text.strip()
    score = None

    try:
        score = int(text.split("|")[0].replace("SCORE:", "").strip())
    except (ValueError, IndexError):
        pass

    return score, text


# ─── Routes ────────────────────────────────────────────────────────────────────

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

    send_telegram(TELEGRAM_CHAT_ID, alert)
    if PARTNER_CHAT_ID and PARTNER_CHAT_ID != TELEGRAM_CHAT_ID:
        send_telegram(PARTNER_CHAT_ID, alert)

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


if __name__ == "__main__":
    app.run(debug=True, port=5000)
