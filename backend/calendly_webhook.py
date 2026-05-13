import hashlib
import hmac
import json
import os
from datetime import datetime, timezone

import anthropic
import requests as http_requests
from flask import Blueprint, jsonify, request

from database import get_db

calendly_bp = Blueprint("calendly_webhook", __name__)

CALENDLY_WEBHOOK_SECRET = os.getenv("CALENDLY_WEBHOOK_SECRET")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PARTNER_CHAT_ID = os.getenv("PARTNER_CHAT_ID")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

claude = anthropic.Anthropic(api_key=CLAUDE_API_KEY) if CLAUDE_API_KEY else None


def _send_telegram(chat_id, text):
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        return
    try:
        http_requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
    except Exception:
        pass


def _notify_both(text):
    _send_telegram(TELEGRAM_CHAT_ID, text)
    if PARTNER_CHAT_ID and PARTNER_CHAT_ID != TELEGRAM_CHAT_ID:
        _send_telegram(PARTNER_CHAT_ID, text)


def _verify_signature(raw_body: bytes, sig_header: str) -> bool:
    if not CALENDLY_WEBHOOK_SECRET:
        return True
    try:
        parts = dict(p.split("=", 1) for p in sig_header.split(","))
        timestamp = parts.get("t", "")
        v1 = parts.get("v1", "")
    except Exception:
        return False
    message = f"{timestamp}.{raw_body.decode('utf-8')}"
    expected = hmac.new(
        CALENDLY_WEBHOOK_SECRET.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, v1)


def _parse_intake_answers(questions_and_answers: list) -> dict:
    """Map Calendly intake Q&A to structured fields by keyword matching."""
    data = {}
    for qa in (questions_and_answers or []):
        q = qa.get("question", "").lower()
        a = (qa.get("answer") or "").strip()
        if not a:
            continue
        if "business" in q and "name" in q:
            data.setdefault("business_name", a)
        elif any(k in q for k in ["industry", "niche", "type of business", "sector"]):
            data.setdefault("industry", a)
        elif "city" in q:
            data.setdefault("city", a)
        elif "state" in q and "business" not in q:
            data.setdefault("state", a)
        elif any(k in q for k in ["employee", "team size", "how many people", "staff"]):
            data.setdefault("employees", a)
        elif "website" in q:
            data.setdefault("website", a)
        elif any(k in q for k in ["pain", "challenge", "struggle", "problem", "biggest"]):
            data.setdefault("pain_point", a)
        elif "keyword" in q:
            data.setdefault("keywords", a)
    return data


def _lookup_lead(email: str) -> dict | None:
    """Return the most recent lead_uploads row for this email, or None."""
    try:
        db = get_db()
        row = db.execute(
            "SELECT * FROM lead_uploads WHERE email = ? ORDER BY uploaded_at DESC LIMIT 1",
            (email,),
        ).fetchone()
        return dict(row) if row else None
    except Exception:
        return None


def _lookup_client(email: str) -> dict | None:
    """Return the clients row for this email, or None."""
    try:
        db = get_db()
        row = db.execute(
            "SELECT * FROM clients WHERE email = ?",
            (email,),
        ).fetchone()
        return dict(row) if row else None
    except Exception:
        return None


def _generate_brief(prospect: dict) -> dict | None:
    """Call Claude and return a structured dict with objections, roi, talking_points, close."""
    if not claude:
        return None

    name = prospect.get("name", "the prospect")
    business = prospect.get("business_name", "their business")
    industry = prospect.get("industry", "local service business")
    location_parts = [x for x in [prospect.get("city"), prospect.get("state")] if x]
    location = ", ".join(location_parts) if location_parts else "their area"
    employees = prospect.get("employees", "unknown number of")
    lead_score = prospect.get("lead_score", "N/A")
    pain_point = prospect.get("pain_point", "not yet specified")

    prompt = (
        f"You are preparing Donald for a discovery call with a potential client.\n\n"
        f"Prospect:\n"
        f"  Name: {name}\n"
        f"  Business: {business}\n"
        f"  Industry: {industry}\n"
        f"  Location: {location}\n"
        f"  Employees: {employees}\n"
        f"  Lead Score: {lead_score}\n"
        f"  Pain Point: {pain_point}\n\n"
        f"Return ONLY a valid JSON object with exactly these keys — no markdown, no extra text:\n"
        f"{{\n"
        f'  "objections": [\n'
        f'    {{"objection": "...", "rebuttal": "one sentence rebuttal"}},\n'
        f'    {{"objection": "...", "rebuttal": "one sentence rebuttal"}},\n'
        f'    {{"objection": "...", "rebuttal": "one sentence rebuttal"}}\n'
        f"  ],\n"
        f'  "roi_calculation": "3-4 sentences. Show: avg job value for {industry}, '
        f"leads lost per month for a {employees}-person shop, revenue lost per month, "
        f'ROI at $1,500/month if we recover 15%% of lost leads. Show the actual math.",\n'
        f'  "talking_points": ["point 1 specific to {business}", "point 2", "point 3"],\n'
        f'  "suggested_close": "One paragraph close script. Reference {business} by name and their pain point."\n'
        f"}}\n\n"
        f"Be specific to {industry} in {location}. Keep every field concise. Return only valid JSON."
    )

    try:
        message = claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=700,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text.strip()
        # Strip any accidental markdown fences
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception as e:
        print(f"[calendly_webhook] Claude/parse error: {e}")
        return None


