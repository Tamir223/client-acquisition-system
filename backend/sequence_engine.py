import logging
import os
import re
import threading
from datetime import datetime, timedelta

import psycopg2
import psycopg2.extras
import requests as _requests
import resend

from telegram_alerts import alert_partners, alert_client, alert_reply, alert_email_sent

logger = logging.getLogger(__name__)

TOUCH_DAYS = {1: 0, 2: 2, 3: 5, 4: 10, 5: 14}

PLAN_LIMITS = {
    "pilot": 500,
    "pro": 500,
    "enterprise": None,
}

# Tamir's own email must be excluded from client-inbox reply scanning
# to avoid conflicts with Make.com's reply detection on the same inbox.
_SYSTEM_EMAILS = {"tamir@clientmachinery.com", "support@clientmachinery.com"}


def _get_conn():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


def _send_reply_email_to_client(client, first_name, last_name, lead_email, snippet):
    lead_name = f"{first_name} {last_name}".strip()
    client_first = (client.get("name") or "there").split()[0]
    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="font-family:-apple-system,sans-serif;background:#f4f6f9;padding:40px 16px;">
  <div style="max-width:560px;margin:0 auto;background:#fff;border-radius:10px;overflow:hidden;">
    <div style="background:#1E3A5F;padding:28px 40px;text-align:center;">
      <h1 style="margin:0;color:#fff;font-size:20px;">{first_name} just replied &#128226;</h1>
    </div>
    <div style="padding:36px 40px;">
      <p style="font-size:16px;color:#334155;">Hi {client_first},</p>
      <p style="font-size:15px;color:#475569;line-height:1.7;">
        <strong>{lead_name}</strong> just replied to your automated follow-up sequence.
        The sequence has been stopped automatically.
      </p>
      <p style="font-size:14px;color:#64748b;font-style:italic;">"{snippet}"</p>
      <div style="text-align:center;margin:28px 0;">
        <a href="https://clientmachinery.com/portal/dashboard"
           style="background:#2E75B6;color:#fff;text-decoration:none;padding:13px 32px;border-radius:7px;font-weight:600;">
          View in Dashboard &rarr;
        </a>
      </div>
    </div>
  </div>
</body></html>"""
    try:
        resend.Emails.send({
            "from": "Client Machinery <support@clientmachinery.com>",
            "to": client["email"],
            "subject": f"{first_name} just replied to your follow up",
            "html": html,
        })
    except Exception as e:
        logger.error(f"[sequence] reply email to client failed: {e}")


_TOUCH1_TEMPLATE = """{first_line}

Most owners I talk to say the same thing — someone reaches out, life gets busy, and the follow up never happens.

By the time they circle back the lead is gone.

We fix that with automated follow up that runs in the background while you focus on the work.

Worth a 15 minute conversation?

clientmachinery.com/portal/dashboard

