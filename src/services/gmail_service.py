import os
import base64
import html
import logging
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from src.db import update_user_gmail_tokens

logger = logging.getLogger("invoicechaser")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
# Sign-in asks for basic profile access only, which shows no warning screen.
# Sending needs gmail.send ("sensitive": Google verification is free). We never
# ask to read the inbox: replies come back through Resend Inbound instead, so
# no "restricted" scope and no paid security assessment.
SIGN_IN_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
SCOPES = SIGN_IN_SCOPES + [GMAIL_SEND_SCOPE]


class GmailService:
    """Wrapper around the Gmail API for sending email from the user's account."""

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

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        thread_id: str | None = None,
        attachments: list[dict] | None = None,
        reply_to: list[str] | None = None,
    ) -> dict:
        """Send email. Returns {id, threadId}.

        The body is HTML-escaped (drafts can quote client text), and header
        values are collapsed to one line so they can't break the message.

        ``reply_to`` lets client replies reach both the freelancer and the
        Resend Inbound tracking address.
        """
        html_body = html.escape(body).replace("\n", "<br>")
        subject = " ".join((subject or "").split())
        to = " ".join((to or "").split())
        if attachments:
            message = MIMEMultipart()
            message.attach(MIMEText(html_body, "html"))
            for attachment in attachments:
                mime_type = attachment.get("mime_type") or "application/octet-stream"
                if "/" in mime_type:
                    maintype, subtype = mime_type.split("/", 1)
                else:
                    maintype, subtype = "application", "octet-stream"
                part = MIMEBase(maintype, subtype)
                part.set_payload(attachment["content"])
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=attachment.get("filename") or "invoice",
                )
                message.attach(part)
        else:
            message = MIMEText(html_body, "html")
        message["to"] = to
        message["subject"] = subject
        if reply_to:
            message["Reply-To"] = ", ".join(reply_to)
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        send_body = {"raw": raw}
        if thread_id:
            send_body["threadId"] = thread_id
        result = self.service.users().messages().send(userId="me", body=send_body).execute()
        logger.info(f"Email sent via Gmail: id={result['id']}, threadId={result['threadId']}")
        return {"id": result["id"], "threadId": result["threadId"]}
