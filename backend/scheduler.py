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
              <tr style="margin:0 -6px;">
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
    if not api_key:
        logger.warning("[scheduler] RESEND_API_KEY not set — skipping weekly summary")
        return
    if not db_url:
        logger.warning("[scheduler] DATABASE_URL not set — skipping weekly summary")
        return

    resend.api_key = api_key
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("SELECT id, name, business_name, email FROM clients WHERE status = 'active'")
        clients = cur.fetchall()

        for client in clients:
            cid = client["id"]

            cur.execute(
                "SELECT COUNT(*) AS c FROM lead_uploads WHERE client_id = %s AND uploaded_at >= %s",
                (cid, week_ago),
            )
            uploaded = cur.fetchone()["c"]

            cur.execute(
                """SELECT COUNT(*) AS c FROM lead_uploads
                   WHERE client_id = %s AND uploaded_at >= %s
                   AND status IN ('Contacted', 'Outreach Queue')""",
                (cid, week_ago),
            )
            contacted = cur.fetchone()["c"]

            cur.execute(
                """SELECT COUNT(*) AS c FROM lead_uploads
                   WHERE client_id = %s AND uploaded_at >= %s
                   AND status IN ('Replied','INTERESTED','QUESTION','NOT NOW','MEETING READY')""",
                (cid, week_ago),
            )
            replied = cur.fetchone()["c"]

            cur.execute(
                """SELECT COUNT(*) AS c FROM lead_uploads
                   WHERE client_id = %s AND uploaded_at >= %s
                   AND status IN ('Booked', 'Call Booked')""",
                (cid, week_ago),
            )
            booked = cur.fetchone()["c"]

            first_name = client["name"].split()[0] if client["name"] else "there"
            html = _weekly_email_html(
                first_name, client["business_name"], uploaded, contacted, replied, booked
            )

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

        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"[scheduler] weekly_summary_job error: {e}")


def start_scheduler():
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.warning("[scheduler] apscheduler not installed — weekly emails disabled")
        return None

    scheduler = BackgroundScheduler(timezone="America/New_York")
    scheduler.add_job(
        func=weekly_summary_job,
        trigger=CronTrigger(day_of_week="mon", hour=8, minute=0),
        id="weekly_summary",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    logger.info("[scheduler] Started — weekly summary runs Mondays 8am ET")
    return scheduler
