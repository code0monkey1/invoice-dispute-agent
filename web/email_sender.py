"""Build the Gmail-backed EmailSender from the live dependency container."""

import logging

logger = logging.getLogger("invoicechaser")


def create_gmail_sender(deps):
    def send(
        user_id: str,
        to_email: str,
        subject: str,
        body: str,
        thread_id: str | None = None,
        attachments: list[dict] | None = None,
        reply_to: list[str] | None = None,
    ) -> dict | None:
        tokens = deps.gmail_tokens(user_id)
        if not tokens:
            logger.warning("No Gmail tokens for user %s — skipping email send", user_id)
            return None
        try:
            gmail = deps.gmail_client(
                user_id,
                tokens[0],
                tokens[1],
                deps.db.update_user_gmail_tokens,
            )
            result = gmail.send_email(
                to_email,
                subject,
                body,
                thread_id,
                attachments=attachments,
                reply_to=reply_to,
            )
            logger.info("Email sent via Gmail: %s", result)
            return result
        except Exception as exc:
            logger.error("Failed to send email via Gmail: %s", exc)
            return None

    return send
