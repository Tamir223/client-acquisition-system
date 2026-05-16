"""
AWS SES integration for Client Machinery.

Sending hierarchy in sequence_engine.py:
  Priority 1 — Gmail (client's connected inbox)
  Priority 2 — SES dedicated address  (client.dedicated_email, this module)
  Priority 3 — Resend fallback        (support@clientmachinery.com)

Inbound replies arrive via SNS → /api/webhooks/ses-inbound.
Bounces  arrive via SNS → /api/webhooks/ses-bounce.
Complaints arrive via SNS → /api/webhooks/ses-complaint.

Required env vars:
  AWS_ACCESS_KEY_ID       — IAM key with ses:SendEmail, ses:SendRawEmail
  AWS_SECRET_ACCESS_KEY   — matching secret
  AWS_SES_REGION          — defaults to us-east-1
  SES_SENDING_DOMAIN      — verified domain, defaults to outreach.clientmachinery.com
"""
import json
import logging
import os
import re
import secrets

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

_SES_REGION = os.getenv("AWS_SES_REGION", "us-east-1")
_SENDING_DOMAIN = os.getenv("SES_SENDING_DOMAIN", "outreach.clientmachinery.com")


def _client():
    return boto3.client(
        "ses",
        region_name=_SES_REGION,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )


def provision_dedicated_email(client_name):
    """
    Generate a unique sending address for a client under the verified SES domain.
    Format: {slug}-{hex6}@{SES_SENDING_DOMAIN}

    No AWS API call needed — SES domain verification covers all sub-addresses
    automatically once the domain is verified in SES.

    Returns the address string.
    """
    slug = re.sub(r"[^a-z0-9]", "", client_name.lower())[:18] or "client"
    suffix = secrets.token_hex(3)
    return f"{slug}-{suffix}@{_SENDING_DOMAIN}"


def send_email(from_addr, to_addr, subject, body, reply_to=None):
    """
    Send a plain-text email via AWS SES.
    Raises ClientError on failure so the caller can fall through to the next provider.
    """
    ses = _client()
    kwargs = {
        "Source": from_addr,
        "Destination": {"ToAddresses": [to_addr]},
        "Message": {
            "Subject": {"Data": subject, "Charset": "UTF-8"},
            "Body": {"Text": {"Data": body, "Charset": "UTF-8"}},
        },
    }
    if reply_to:
        kwargs["ReplyToAddresses"] = [reply_to]
    ses.send_email(**kwargs)
    return True


# ─── SNS notification parsing ────────────────────────────────────────────────

def parse_sns_notification(raw_body):
    """
    Unwrap an SNS HTTP notification envelope and return the inner SES message dict.
    The outer envelope has a "Message" field that is a JSON string.
    """
    if isinstance(raw_body, (bytes, bytearray)):
        raw_body = raw_body.decode("utf-8")
    outer = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
    inner = outer.get("Message", "{}")
    if isinstance(inner, str):
        inner = json.loads(inner)
    return inner


def extract_inbound_fields(ses_msg):
    """
    Pull from_email, to_emails, subject, and snippet from an SES inbound notification.
    Returns a dict with those four keys.
    """
    mail = ses_msg.get("mail", {})
    headers = mail.get("commonHeaders", {})

    raw_from = headers.get("from", "")
    if isinstance(raw_from, list):
        raw_from = raw_from[0] if raw_from else ""
    match = re.search(r"<(.+?)>", raw_from)
    from_email = match.group(1).lower() if match else raw_from.strip().lower()

    to_addrs = headers.get("to", [])
    if isinstance(to_addrs, str):
        to_addrs = [to_addrs]

    subject = headers.get("subject", "")

    return {
        "from_email": from_email,
        "to_emails": to_addrs,
        "subject": subject,
        "snippet": subject,  # full body is in S3 if action=s3 is configured
    }


def extract_bounce_fields(ses_msg):
    """
    Pull bounce type and bounced recipient emails from an SES bounce notification.
    bounce_type is "Permanent" or "Transient".
    """
    bounce = ses_msg.get("bounce", {})
    mail = ses_msg.get("mail", {})
    return {
        "bounce_type": bounce.get("bounceType", ""),
        "bounce_subtype": bounce.get("bounceSubType", ""),
        "bounced_emails": [
            r.get("emailAddress", "")
            for r in bounce.get("bouncedRecipients", [])
        ],
        "source_email": mail.get("source", ""),
    }


def extract_complaint_fields(ses_msg):
    """
    Pull complained recipient emails from an SES complaint (spam report) notification.
    """
    complaint = ses_msg.get("complaint", {})
    mail = ses_msg.get("mail", {})
    return {
        "complained_emails": [
            r.get("emailAddress", "")
            for r in complaint.get("complainedRecipients", [])
        ],
        "source_email": mail.get("source", ""),
    }
