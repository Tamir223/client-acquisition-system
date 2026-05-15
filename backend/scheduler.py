import logging
import os
from datetime import datetime, timedelta, timezone

import psycopg2
import psycopg2.extras
import resend

logger = logging.getLogger(__name__)


def _weekly_email_html(first_name, business_name, uploaded, contacted, replied, booked):
    if booked > 0:
        motivation = f"You booked {booked} call{'s' if booked != 1 else ''} this week. Great work."
    elif replied > 0:
        motivation = f"You got {replied} repl{'ies' if replied != 1 else 'y'} this week. Follow up fast."
    elif uploaded > 0:
        motivation = f"Your system followed up on {uploaded} lead{'s' if uploaded != 1 else ''} this week."
    else:
        motivation = "Upload your first leads to get the system running."

    def stat_box(label, value, color):
        return f"""<td style="width:25%;padding:0 6px;text-align:center;">
          <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:16px 8px;">
            <div style="font-size:28px;font-weight:800;color:{color};line-height:1;">{value}</div>
            <div style="font-size:11px;font-weight:600;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;margin-top:6px;">{label}</div>
          </div>
        </td>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f4f6f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9;padding:40px 16px;">
    <tr><td align="center">
      <table width="100%" cellpadding="0" cellspacing="0" style="max-width:580px;">
        <tr>
          <td style="background:#1E3A5F;border-radius:10px 10px 0 0;padding:32px 40px;text-align:center;">
            <p style="margin:0;font-size:12px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:#7aafd4;">Client Machinery</p>
            <h1 style="margin:12px 0 0;font-size:24px;font-weight:700;color:#ffffff;">Your Week in Review</h1>
          </td>
        </tr>
        <tr>
          <td style="background:#ffffff;padding:36px 40px;border-left:1px solid #e2e8f0;border-right:1px solid #e2e8f0;">
            <p style="margin:0 0 28px;font-size:16px;color:#334155;">Hi {first_name},</p>
            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:32px;">
              <tr>
                {stat_box("Uploaded", uploaded, "#1E3A5F")}
                {stat_box("Contacted", contacted, "#2E75B6")}
                {stat_box("Replied", replied, "#f59e0b")}
                {stat_box("Booked", booked, "#10b981")}
              </tr>
            </table>
            <div style="background:#f0f9ff;border-left:4px solid #2E75B6;border-radius:0 6px 6px 0;padding:16px 20px;margin-bottom:28px;">
              <p style="margin:0;font-size:15px;color:#1e293b;line-height:1.6;">{motivation}</p>
            </div>
            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
              <tr>
                <td align="center">
                  <a href="https://clientmachinery.com/portal/dashboard"
                     style="display:inline-block;background:#2E75B6;color:#ffffff;text-decoration:none;font-size:15px;font-weight:600;padding:14px 36px;border-radius:7px;">
                    View Your Dashboard &rarr;
                  </a>
                </td>
              </tr>
            </table>
            <p style="margin:0;font-size:14px;color:#64748b;line-height:1.6;">
              Reply to this email or contact
              <a href="mailto:support@clientmachinery.com" style="color:#2E75B6;">support@clientmachinery.com</a>
            </p>
          </td>
        </tr>
        <tr>
          <td style="background:#f8fafc;border:1px solid #e2e8f0;border-top:none;border-radius:0 0 10px 10px;padding:20px 40px;text-align:center;">
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


def weekly_summary_job():
    api_key = os.getenv("RESEND_API_KEY")
    db_url = os.getenv("DATABASE_URL")
    if not api_key or not db_url:
        logger.warning("[scheduler] RESEND_API_KEY or DATABASE_URL not set — skipping weekly summary")
        return

    resend.api_key = api_key
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("SELECT id, name, business_name, email, telegram_connected, telegram_chat_id, notify_weekly FROM clients WHERE status = 'active'")
        clients = cur.fetchall()

        for client in clients:
            cid = client["id"]
            cur.execute("SELECT COUNT(*) AS c FROM lead_uploads WHERE client_id = %s AND uploaded_at >= %s", (cid, week_ago))
            uploaded = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) AS c FROM lead_uploads WHERE client_id = %s AND uploaded_at >= %s AND status IN ('Contacted','Outreach Queue')", (cid, week_ago))
            contacted = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) AS c FROM lead_uploads WHERE client_id = %s AND uploaded_at >= %s AND status IN ('Replied','INTERESTED','QUESTION','NOT NOW','MEETING READY')", (cid, week_ago))
            replied = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) AS c FROM lead_uploads WHERE client_id = %s AND uploaded_at >= %s AND status IN ('Booked','Call Booked')", (cid, week_ago))
            booked = cur.fetchone()["c"]

            first_name = client["name"].split()[0] if client["name"] else "there"
            html = _weekly_email_html(first_name, client["business_name"], uploaded, contacted, replied, booked)

            try:
                resend.Emails.send({
                    "from": "Client Machinery <support@clientmachinery.com>",
                    "to": client["email"],
                    "reply_to": "support@clientmachinery.com",
                    "subject": f"Your Weekly Lead Summary — {client['business_name']}",
                    "html": html,
                })
                logger.info(f"[scheduler] Weekly summary sent to {client['email']}")
            except Exception as e:
                logger.error(f"[scheduler] Failed to send to {client['email']}: {e}")

            # Telegram weekly summary
            if client.get("telegram_connected") and client.get("notify_weekly") and client.get("telegram_chat_id"):
                _send_telegram(
                    client["telegram_chat_id"],
                    f"\U0001f4ca Weekly Summary — {client['business_name']}\n\n"
                    f"Uploaded: {uploaded}\n"
                    f"Contacted: {contacted}\n"
                    f"Replied: {replied}\n"
                    f"Booked: {booked}\n\n"
                    f"View dashboard: clientmachinery.com/portal/dashboard",
                )

        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"[scheduler] weekly_summary_job error: {e}")


def check_incomplete_onboarding():
    db_url = os.getenv("DATABASE_URL")
    partner_chat_id = os.getenv("PARTNER_CHAT_ID")
    if not db_url:
        return
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cutoff = datetime.utcnow() - timedelta(hours=48)
        cur.execute(
            """SELECT id, name, email FROM clients
               WHERE created_at <= %s
                 AND (target_icp IS NULL OR target_icp = '')
                 AND status = 'active'""",
            (cutoff,),
        )
        clients = cur.fetchall()
        for client in clients:
            if partner_chat_id:
                _send_telegram(
                    partner_chat_id,
                    f"⚠️ Client hasn't completed intake\n"
                    f"Name: {client['name']}\n"
                    f"Email: {client['email']}\n"
                    f"Action: reach out directly",
                )
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"[scheduler] check_incomplete_onboarding error: {e}")


def reset_monthly_lead_counts():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        cur.execute("UPDATE clients SET leads_this_month = 0, billing_cycle_start = CURRENT_TIMESTAMP")
        conn.commit()
        cur.close()
        conn.close()
        logger.info("[scheduler] Monthly lead counts reset")
    except Exception as e:
        logger.error(f"[scheduler] reset_monthly_lead_counts error: {e}")


def _send_telegram(chat_id, text):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or not chat_id:
        return
    import requests
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=5,
        )
    except Exception as e:
        logger.error(f"[scheduler] Telegram send failed: {e}")


def start_scheduler():
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        from sequence_engine import SequenceEngine
    except ImportError as e:
        logger.warning(f"[scheduler] import failed — {e}")
        return None

    scheduler = BackgroundScheduler(timezone="America/New_York")

    scheduler.add_job(
        func=SequenceEngine.send_due_emails,
        trigger="interval",
        minutes=15,
        id="send_emails",
        replace_existing=True,
        misfire_grace_time=300,
    )
    scheduler.add_job(
        func=SequenceEngine.check_gmail_replies,
        trigger="interval",
        minutes=30,
        id="check_replies",
        replace_existing=True,
        misfire_grace_time=300,
    )
    scheduler.add_job(
        func=weekly_summary_job,
        trigger=CronTrigger(day_of_week="mon", hour=8, minute=0),
        id="weekly_summary",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        func=check_incomplete_onboarding,
        trigger="interval",
        hours=1,
        id="onboarding_check",
        replace_existing=True,
        misfire_grace_time=600,
    )
    scheduler.add_job(
        func=reset_monthly_lead_counts,
        trigger=CronTrigger(day=1, hour=0, minute=0),
        id="monthly_reset",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    scheduler.start()
    logger.info("[scheduler] Started — email sender every 15m, reply checker every 30m, weekly summary Mon 8am ET")
    return scheduler
