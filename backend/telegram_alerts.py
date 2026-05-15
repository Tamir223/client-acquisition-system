import logging
import os

import requests

logger = logging.getLogger(__name__)

TAMIR_CHAT_ID = "8647323622"
DONALD_CHAT_ID = "5803919273"


def send_telegram(chat_id, text):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=5,
        )
    except Exception as e:
        logger.error(f"[telegram] send failed to {chat_id}: {e}")


def alert_partners(text):
    """Send to both Tamir and Donald."""
    send_telegram(TAMIR_CHAT_ID, text)
    if DONALD_CHAT_ID != TAMIR_CHAT_ID:
        send_telegram(DONALD_CHAT_ID, text)


def alert_client(client, text):
    """Send to a connected client's Telegram."""
    if client.get("telegram_connected") and client.get("telegram_chat_id"):
        send_telegram(client["telegram_chat_id"], text)


def alert_reply(client, lead_first, lead_last, from_email, snippet):
    alert_partners(
        f"\U0001f4ac Reply Detected\n"
        f"Client: {client.get('business_name', '')}\n"
        f"Lead: {lead_first} {lead_last}\n"
        f"Email: {from_email}\n"
        f"Preview: {snippet}"
    )
    if client.get("telegram_connected") and client.get("notify_replies") and client.get("telegram_chat_id"):
        alert_client(
            client,
            f"\U0001f525 Lead Replied!\n\n"
            f"{lead_first} {lead_last} just replied to your follow-up sequence.\n\n"
            f"Sequence stopped automatically.\n\n"
            f"View reply: clientmachinery.com/portal/dashboard",
        )


def alert_email_sent(client, lead_first, lead_last, lead_email, touch_number, from_addr):
    alert_partners(
        f"\U0001f4e7 Email {touch_number} Sent\n"
        f"Client: {client.get('business_name', '')}\n"
        f"To: {lead_first} {lead_last}\n"
        f"Email: {lead_email}\n"
        f"From: {from_addr}"
    )
    if client.get("telegram_connected") and client.get("notify_replies") and client.get("telegram_chat_id"):
        alert_client(
            client,
            f"\U0001f4e7 Follow Up Sent\n\n"
            f"Email {touch_number} of 5 sent to:\n"
            f"{lead_first} {lead_last}\n"
            f"{lead_email}\n\n"
            f"View dashboard: clientmachinery.com/portal/dashboard",
        )


def alert_booking(client, lead_first, lead_last):
    alert_partners(
        f"\U0001f4c5 Booking!\n"
        f"Client: {client.get('business_name', '')}\n"
        f"Lead: {lead_first} {lead_last}"
    )
    if client.get("telegram_connected") and client.get("notify_bookings") and client.get("telegram_chat_id"):
        alert_client(
            client,
            f"\U0001f4c5 Booking Confirmed!\n\n"
            f"{lead_first} {lead_last} booked a call.\n\n"
            f"View dashboard: clientmachinery.com/portal/dashboard",
        )


def alert_sequence_started(client, lead_first, lead_last, count):
    alert_partners(
        f"\U0001f680 Sequence Started\n"
        f"Client: {client.get('business_name', '')}\n"
        f"Lead: {lead_first} {lead_last}\n"
        f"Emails scheduled: {count}"
    )