{business_name}"""


def score_lead(lead_data, client):
    """
    Call Claude Haiku to score and personalize a lead.
    Returns dict with lead_score, reason, pain_point, ai_first_line — or None on failure.
    """
    api_key = os.getenv("CLAUDE_API_KEY")
    if not api_key:
        logger.debug("[scoring] CLAUDE_API_KEY not set — skipping AI scoring")
        return None

    business_name = (lead_data.get("business_name") or "").strip()
    is_individual = business_name.lower() in ("", "n/a", "na")

    if is_individual:
        first_name = lead_data.get("first_name", "")
        last_name = lead_data.get("last_name", "")
        prompt = (
            "Lead Type: Individual Consumer\n"
            f"Name: {first_name} {last_name}\n"
            f"Service Needed: {lead_data.get('service_requested', '')}\n"
            f"City: {lead_data.get('city', '')}\n\n"
            "Score this individual lead 1-10 based on how likely they are to convert "
            "given their service need and location. Generate a pain point and personalized "
            "first line addressing them as an individual, not a business owner.\n\n"
            "Return ONLY this format:\n"
            "SCORE: [number]\n"
            "REASON: [one sentence]\n"
            "PAIN: [one sentence describing their specific pain point as an individual]\n"
            "FIRSTLINE: [one sentence opener under 25 words, personal and specific to their "
            "situation, does not start with Most/I/We]"
        )
    else:
        prompt = (
            "Score this lead 1-10 on how likely they need automated lead follow up software.\n\n"
            f"Business Name: {business_name}\n"
            f"Service They Need: {lead_data.get('service_requested', '')}\n"
            f"City: {lead_data.get('city', '')}\n"
            f"Client Niche: {client.get('niche', '')}\n"
            f"Target ICP: {client.get('target_icp', '')}\n\n"
            "High score (8-10): local or regional business that gets inbound leads and "
            "likely has a manual follow up process.\n"
            "Low score (1-3): large enterprise, no inbound leads, or already has "
            "sophisticated automation.\n\n"
            "Return ONLY this format:\n"
            "SCORE: [number]\n"
            "REASON: [one sentence]\n"
            "PAIN: [one sentence describing their specific pain point]\n"
            "FIRSTLINE: [one sentence cold email opener under 25 words, specific to their "
            "business, does not start with Most/I/We]"
        )

    try:
        resp = _requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 200,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=20,
        )
        resp.raise_for_status()
        text = resp.json()["content"][0]["text"].strip()

        score, reason, pain, firstline = None, "", "", ""
        for line in text.splitlines():
            line = line.strip()
            if line.upper().startswith("SCORE:"):
                try:
                    score = int(re.search(r"\d+", line.split(":", 1)[1]).group())
                except Exception:
                    pass
            elif line.upper().startswith("REASON:"):
                reason = line.split(":", 1)[1].strip()
            elif line.upper().startswith("PAIN:"):
                pain = line.split(":", 1)[1].strip()
            elif line.upper().startswith("FIRSTLINE:"):
                firstline = line.split(":", 1)[1].strip()

        if score is None:
            logger.warning("[scoring] Could not parse SCORE from Claude response")
            return None

        score = max(1, min(10, score))
        return {"lead_score": score, "reason": reason, "pain_point": pain, "ai_first_line": firstline}

    except Exception as e:
        logger.error(f"[scoring] score_lead failed: {e}")
        return None


def _apply_scoring(client_id, lead_id, lead_data):
    """
    Background thread: score the lead, update DB, update Touch 1 email, update sheet.
    Uses its own DB connection — safe to run after schedule_sequence() commits.
    """
    conn = None
    try:
        conn = _get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("SELECT * FROM clients WHERE id = %s", (client_id,))
        client = cur.fetchone()
        if not client:
            return

        result = score_lead(lead_data, dict(client))
        if not result:
            return

        score = result["lead_score"]
        pain = result["pain_point"]
        firstline = result["ai_first_line"]
        first_name = lead_data.get("first_name", "")
        last_name = lead_data.get("last_name", "")

        # Save score to lead record
        cur.execute(
            """UPDATE lead_uploads
               SET lead_score = %s, pain_point = %s, ai_first_line = %s
               WHERE id = %s""",
            (score, pain, firstline, lead_id),
        )

        # Rewrite Touch 1 body with AI first line
        touch1_body = _TOUCH1_TEMPLATE.format(
            first_line=firstline,
            business_name=client.get("business_name", ""),
        )
        cur.execute(
            """UPDATE scheduled_emails SET body = %s
               WHERE lead_id = %s AND touch_number = 1 AND status = 'scheduled'""",
            (touch1_body, lead_id),
        )

        conn.commit()
        logger.info(
            f"[scoring] Lead {lead_id} scored {score}/10 — "
            f"{first_name} {last_name}"
        )

        # Update Google Sheet with score, status, pain point, first line
        sheet_id = (client.get("google_sheet_id") or "").strip()
        if sheet_id and sheet_id != "placeholder":
            lead_email = (lead_data.get("email") or "").strip()
            sheet_status = "Outreach Queue" if score >= 7 else "Low Score"
            try:
                from sheets import update_lead_in_sheet
                update_lead_in_sheet(sheet_id, lead_email, score, sheet_status, pain, firstline)
            except Exception as e:
                logger.error(f"[scoring] Sheet update failed for lead {lead_id}: {e}")

    except Exception as e:
        logger.error(f"[scoring] _apply_scoring error for lead {lead_id}: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


class SequenceEngine:

    @staticmethod
    def schedule_sequence(client_id, lead_id, lead_data):
        conn = _get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            email = (lead_data.get("email") or "").lower().strip()
            if email:
                cur.execute(
                    "SELECT id FROM suppression_list WHERE client_id = %s AND email = %s",
                    (client_id, email),
                )
                if cur.fetchone():
                    logger.info(f"[sequence] {email} suppressed — skipping sequence")
                    return 0

            cur.execute(
                """SELECT touch_number, send_day, subject, body
                   FROM sequences WHERE client_id = %s AND status = 'active'
                   ORDER BY touch_number""",
                (client_id,),
            )
            sequences = cur.fetchall()
            if not sequences:
                return 0

            now = datetime.utcnow()
            first_name = lead_data.get("first_name", "")
            last_name = lead_data.get("last_name", "")
            business_name = lead_data.get("service_requested", "")
            industry = lead_data.get("niche", "")

            count = 0
            for seq in sequences:
                touch_num = seq["touch_number"]
                days = TOUCH_DAYS.get(touch_num, touch_num * 2)
                send_time = now + timedelta(days=days)

                subject = seq["subject"]
                body = seq["body"]
                for placeholder, value in [
                    ("{{First Name}}", first_name),
                    ("{{Last Name}}", last_name),
                    ("{{Business Name}}", business_name),
                    ("{{Industry}}", industry),
                ]:
                    subject = subject.replace(placeholder, value)
                    body = body.replace(placeholder, value)

                cur.execute(
                    """INSERT INTO scheduled_emails
                       (client_id, lead_id, touch_number, scheduled_for, subject, body, status)
                       VALUES (%s, %s, %s, %s, %s, %s, 'scheduled')""",
                    (client_id, lead_id, touch_num, send_time, subject, body),
                )
                count += 1

            cur.execute(
                """INSERT INTO activity_log (client_id, event_type, description)
                   VALUES (%s, %s, %s)""",
                (client_id, "sequence_scheduled",
                 f"Sequence scheduled for {first_name} {last_name}"),
            )
            conn.commit()

            if count > 0 and lead_id and lead_id > 0:
                threading.Thread(
                    target=_apply_scoring,
                    args=(client_id, lead_id, lead_data),
                    daemon=True,
                ).start()

            return count
        except Exception as e:
            logger.error(f"[sequence] schedule_sequence error: {e}")
            conn.rollback()
            return 0
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def send_due_emails():
        resend_api_key = os.getenv("RESEND_API_KEY")
        if resend_api_key:
            resend.api_key = resend_api_key

        conn = _get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            now = datetime.utcnow()
            cur.execute(
                """SELECT se.*,
                          l.first_name, l.last_name, l.email AS lead_email, l.status AS lead_status,
                          c.email AS client_email, c.name AS client_name, c.business_name,
                          c.gmail_connected, c.gmail_email,
                          c.gmail_access_token, c.gmail_refresh_token,
                          c.telegram_connected, c.telegram_chat_id, c.notify_replies,
                          c.dedicated_email
                   FROM scheduled_emails se
                   JOIN lead_uploads l ON se.lead_id = l.id
                   JOIN clients c ON se.client_id = c.id
                   WHERE se.status = 'scheduled'
                     AND se.scheduled_for <= %s
                   ORDER BY se.scheduled_for ASC
                   LIMIT 50""",
                (now,),
            )
            due = cur.fetchall()

            replied_statuses = (
                "Replied", "INTERESTED", "NOT NOW", "QUESTION",
                "MEETING READY", "UNSUBSCRIBE", "Unsubscribed",
            )

            for em in due:
                lead_id = em["lead_id"]

                if em["lead_status"] in replied_statuses:
                    cur.execute(
                        "UPDATE scheduled_emails SET status='cancelled' WHERE lead_id=%s AND status='scheduled'",
                        (lead_id,),
                    )
                    conn.commit()
                    continue

                body = (
                    em["body"]
                    + "\n\n---\n"
                    + f"Sent on behalf of {em['business_name']}\n"
                    + "To unsubscribe reply UNSUBSCRIBE\n"
                    + "Powered by Client Machinery"
                )

                sent = False
                error_msg = None

                if em["gmail_connected"]:
                    try:
                        from gmail_oauth import send_via_gmail
                        client_obj = {
                            "id": em["client_id"],
                            "email": em["client_email"],
                            "gmail_email": em["gmail_email"],
                            "gmail_access_token": em["gmail_access_token"],
                            "gmail_refresh_token": em["gmail_refresh_token"],
                        }
                        send_via_gmail(client_obj, em["lead_email"], em["subject"], body)
                        sent = True
                    except Exception as e:
                        logger.warning(f"[sequence] Gmail failed ({em['id']}): {e} — trying Resend")

                if not sent and em.get("dedicated_email"):
                    try:
                        from ses_client import send_email as _ses_send
                        from_display = f"{em['business_name']} <{em['dedicated_email']}>"
                        _ses_send(
                            from_addr=from_display,
                            to_addr=em["lead_email"],
                            subject=em["subject"],
                            body=body,
                            reply_to=em["dedicated_email"],
                        )
                        sent = True
                    except Exception as e:
                        logger.warning(f"[sequence] SES failed ({em['id']}): {e} — trying Resend")

                if not sent and resend_api_key:
                    try:
                        footer = ""
                        if not em["gmail_connected"] and not em.get("dedicated_email"):
                            footer = "\n\n[Sent via Client Machinery — connect your Gmail in portal settings to send from your own address]"
                        resend.Emails.send({
                            "from": "Client Machinery <support@clientmachinery.com>",
                            "to": em["lead_email"],
                            "subject": em["subject"],
                            "text": body + footer,
                        })
                        sent = True
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"[sequence] Resend failed ({em['id']}): {e}")

                if sent:
                    cur.execute(
                        "UPDATE scheduled_emails SET status='sent', sent_at=%s WHERE id=%s",
                        (now, em["id"]),
                    )
                    cur.execute(
                        "UPDATE lead_uploads SET status='Contacted' WHERE id=%s AND status='New'",
                        (lead_id,),
                    )
                    cur.execute(
                        """INSERT INTO activity_log (client_id, event_type, description)
                           VALUES (%s, %s, %s)""",
                        (em["client_id"], "email_sent",
                         f"Email {em['touch_number']} sent to {em['first_name']} {em['last_name']}"),
                    )
                    cur.execute(
                        """INSERT INTO notifications (client_id, type, message)
                           VALUES (%s, %s, %s)""",
                        (em["client_id"], "email_sent",
                         f"\U0001f4e7 Email {em['touch_number']} sent to {em['first_name']} {em['last_name']}"),
                    )
                    cur.execute(
                        """INSERT INTO email_events (client_id, lead_id, scheduled_email_id, event_type)
                           VALUES (%s, %s, %s, %s)""",
                        (em["client_id"], lead_id, em["id"], "sent"),
                    )

                    from_addr = em.get("gmail_email") or em.get("dedicated_email") or "support@clientmachinery.com"
                    alert_email_sent(
                        {
                            "business_name": em["business_name"],
                            "telegram_connected": em["telegram_connected"],
                            "notify_replies": em["notify_replies"],
                            "telegram_chat_id": em["telegram_chat_id"],
                        },
                        em["first_name"], em["last_name"],
                        em["lead_email"], em["touch_number"], from_addr,
                    )
                else:
                    cur.execute(
                        "UPDATE scheduled_emails SET status='error', error_message=%s WHERE id=%s",
                        (error_msg, em["id"]),
                    )

                conn.commit()

        except Exception as e:
            logger.error(f"[sequence] send_due_emails error: {e}")
            conn.rollback()
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def cancel_sequence(lead_id):
        conn = _get_conn()
        cur = conn.cursor()
        try:
            cur.execute(
                "UPDATE scheduled_emails SET status='cancelled' WHERE lead_id=%s AND status='scheduled'",
                (lead_id,),
            )
            conn.commit()
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def check_gmail_replies():
        resend_api_key = os.getenv("RESEND_API_KEY")
        if resend_api_key:
            resend.api_key = resend_api_key

        conn = _get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cur.execute(
                """SELECT id, name, email, business_name,
                          gmail_access_token, gmail_refresh_token, gmail_email,
                          telegram_connected, telegram_chat_id, notify_replies
                   FROM clients WHERE gmail_connected = TRUE"""
            )
            clients = cur.fetchall()

            for client in clients:
                # Skip system inboxes — Make.com handles those via /api/webhooks/reply-detected
                if (client.get("gmail_email") or "").lower() in _SYSTEM_EMAILS:
                    continue
                if (client.get("email") or "").lower() in _SYSTEM_EMAILS:
                    continue

                try:
                    from gmail_oauth import get_unread_replies
                    replies = get_unread_replies(client)

                    for reply in replies:
                        raw_from = reply.get("from", "")
                        match = re.search(r"<(.+?)>", raw_from)
                        from_email = match.group(1) if match else raw_from.strip()
                        from_email = from_email.lower()

                        cur.execute(
                            """SELECT id, first_name, last_name, email
                               FROM lead_uploads
                               WHERE client_id = %s
                                 AND LOWER(email) = %s
                                 AND status NOT IN (
                                   'Replied','INTERESTED','NOT NOW','QUESTION',
                                   'MEETING READY','UNSUBSCRIBE','Unsubscribed'
                                 )""",
                            (client["id"], from_email),
                        )
                        lead = cur.fetchone()
                        if not lead:
                            continue

                        lead_id = lead["id"]
                        first_name = lead["first_name"] or ""
                        last_name = lead["last_name"] or ""
                        snippet = (reply.get("snippet") or "")[:200]

                        cur.execute(
                            "UPDATE lead_uploads SET status='Replied' WHERE id=%s",
                            (lead_id,),
                        )
                        cur.execute(
                            "UPDATE scheduled_emails SET status='cancelled' WHERE lead_id=%s AND status='scheduled'",
                            (lead_id,),
                        )
                        cur.execute(
                            """INSERT INTO lead_replies (client_id, lead_id, from_email, snippet, subject, source)
                               VALUES (%s, %s, %s, %s, %s, 'gmail')
                               ON CONFLICT DO NOTHING""",
                            (client["id"], lead_id, from_email, snippet,
                             reply.get("subject", "")),
                        )
                        cur.execute(
                            """INSERT INTO notifications (client_id, type, message)
                               VALUES (%s, %s, %s)""",
                            (client["id"], "replied",
                             f"{first_name} {last_name} replied to your follow up"),
                        )
                        cur.execute(
                            """INSERT INTO activity_log (client_id, event_type, description)
                               VALUES (%s, %s, %s)""",
                            (client["id"], "reply_detected",
                             f"Reply detected from {first_name} {last_name}"),
                        )

                        alert_reply(dict(client), first_name, last_name, from_email, snippet)

                        if resend_api_key:
                            _send_reply_email_to_client(
                                client, first_name, last_name, from_email, snippet
                            )

                        conn.commit()

                except Exception as e:
                    logger.error(f"[sequence] check_gmail_replies client {client['id']}: {e}")

        except Exception as e:
            logger.error(f"[sequence] check_gmail_replies error: {e}")
        finally:
            cur.close()
            conn.close()