def _format_telegram(prospect: dict, brief: dict | None, call_time: str) -> str:
    name = prospect.get("name", "Unknown")
    business = prospect.get("business_name", "Unknown")
    industry = prospect.get("industry", "Unknown")
    location_parts = [x for x in [prospect.get("city"), prospect.get("state")] if x]
    location = ", ".join(location_parts) if location_parts else "Unknown"
    employees = prospect.get("employees", "Unknown")
    lead_score = prospect.get("lead_score", "N/A")
    pain_point = prospect.get("pain_point", "Not specified")
    email = prospect.get("email", "")

    # Escape underscores in dynamic values to avoid Markdown parse errors
    def esc(s):
        return str(s).replace("_", "\\_")

    lines = [
        "📞 *Discovery Call Brief*\n",
        f"👤 {esc(name)} — {esc(business)}",
        f"🏢 {esc(industry)} | {esc(location)}",
        f"👥 {esc(employees)} employees",
        f"⭐ Lead Score: {esc(lead_score)}\n",
        f"💡 *Pain Point:*\n{esc(pain_point)}\n",
    ]

    if brief:
        # Objections
        objections = brief.get("objections") or []
        lines.append("⚠️ *Top Objections:*")
        for i, obj in enumerate(objections[:3], 1):
            o = esc(obj.get("objection", ""))
            r = esc(obj.get("rebuttal", ""))
            lines.append(f"{i}. {o} → {r}")
        lines.append("")

        # ROI
        roi = esc(brief.get("roi_calculation", ""))
        lines.append(f"💰 *ROI Calculation:*\n{roi}\n")

        # Talking points
        tps = brief.get("talking_points") or []
        lines.append("🎯 *Talking Points:*")
        for i, tp in enumerate(tps[:3], 1):
            lines.append(f"{i}. {esc(tp)}")
        lines.append("")

        # Close
        close = esc(brief.get("suggested_close", ""))
        lines.append(f"✅ *Suggested Close:*\n{close}\n")
    else:
        lines.append("_(Brief generation unavailable — Claude not configured)_\n")

    lines.append(f"📅 Call Time: {esc(call_time)}")
    lines.append(f"📧 {esc(email)}")

    return "\n".join(lines)


@calendly_bp.route("/api/calendly/webhook", methods=["POST"])
def handle_calendly_webhook():
    raw_body = request.get_data()
    sig_header = request.headers.get("Calendly-Webhook-Signature", "")

    if not _verify_signature(raw_body, sig_header):
        print("[calendly_webhook] Signature verification failed")
        return jsonify({"error": "Invalid signature"}), 401

    try:
        data = json.loads(raw_body)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    # Only handle new bookings
    if data.get("event") != "invitee.created":
        return jsonify({"received": True}), 200

    payload = data.get("payload", {})
    invitee = payload.get("invitee", {})
    event = payload.get("event", {})

    invitee_name = (invitee.get("name") or "Unknown").strip()
    invitee_email = (invitee.get("email") or "").strip().lower()
    event_start_time = event.get("start_time", "")
    questions_and_answers = invitee.get("questions_and_answers", [])

    # Parse Calendly intake form answers
    intake = _parse_intake_answers(questions_and_answers)

    # Build prospect dict — Calendly data takes precedence over DB data
    prospect = {"name": invitee_name, "email": invitee_email, **intake}

    # Enrich from lead_uploads if we have a matching record
    if invitee_email:
        db_lead = _lookup_lead(invitee_email)
        if db_lead:
            for field in ("business_name", "industry", "city", "state", "employees", "pain_point"):
                if not prospect.get(field) and db_lead.get(field):
                    prospect[field] = db_lead[field]
            # Fallback: use service_requested as industry hint
            if not prospect.get("industry") and db_lead.get("service_requested"):
                prospect["industry"] = db_lead["service_requested"]

    # Format call time
    try:
        dt = datetime.fromisoformat(event_start_time.replace("Z", "+00:00"))
        call_time = dt.strftime("%B %d, %Y at %I:%M %p UTC")
    except Exception:
        call_time = event_start_time or "TBD"

    # Generate AI brief
    brief = _generate_brief(prospect)

    # Send to both partners
    msg = _format_telegram(prospect, brief, call_time)
    _notify_both(msg)

    # Log to activity_log only when the booker is an existing client
    if invitee_email:
        client = _lookup_client(invitee_email)
        if client:
            try:
                db = get_db()
                db.execute(
                    "INSERT INTO activity_log (client_id, event_type, description) VALUES (?, ?, ?)",
                    (client["id"], "discovery_call_booked", f"Discovery call booked with {invitee_name}"),
                )
                db.commit()
            except Exception as e:
                print(f"[calendly_webhook] Activity log error: {e}")

    print(f"[calendly_webhook] Processed booking for {invitee_name} <{invitee_email}>")
    return jsonify({"received": True}), 200
