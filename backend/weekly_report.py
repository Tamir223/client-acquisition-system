import logging
import os
from datetime import datetime, timedelta, timezone

import psycopg2
import psycopg2.extras
import resend

logger = logging.getLogger(__name__)


def _build_html(first_name, business_name, leads_contacted, replies_received,
                interested_count, meeting_ready_count, calls_booked):
    hot_leads = interested_count + meeting_ready_count
    if calls_booked > 0:
        cta_text = (
            f"You booked {calls_booked} call{'s' if calls_booked != 1 else ''} this week. "
            "Great work — keep the momentum going."
        )
        cta_url_text = "View your dashboard"
    elif hot_leads > 0:
        cta_text = (
            f"You have {hot_leads} lead{'s' if hot_leads != 1 else ''} ready for follow up. "
            "Log in and reach out while they're warm."
        )
        cta_url_text = "Follow up now"
    elif replies_received > 0:
        cta_text = (
            f"You got {replies_received} repl{'ies' if replies_received != 1 else 'y'} this week. "
            "Follow up fast for best results."
        )
        cta_url_text = "View replies"
    elif leads_contacted > 0:
        cta_text = (
            f"Your system followed up on {leads_contacted} lead{'s' if leads_contacted != 1 else ''} "
            "this week. Replies typically come within 3–5 days."
        )
        cta_url_text = "View your dashboard"
    else:
        cta_text = "Upload your first leads to start getting replies."
        cta_url_text = "Upload leads now"

    def stat_box(label, value, color):
        return (
            f'<td style="width:20%;padding:0 5px;text-align:center;">'
            f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:14px 6px;">'
            f'<div style="font-size:26px;font-weight:800;color:{color};line-height:1;">{value}</div>'
            f'<div style="font-size:10px;font-weight:600;color:#94a3b8;text-transform:uppercase;'
            f'letter-spacing:1px;margin-top:6px;">{label}</div>'
            f'</div></td>'
        )

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
            <h1 style="margin:12px 0 0;font-size:22px;font-weight:700;color:#ffffff;">Your Weekly Performance Report</h1>
          </td>
        </tr>
        <tr>
          <td style="background:#ffffff;padding:36px 40px;border-left:1px solid #e2e8f0;border-right:1px solid #e2e8f0;">
            <p style="margin:0 0 24px;font-size:16px;color:#334155;">Hi {first_name},</p>
            <p style="margin:0 0 20px;font-size:14px;color:#64748b;">Here&rsquo;s how your automated follow up performed this week:</p>
            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:32px;">
              <tr>
                {stat_box("Contacted", leads_contacted, "#1E3A5F")}
                {stat_box("Replies", replies_received, "#2E75B6")}
                {stat_box("Interested", interested_count, "#f59e0b")}
                {stat_box("Mtg Ready", meeting_ready_count, "#8b5cf6")}
                {stat_box("Booked", calls_booked, "#10b981")}
              </tr>
            </table>
            <div style="background:#f0f9ff;border-left:4px solid #2E75B6;border-radius:0 6px 6px 0;padding:16px 20px;margin-bottom:28px;">
              <p style="margin:0;font-size:15px;color:#1e293b;line-height:1.6;">{cta_text}</p>
            </div>
            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
              <tr>
                <td align="center">
                  <a href="https://clientmachinery.com/portal/dashboard"
                     style="display:inline-block;background:#2E75B6;color:#ffffff;text-decoration:none;font-size:15px;font-weight:600;padding:14px 36px;border-radius:7px;">
                    {cta_url_text} &rarr;
                  </a>
                </td>
              </tr>
            </table>
            <p style="margin:0;font-size:13px;color:#64748b;line-height:1.6;text-align:center;">
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


def send_weekly_report(client_id):
    """Send the weekly performance email for a single client."""
    api_key = os.getenv("RESEND_API_KEY")
    db_url = os.getenv("DATABASE_URL")
    if not api_key or not db_url:
        logger.warning("[weekly_report] RESEND_API_KEY or DATABASE_URL not set")
        return

    resend.api_key = api_key
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)

    conn = psycopg2.connect(db_url)
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT id, name, business_name, email, telegram_connected, telegram_chat_id, notify_weekly "
            "FROM clients WHERE id = %s AND status = 'active'",
            (client_id,)
        )
        client = cur.fetchone()
        if not client:
            return

        cid = client["id"]

        cur.execute(
            "SELECT COUNT(*) AS c FROM scheduled_emails WHERE client_id = %s AND status = 'sent' AND sent_at >= %s",
            (cid, week_ago)
        )
        leads_contacted = cur.fetchone()["c"]

        cur.execute(
            "SELECT COUNT(*) AS c FROM lead_replies WHERE client_id = %s AND created_at >= %s AND source != 'auto_reply'",
            (cid, week_ago)
        )
        replies_received = cur.fetchone()["c"]

        cur.execute(
            "SELECT COUNT(*) AS c FROM lead_uploads WHERE client_id = %s AND uploaded_at >= %s AND status = 'INTERESTED'",
            (cid, week_ago)
        )
        interested_count = cur.fetchone()["c"]

        cur.execute(
            "SELECT COUNT(*) AS c FROM lead_uploads WHERE client_id = %s AND uploaded_at >= %s AND status = 'MEETING READY'",
            (cid, week_ago)
        )
        meeting_ready_count = cur.fetchone()["c"]

        cur.execute(
            "SELECT COUNT(*) AS c FROM lead_uploads WHERE client_id = %s AND uploaded_at >= %s AND status IN ('Booked','Call Booked')",
            (cid, week_ago)
        )
        calls_booked = cur.fetchone()["c"]

        cur.close()

        first_name = client["name"].split()[0] if client["name"] else "there"
        html = _build_html(
            first_name, client["business_name"],
            leads_contacted, replies_received,
            interested_count, meeting_ready_count, calls_booked
        )

        resend.Emails.send({
            "from": "Client Machinery <support@clientmachinery.com>",
            "to": client["email"],
            "reply_to": "support@clientmachinery.com",
            "subject": "Your Client Machinery Weekly Report",
            "html": html,
        })
        logger.info(f"[weekly_report] Sent to {client['email']}")
    except Exception as e:
        logger.error(f"[weekly_report] Failed for client {client_id}: {e}")
    finally:
        conn.close()


def send_all_weekly_reports():
    """Send weekly performance emails to all active clients."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.warning("[weekly_report] DATABASE_URL not set")
        return

    conn = psycopg2.connect(db_url)
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT id FROM clients WHERE status = 'active'")
        client_ids = [r["id"] for r in cur.fetchall()]
        cur.close()
    finally:
        conn.close()

    for cid in client_ids:
        try:
            send_weekly_report(cid)
        except Exception as e:
            logger.error(f"[weekly_report] Error for client {cid}: {e}")
