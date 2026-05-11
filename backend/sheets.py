import os
import json
import logging
from datetime import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SERVICE_ACCOUNT_EMAIL = "cas-sheets-bot@client-machinery-496012.iam.gserviceaccount.com"

SHEET_HEADERS = [
    "Date Added", "First Name", "Last Name", "Business Name", "Industry",
    "Email", "Phone", "Lead Source", "Lead Score", "Status", "Notes",
    "Follow Up Date", "Booked", "Pain Point", "First Line",
    "Reply Classification", "Website", "Employees", "Keywords", "City", "State",
]


def _get_credentials():
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not creds_json or creds_json == "placeholder":
        return None
    try:
        creds_dict = json.loads(creds_json)
        return service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    except Exception as e:
        logger.error(f"[sheets] Failed to parse credentials: {e}")
        return None


def create_client_sheet(client_name, client_email):
    credentials = _get_credentials()
    if not credentials:
        logger.warning("[sheets] GOOGLE_SERVICE_ACCOUNT_JSON not configured — skipping sheet creation")
        return None

    try:
        sheets_service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
        drive_service = build("drive", "v3", credentials=credentials, cache_discovery=False)

        spreadsheet = sheets_service.spreadsheets().create(body={
            "properties": {"title": f"{client_name} — CAS Leads"},
            "sheets": [{"properties": {"title": "LEADS"}}],
        }).execute()

        sheet_id = spreadsheet["spreadsheetId"]

        sheets_service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range="LEADS!A1",
            valueInputOption="USER_ENTERED",
            body={"values": [SHEET_HEADERS]},
        ).execute()

        drive_service.permissions().create(
            fileId=sheet_id,
            body={
                "type": "user",
                "role": "writer",
                "emailAddress": SERVICE_ACCOUNT_EMAIL,
            },
            sendNotificationEmail=False,
        ).execute()

        logger.info(f"[sheets] Created sheet for {client_email}: {sheet_id}")
        return sheet_id
    except Exception as e:
        logger.error(f"[sheets] Failed to create sheet for {client_email}: {e}")
        return None


def create_client_drive_folder(client_name):
    credentials = _get_credentials()
    if not credentials:
        logger.warning("[sheets] GOOGLE_SERVICE_ACCOUNT_JSON not configured — skipping Drive folder creation")
        return None

    try:
        drive_service = build("drive", "v3", credentials=credentials, cache_discovery=False)

        folder = drive_service.files().create(body={
            "name": f"{client_name} — Client Machinery",
            "mimeType": "application/vnd.google-apps.folder",
        }).execute()
        folder_id = folder["id"]

        for sub in ["Onboarding", "Reports", "Case Study"]:
            drive_service.files().create(body={
                "name": sub,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [folder_id],
            }).execute()

        logger.info(f"[sheets] Created Drive folder for {client_name}: {folder_id}")
        return folder_id
    except Exception as e:
        logger.error(f"[sheets] Failed to create Drive folder for {client_name}: {e}")
        return None


def append_lead_to_sheet(sheet_id, lead_data):
    credentials = _get_credentials()
    if not credentials:
        logger.warning("[sheets] GOOGLE_SERVICE_ACCOUNT_JSON is not configured — skipping sheet append")
        return None

    try:
        service = build("sheets", "v4", credentials=credentials, cache_discovery=False)

        today = datetime.now().strftime("%m/%d/%Y")
        empty = ""
        row = [
            today,
            lead_data.get("first_name", ""),
            lead_data.get("last_name", ""),
            lead_data.get("service_requested", ""),
            lead_data.get("target_icp") or lead_data.get("niche", ""),
            lead_data.get("email", ""),
            lead_data.get("phone", ""),
            "Portal",
            empty, empty, empty, empty, empty,
            empty, empty, empty, empty, empty,
            empty, empty, empty,
        ]

        service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range="LEADS!A:U",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [row]},
        ).execute()

        return True
    except Exception as e:
        logger.error(f"[sheets] Failed to append lead to sheet {sheet_id}: {e}")
        return None
