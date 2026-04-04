import os
import base64
import logging
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from src.db import update_user_gmail_tokens

logger = logging.getLogger("invoicechaser")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]


class GmailService:
    """Wrapper around Gmail API for sending and reading emails."""

    def __init__(self, user_id: str, access_token: str, refresh_token: str | None = None):
        self.user_id = user_id
        self.creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            scopes=SCOPES,
        )
        self._refresh_if_needed()
        self.service = build("gmail", "v1", credentials=self.creds)

    def _refresh_if_needed(self):
        if self.creds.expired and self.creds.refresh_token:
            self.creds.refresh(Request())
            update_user_gmail_tokens(self.user_id, self.creds.token, self.creds.refresh_token)
            logger.info(f"Refreshed Gmail token for user {self.user_id}")

    def send_email(self, to: str, subject: str, body: str, thread_id: str | None = None) -> dict:
        """Send email. Returns {id, threadId}."""
        message = MIMEText(body.replace("\n", "<br>"), "html")
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        send_body = {"raw": raw}
        if thread_id:
            send_body["threadId"] = thread_id
        result = self.service.users().messages().send(userId="me", body=send_body).execute()
        logger.info(f"Email sent via Gmail: id={result['id']}, threadId={result['threadId']}")
        return {"id": result["id"], "threadId": result["threadId"]}

    def get_replies(self, client_email: str, thread_id: str | None = None, after_timestamp: str | None = None) -> list[dict]:
        """Get emails from a specific sender, optionally within a thread."""
        if thread_id:
            thread = self.service.users().threads().get(userId="me", id=thread_id, format="full").execute()
            messages = []
            for msg in thread.get("messages", []):
                headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}
                if client_email.lower() in headers.get("from", "").lower():
                    messages.append(self._parse_message(msg))
            return messages
        query = f"from:{client_email}"
        if after_timestamp:
            query += f" after:{after_timestamp}"
        results = self.service.users().messages().list(userId="me", q=query, maxResults=10).execute()
        messages = []
        for msg_ref in results.get("messages", []):
            msg = self.service.users().messages().get(userId="me", id=msg_ref["id"], format="full").execute()
            messages.append(self._parse_message(msg))
        return messages

    def search_emails(self, query: str, max_results: int = 10) -> list[dict]:
        results = self.service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
        messages = []
        for msg_ref in results.get("messages", []):
            msg = self.service.users().messages().get(userId="me", id=msg_ref["id"], format="full").execute()
            messages.append(self._parse_message(msg))
        return messages

    def get_thread(self, thread_id: str) -> list[dict]:
        thread = self.service.users().threads().get(userId="me", id=thread_id, format="full").execute()
        return [self._parse_message(msg) for msg in thread.get("messages", [])]

    def mark_as_read(self, message_id: str):
        self.service.users().messages().modify(userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}).execute()

    def watch_inbox(self, topic_name: str) -> dict:
        """Register for Gmail push notifications. Returns {historyId, expiration}."""
        result = self.service.users().watch(userId="me", body={"topicName": topic_name, "labelIds": ["INBOX"]}).execute()
        logger.info(f"Gmail watch registered: historyId={result['historyId']}, expires={result['expiration']}")
        return result

    def get_history(self, start_history_id: str) -> list[dict]:
        """Get new messages since a history ID."""
        try:
            results = self.service.users().history().list(
                userId="me", startHistoryId=start_history_id,
                historyTypes=["messageAdded"], labelId="INBOX"
            ).execute()
        except Exception as e:
            logger.error(f"Failed to get history: {e}")
            return []
        messages = []
        for record in results.get("history", []):
            for msg_added in record.get("messagesAdded", []):
                try:
                    msg = self.service.users().messages().get(
                        userId="me", id=msg_added["message"]["id"], format="full"
                    ).execute()
                    messages.append(self._parse_message(msg))
                except Exception as e:
                    logger.error(f"Failed to fetch message: {e}")
        return messages

    def _parse_message(self, msg: dict) -> dict:
        headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}
        body = ""
        payload = msg["payload"]
        if payload.get("body", {}).get("data"):
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
        elif payload.get("parts"):
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain" and part.get("body", {}).get("data"):
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                    break
        return {
            "id": msg["id"], "threadId": msg["threadId"],
            "from": headers.get("from", ""), "to": headers.get("to", ""),
            "subject": headers.get("subject", ""), "body": body,
            "date": headers.get("date", ""), "labels": msg.get("labelIds", []),
        }
