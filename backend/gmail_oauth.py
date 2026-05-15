import base64
import logging
import os
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]

REDIRECT_URI = "https://clientmachinery.com/api/portal/auth/gmail/callback"


def _client_config():
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise ValueError("GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET must be set")
    return {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI],
        }
    }


def _creds_from_client(client):
    cfg = _client_config()["web"]
    return Credentials(
        token=client.get("gmail_access_token"),
        refresh_token=client.get("gmail_refresh_token"),
        token_uri=cfg["token_uri"],
        client_id=cfg["client_id"],
        client_secret=cfg["client_secret"],
        scopes=GMAIL_SCOPES,
    )


def get_oauth_url(client_id):
    flow = Flow.from_client_config(_client_config(), scopes=GMAIL_SCOPES)
    flow.redirect_uri = REDIRECT_URI
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        state=str(client_id),
        prompt="consent",
    )
    return auth_url


def exchange_code(code, client_id):
    from database import get_db
    flow = Flow.from_client_config(_client_config(), scopes=GMAIL_SCOPES)
    flow.redirect_uri = REDIRECT_URI
    flow.fetch_token(code=code)

    creds = flow.credentials
    service = build("gmail", "v1", credentials=creds)
    profile = service.users().getProfile(userId="me").execute()
    gmail_email = profile.get("emailAddress", "")

    db = get_db()
    db.execute(
        """UPDATE clients SET
               gmail_access_token = ?,
               gmail_refresh_token = ?,
               gmail_connected = TRUE,
               gmail_email = ?
           WHERE id = ?""",
        (creds.token, creds.refresh_token, gmail_email, client_id),
    )
    db.commit()
    return True


def refresh_access_token(client_id):
    from database import get_db
    db = get_db()
    row = db.execute(
        "SELECT gmail_refresh_token FROM clients WHERE id = ?", (client_id,)
    ).fetchone()
    if not row or not row["gmail_refresh_token"]:
        raise ValueError("No refresh token available")

    cfg = _client_config()["web"]
    creds = Credentials(
        token=None,
        refresh_token=row["gmail_refresh_token"],
        token_uri=cfg["token_uri"],
        client_id=cfg["client_id"],
        client_secret=cfg["client_secret"],
        scopes=GMAIL_SCOPES,
    )
    creds.refresh(Request())
    db.execute(
        "UPDATE clients SET gmail_access_token = ? WHERE id = ?",
        (creds.token, client_id),
    )
    db.commit()
    return creds.token


def send_via_gmail(client, to_email, subject, body):
    creds = _creds_from_client(client)
    if not creds.valid:
        try:
            creds.refresh(Request())
            from database import get_db
            db = get_db()
            db.execute(
                "UPDATE clients SET gmail_access_token = ? WHERE id = ?",
                (creds.token, client["id"]),
            )
            db.commit()
        except Exception as e:
            raise RuntimeError(f"Token refresh failed: {e}")

    service = build("gmail", "v1", credentials=creds)
    msg = MIMEMultipart()
    msg["To"] = to_email
    msg["From"] = client.get("gmail_email") or client.get("email", "")
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return result.get("id")


def get_unread_replies(client):
    creds = _creds_from_client(client)
    if not creds.valid:
        try:
            creds.refresh(Request())
            from database import get_db
            db = get_db()
            db.execute(
                "UPDATE clients SET gmail_access_token = ? WHERE id = ?",
                (creds.token, client["id"]),
            )
            db.commit()
        except Exception as e:
            logger.error(f"[gmail] Token refresh failed for client {client['id']}: {e}")
            return []

    service = build("gmail", "v1", credentials=creds)
    results = service.users().messages().list(
        userId="me", q="in:inbox is:unread"
    ).execute()

    emails = []
    for msg in (results.get("messages") or [])[:20]:
        data = service.users().messages().get(
            userId="me", id=msg["id"], format="full"
        ).execute()
        headers = {h["name"]: h["value"] for h in data.get("payload", {}).get("headers", [])}
        emails.append({
            "id": msg["id"],
            "from": headers.get("From", ""),
            "subject": headers.get("Subject", ""),
            "snippet": data.get("snippet", ""),
        })
        service.users().messages().modify(
            userId="me", id=msg["id"], body={"removeLabelIds": ["UNREAD"]}
        ).execute()

    return emails
