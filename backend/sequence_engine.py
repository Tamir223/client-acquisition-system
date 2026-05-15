import logging
import os
import re
from datetime import datetime, timedelta

import psycopg2
import psycopg2.extras
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
                          c.telegram_connected, c.telegram_chat_id, c.notify_replies
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

                if not sent and resend_api_key:
                    try:
                        footer = ""
                        if not em["gmail_connected"]:
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

                    from_addr = em.get("gmail_email") or "support@clientmachinery.com"
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
