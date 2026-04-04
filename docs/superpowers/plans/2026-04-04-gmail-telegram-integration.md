# Gmail + Telegram Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Resend with Gmail API for sending/receiving emails, add real-time push notifications via Pub/Sub, Telegram bot notifications, SQLite persistence, and Google OAuth sign-in.

**Architecture:** GmailService wraps Gmail API for send/read. Google Pub/Sub pushes incoming email notifications to a webhook. TelegramService sends mobile alerts. SQLite replaces in-memory stores. Google OAuth serves as both sign-in and Gmail access grant.

**Tech Stack:** Python (FastAPI, google-auth, google-api-python-client, cryptography, PyJWT), React (Vite, Tailwind), SQLite, Gmail API, Google Pub/Sub, Telegram Bot API.

**Spec:** `docs/superpowers/specs/2026-04-04-gmail-telegram-integration-design.md`

---

## File Structure

### New Files

| File | Responsibility |
|------|---------------|
| `src/db.py` | SQLite database init, schema, query helpers |
| `src/services/gmail_service.py` | Gmail API wrapper (OAuth, send, read, watch) |
| `src/services/telegram_service.py` | Telegram Bot API notification sender |
| `src/tools/payment_tools.py` | `mark_invoice_pending`, `mark_invoice_paid` agent tools |
| `frontend/src/contexts/AuthContext.tsx` | React auth context (JWT storage, user state, sign-in/out) |
| `frontend/src/pages/GoogleCallback.tsx` | OAuth redirect handler page |

### Modified Files

| File | Changes |
|------|---------|
| `requirements.txt` | Add google-auth, google-auth-oauthlib, google-api-python-client, cryptography, PyJWT; remove resend |
| `.env.example` | Replace Resend vars with Google OAuth + Telegram vars |
| `src/state.py` | Add `gmail_thread_id`, `gmail_message_ids` fields |
| `src/agent.py` | Register payment tools, add HITL config for them |
| `src/middleware/dynamic_tools.py` | Add payment tools to level gates |
| `src/prompts/v1/escalation_level_1.txt` | Add reply analysis instructions |
| `src/prompts/v1/escalation_level_2.txt` | Add reply analysis instructions |
| `src/prompts/v1/escalation_level_3.txt` | Add reply analysis instructions |
| `api/index.py` | Add auth endpoints, gmail webhook, replace Resend with GmailService, use SQLite |
| `frontend/src/App.tsx` | Add callback route, wrap with AuthProvider |
| `frontend/src/api.ts` | Add auth API calls, attach JWT to requests |
| `frontend/src/types.ts` | Add User type |
| `frontend/src/components/LandingPage.tsx` | Replace mock sign-in with Google OAuth button |
| `frontend/src/components/ChatPanel.tsx` | Display inbound email messages |
| `frontend/src/components/Layout.tsx` | Show user avatar/email, sign-out button |

---

### Task 1: Update Dependencies

**Files:**
- Modify: `requirements.txt`
- Modify: `.env.example`

- [ ] **Step 1: Update requirements.txt**

Replace the contents of `requirements.txt`:

```text
langchain>=0.3.0
langgraph>=0.4.0
langchain-groq>=0.3.0
langchain-mcp-adapters>=0.1.13
mcp>=1.21.1
tavily-python>=0.7.13
python-dotenv>=1.2.0
fastapi>=0.115.0
uvicorn>=0.34.0
mangum>=0.19.0
ipykernel>=7.1.0
google-auth>=2.29.0
google-auth-oauthlib>=1.2.0
google-api-python-client>=2.130.0
cryptography>=42.0.0
PyJWT>=2.8.0
```

- [ ] **Step 2: Update .env.example**

Replace the contents of `.env.example`:

```text
GROQ_API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key

# Google OAuth (from Google Cloud Console > APIs & Services > Credentials)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:5173/auth/google/callback
GOOGLE_PUBSUB_TOPIC=projects/your-project-id/topics/gmail-notifications

# Telegram Bot (from @BotFather)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# Security
SECRET_KEY=generate-a-random-32-byte-key-here
```

- [ ] **Step 3: Install dependencies**

Run: `pip install -r requirements.txt`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt .env.example
git commit -m "chore: update deps — add google-auth, gmail, telegram; remove resend"
```

---

### Task 2: SQLite Database Layer

**Files:**
- Create: `src/db.py`

- [ ] **Step 1: Create src/db.py**

```python
import os
import sqlite3
import json
from datetime import datetime, timezone
from cryptography.fernet import Fernet
import base64
import hashlib

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "invoice_agent.db")

def _get_fernet() -> Fernet:
    """Derive a Fernet key from SECRET_KEY env var."""
    secret = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)

def encrypt_token(token: str) -> str:
    return _get_fernet().encrypt(token.encode()).decode()

def decrypt_token(encrypted: str) -> str:
    return _get_fernet().decrypt(encrypted.encode()).decode()

def get_db() -> sqlite3.Connection:
    """Get a SQLite connection. Creates the database and tables if they don't exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    """Create tables if they don't exist."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            picture TEXT,
            gmail_access_token TEXT,
            gmail_refresh_token TEXT,
            gmail_connected_at TEXT,
            gmail_history_id TEXT,
            telegram_chat_id TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS invoices (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            client_name TEXT NOT NULL,
            client_email TEXT NOT NULL,
            invoice_amount REAL NOT NULL,
            days_overdue INTEGER NOT NULL DEFAULT 0,
            jurisdiction TEXT,
            escalation_level INTEGER NOT NULL DEFAULT 0,
            gmail_thread_id TEXT,
            gmail_message_ids TEXT DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS communication_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id TEXT NOT NULL,
            type TEXT NOT NULL,
            subject TEXT,
            content TEXT,
            direction TEXT NOT NULL DEFAULT 'outbound',
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (invoice_id) REFERENCES invoices(id)
        );
    """)
    conn.commit()
    conn.close()

# --- User queries ---

def upsert_user(user_id: str, email: str, name: str, picture: str,
                access_token: str, refresh_token: str) -> dict:
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        INSERT INTO users (id, email, name, picture, gmail_access_token, gmail_refresh_token, gmail_connected_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            email=excluded.email,
            name=excluded.name,
            picture=excluded.picture,
            gmail_access_token=excluded.gmail_access_token,
            gmail_refresh_token=excluded.gmail_refresh_token,
            gmail_connected_at=excluded.gmail_connected_at
    """, (user_id, email, name, picture,
          encrypt_token(access_token),
          encrypt_token(refresh_token) if refresh_token else None,
          now, now))
    conn.commit()
    user = dict(conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone())
    conn.close()
    return user

def get_user(user_id: str) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_gmail_tokens(user_id: str) -> tuple[str, str] | None:
    user = get_user(user_id)
    if not user or not user.get("gmail_access_token"):
        return None
    access = decrypt_token(user["gmail_access_token"])
    refresh = decrypt_token(user["gmail_refresh_token"]) if user.get("gmail_refresh_token") else None
    return access, refresh

def update_user_gmail_tokens(user_id: str, access_token: str, refresh_token: str | None = None):
    conn = get_db()
    if refresh_token:
        conn.execute(
            "UPDATE users SET gmail_access_token = ?, gmail_refresh_token = ? WHERE id = ?",
            (encrypt_token(access_token), encrypt_token(refresh_token), user_id)
        )
    else:
        conn.execute(
            "UPDATE users SET gmail_access_token = ? WHERE id = ?",
            (encrypt_token(access_token), user_id)
        )
    conn.commit()
    conn.close()

def update_user_history_id(user_id: str, history_id: str):
    conn = get_db()
    conn.execute("UPDATE users SET gmail_history_id = ? WHERE id = ?", (history_id, user_id))
    conn.commit()
    conn.close()

# --- Invoice queries ---

def create_invoice(invoice_id: str, user_id: str, client_name: str, client_email: str,
                   invoice_amount: float, days_overdue: int, jurisdiction: str) -> dict:
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        INSERT INTO invoices (id, user_id, client_name, client_email, invoice_amount,
                              days_overdue, jurisdiction, escalation_level, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1, 'active', ?, ?)
    """, (invoice_id, user_id, client_name, client_email, invoice_amount,
          days_overdue, jurisdiction, now, now))
    conn.commit()
    row = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    conn.close()
    return dict(row)

def get_invoice(invoice_id: str) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_invoices_by_user(user_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM invoices WHERE user_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_invoice(invoice_id: str, **kwargs) -> dict | None:
    conn = get_db()
    sets = []
    vals = []
    for k, v in kwargs.items():
        sets.append(f"{k} = ?")
        vals.append(v)
    sets.append("updated_at = ?")
    vals.append(datetime.now(timezone.utc).isoformat())
    vals.append(invoice_id)
    conn.execute(f"UPDATE invoices SET {', '.join(sets)} WHERE id = ?", vals)
    conn.commit()
    row = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_invoices_by_client_email(client_email: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM invoices WHERE client_email = ? AND status = 'active'",
        (client_email,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# --- Communication history queries ---

def add_communication(invoice_id: str, comm_type: str, subject: str,
                      content: str, direction: str = "outbound") -> dict:
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute("""
        INSERT INTO communication_history (invoice_id, type, subject, content, direction, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (invoice_id, comm_type, subject, content, direction, now))
    conn.commit()
    row = conn.execute("SELECT * FROM communication_history WHERE id = ?", (cursor.lastrowid,)).fetchone()
    conn.close()
    return dict(row)

def get_communications(invoice_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM communication_history WHERE invoice_id = ? ORDER BY timestamp",
        (invoice_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
```

- [ ] **Step 2: Add data/ to .gitignore**

Append to `.gitignore`:

```text
data/
```

- [ ] **Step 3: Verify database initializes**

Run: `python -c "from src.db import init_db; init_db(); print('DB initialized')"`

Expected: `DB initialized` and `data/invoice_agent.db` file created.

- [ ] **Step 4: Commit**

```bash
git add src/db.py .gitignore
git commit -m "feat: add SQLite persistence layer with encrypted token storage"
```

---

### Task 3: Telegram Service

**Files:**
- Create: `src/services/telegram_service.py`

- [ ] **Step 1: Create src/services/__init__.py**

```python
```

(Empty file to make it a package.)

- [ ] **Step 2: Create src/services/telegram_service.py**

```python
import os
import logging
import urllib.request
import urllib.parse
import json

logger = logging.getLogger("invoicechaser")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


def send_telegram_notification(message: str) -> bool:
    """Send a notification message via Telegram Bot API. Returns True on success."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram not configured — skipping notification")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }).encode()

    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            if result.get("ok"):
                logger.info("Telegram notification sent")
                return True
            logger.error(f"Telegram API error: {result}")
            return False
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {e}")
        return False
```

- [ ] **Step 3: Verify Telegram service works**

Run:

```bash
TELEGRAM_BOT_TOKEN=8690631740:AAFGrA1MdL0_WC5OnpB98bDTbjfZY93n_WE \
TELEGRAM_CHAT_ID=8657502519 \
python -c "from src.services.telegram_service import send_telegram_notification; print(send_telegram_notification('Test from plan'))"
```

Expected: `True` printed, and you receive a Telegram message.

- [ ] **Step 4: Commit**

```bash
git add src/services/
git commit -m "feat: add Telegram notification service"
```

---

### Task 4: Gmail Service

**Files:**
- Create: `src/services/gmail_service.py`

- [ ] **Step 1: Create src/services/gmail_service.py**

```python
import os
import base64
import json
import logging
from email.mime.text import MIMEText
from typing import Optional

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
        """Refresh access token if expired."""
        if self.creds.expired and self.creds.refresh_token:
            self.creds.refresh(Request())
            update_user_gmail_tokens(
                self.user_id,
                self.creds.token,
                self.creds.refresh_token,
            )
            logger.info(f"Refreshed Gmail token for user {self.user_id}")

    def send_email(self, to: str, subject: str, body: str,
                   thread_id: str | None = None) -> dict:
        """Send an email via Gmail API. Returns {id, threadId}."""
        message = MIMEText(body.replace("\n", "<br>"), "html")
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        send_body = {"raw": raw}
        if thread_id:
            send_body["threadId"] = thread_id

        result = self.service.users().messages().send(
            userId="me", body=send_body
        ).execute()

        logger.info(f"Email sent via Gmail: id={result['id']}, threadId={result['threadId']}")
        return {"id": result["id"], "threadId": result["threadId"]}

    def get_replies(self, client_email: str, thread_id: str | None = None,
                    after_timestamp: str | None = None) -> list[dict]:
        """Get emails from a specific sender, optionally within a thread."""
        query = f"from:{client_email}"
        if after_timestamp:
            query += f" after:{after_timestamp}"

        if thread_id:
            # Get all messages in the thread, then filter by sender
            thread = self.service.users().threads().get(
                userId="me", id=thread_id, format="full"
            ).execute()
            messages = []
            for msg in thread.get("messages", []):
                headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}
                from_addr = headers.get("from", "")
                if client_email.lower() in from_addr.lower():
                    messages.append(self._parse_message(msg))
            return messages

        # Fallback: search by query
        results = self.service.users().messages().list(
            userId="me", q=query, maxResults=10
        ).execute()

        messages = []
        for msg_ref in results.get("messages", []):
            msg = self.service.users().messages().get(
                userId="me", id=msg_ref["id"], format="full"
            ).execute()
            messages.append(self._parse_message(msg))
        return messages

    def search_emails(self, query: str, max_results: int = 10) -> list[dict]:
        """Search Gmail with a raw query string."""
        results = self.service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()

        messages = []
        for msg_ref in results.get("messages", []):
            msg = self.service.users().messages().get(
                userId="me", id=msg_ref["id"], format="full"
            ).execute()
            messages.append(self._parse_message(msg))
        return messages

    def get_thread(self, thread_id: str) -> list[dict]:
        """Get all messages in a Gmail thread."""
        thread = self.service.users().threads().get(
            userId="me", id=thread_id, format="full"
        ).execute()
        return [self._parse_message(msg) for msg in thread.get("messages", [])]

    def mark_as_read(self, message_id: str):
        """Mark a message as read by removing the UNREAD label."""
        self.service.users().messages().modify(
            userId="me", id=message_id,
            body={"removeLabelIds": ["UNREAD"]}
        ).execute()

    def watch_inbox(self, topic_name: str) -> dict:
        """Register for Gmail push notifications via Pub/Sub. Returns {historyId, expiration}."""
        result = self.service.users().watch(
            userId="me",
            body={
                "topicName": topic_name,
                "labelIds": ["INBOX"],
            }
        ).execute()
        logger.info(f"Gmail watch registered: historyId={result['historyId']}, expires={result['expiration']}")
        return result

    def get_history(self, start_history_id: str) -> list[dict]:
        """Get message history since a given history ID. Returns list of new messages."""
        try:
            results = self.service.users().history().list(
                userId="me",
                startHistoryId=start_history_id,
                historyTypes=["messageAdded"],
                labelId="INBOX",
            ).execute()
        except Exception as e:
            logger.error(f"Failed to get history: {e}")
            return []

        messages = []
        for record in results.get("history", []):
            for msg_added in record.get("messagesAdded", []):
                msg_id = msg_added["message"]["id"]
                try:
                    msg = self.service.users().messages().get(
                        userId="me", id=msg_id, format="full"
                    ).execute()
                    messages.append(self._parse_message(msg))
                except Exception as e:
                    logger.error(f"Failed to fetch message {msg_id}: {e}")
        return messages

    def _parse_message(self, msg: dict) -> dict:
        """Parse a Gmail API message into a simple dict."""
        headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}
        body = ""
        payload = msg["payload"]

        # Try to extract plain text body
        if payload.get("body", {}).get("data"):
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
        elif payload.get("parts"):
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain" and part.get("body", {}).get("data"):
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                    break

        return {
            "id": msg["id"],
            "threadId": msg["threadId"],
            "from": headers.get("from", ""),
            "to": headers.get("to", ""),
            "subject": headers.get("subject", ""),
            "body": body,
            "date": headers.get("date", ""),
            "labels": msg.get("labelIds", []),
        }
```

- [ ] **Step 2: Commit**

```bash
git add src/services/gmail_service.py
git commit -m "feat: add GmailService — send, read, search, watch, history"
```

---

### Task 5: Update Agent State and Tools

**Files:**
- Modify: `src/state.py`
- Create: `src/tools/payment_tools.py`
- Modify: `src/agent.py`
- Modify: `src/middleware/dynamic_tools.py`

- [ ] **Step 1: Update src/state.py — add Gmail fields**

Add two new fields to `InvoiceDisputeState` after `jurisdiction`:

```python
class InvoiceDisputeState(AgentState):
    client_name: str
    client_email: str
    invoice_amount: float
    invoice_id: str
    days_overdue: int
    escalation_level: int        # 1=friendly, 2=formal, 3=legal
    communication_history: list  # [{"type": str, "content": str, "timestamp": str}]
    jurisdiction: str            # e.g., "California", "England and Wales"
    gmail_thread_id: str         # Gmail thread ID for tracking replies
    gmail_message_ids: list      # List of sent message IDs
```

- [ ] **Step 2: Create src/tools/payment_tools.py**

```python
from langchain.tools import tool, ToolRuntime
from langgraph.types import Command
from langchain.messages import ToolMessage
from datetime import datetime, timezone


@tool
def mark_invoice_pending(follow_up_date: str, runtime: ToolRuntime) -> Command:
    """Mark an invoice as pending payment. The client has agreed to pay. Provide a follow-up date (YYYY-MM-DD) to check back."""
    invoice_id = runtime.state.get("invoice_id", "N/A")
    return Command(update={
        "messages": [ToolMessage(
            f"Invoice #{invoice_id} marked as PENDING. Client has agreed to pay. "
            f"Follow-up scheduled for {follow_up_date}.",
            tool_call_id=runtime.tool_call_id
        )]
    })


@tool
def mark_invoice_paid(runtime: ToolRuntime) -> Command:
    """Mark an invoice as paid. Use when payment has been confirmed."""
    invoice_id = runtime.state.get("invoice_id", "N/A")
    return Command(update={
        "messages": [ToolMessage(
            f"Invoice #{invoice_id} has been marked as PAID. Dispute resolved.",
            tool_call_id=runtime.tool_call_id
        )]
    })
```

- [ ] **Step 3: Update src/agent.py — register payment tools**

Replace the full contents of `src/agent.py`:

```python
from dotenv import load_dotenv

load_dotenv()

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.middleware import HumanInTheLoopMiddleware

from src.state import InvoiceDisputeState, FreelancerContext
from src.middleware.dynamic_tools import dynamic_tool_middleware
from src.middleware.dynamic_prompts import escalation_prompt

from src.tools.drafting import draft_polite_reminder, draft_formal_demand_letter, draft_final_notice
from src.tools.invoice import check_invoice_status, calculate_late_fees
from src.tools.legal import lookup_small_claims_procedures, generate_court_filing_guide
from src.tools.escalation import escalate_dispute, update_invoice_details
from src.tools.payment_tools import mark_invoice_pending, mark_invoice_paid

ALL_TOOLS = [
    update_invoice_details,
    check_invoice_status,
    draft_polite_reminder,
    escalate_dispute,
    draft_formal_demand_letter,
    calculate_late_fees,
    lookup_small_claims_procedures,
    generate_court_filing_guide,
    draft_final_notice,
    mark_invoice_pending,
    mark_invoice_paid,
]

model = init_chat_model("llama-3.3-70b-versatile", model_provider="groq")
checkpointer = InMemorySaver()

agent = create_agent(
    model=model,
    tools=ALL_TOOLS,
    checkpointer=checkpointer,
    state_schema=InvoiceDisputeState,
    context_schema=FreelancerContext,
    middleware=[
        dynamic_tool_middleware,
        escalation_prompt,
        HumanInTheLoopMiddleware(
            interrupt_on={
                "draft_polite_reminder": True,
                "draft_formal_demand_letter": True,
                "draft_final_notice": True,
                "mark_invoice_pending": True,
                "mark_invoice_paid": True,
                "update_invoice_details": False,
                "check_invoice_status": False,
                "calculate_late_fees": False,
                "escalate_dispute": False,
                "lookup_small_claims_procedures": False,
                "generate_court_filing_guide": False,
            },
            description_prefix="APPROVAL REQUIRED: Review this action before proceeding",
        ),
    ],
)
```

- [ ] **Step 4: Update src/middleware/dynamic_tools.py — add payment tools**

Replace the full contents:

```python
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from typing import Callable

from src.tools.drafting import draft_polite_reminder, draft_formal_demand_letter, draft_final_notice
from src.tools.invoice import check_invoice_status, calculate_late_fees
from src.tools.legal import lookup_small_claims_procedures, generate_court_filing_guide
from src.tools.escalation import escalate_dispute, update_invoice_details
from src.tools.payment_tools import mark_invoice_pending, mark_invoice_paid

# Tools available at each escalation level (progressive unlocking)
# Payment tools are available at all levels (client can reply/pay at any stage)
PAYMENT_TOOLS = [mark_invoice_pending, mark_invoice_paid]

LEVEL_0_TOOLS = [update_invoice_details]

LEVEL_1_TOOLS = [
    check_invoice_status,
    draft_polite_reminder,
    escalate_dispute,
    update_invoice_details,
] + PAYMENT_TOOLS

LEVEL_2_TOOLS = LEVEL_1_TOOLS + [
    draft_formal_demand_letter,
    calculate_late_fees,
]

LEVEL_3_TOOLS = LEVEL_2_TOOLS + [
    lookup_small_claims_procedures,
    generate_court_filing_guide,
    draft_final_notice,
]


@wrap_model_call
def dynamic_tool_middleware(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """Dynamically provide tools based on the current escalation level in state."""
    escalation_level = request.state.get("escalation_level", 0)

    if escalation_level <= 0:
        tools = LEVEL_0_TOOLS
    elif escalation_level == 1:
        tools = LEVEL_1_TOOLS
    elif escalation_level == 2:
        tools = LEVEL_2_TOOLS
    else:
        tools = LEVEL_3_TOOLS

    request = request.override(tools=tools)
    return handler(request)
```

- [ ] **Step 5: Commit**

```bash
git add src/state.py src/tools/payment_tools.py src/agent.py src/middleware/dynamic_tools.py
git commit -m "feat: add payment tools (mark_pending, mark_paid) with HITL + dynamic gating"
```

---

### Task 6: Update Prompts — Add Reply Analysis

**Files:**
- Modify: `src/prompts/v1/escalation_level_1.txt`
- Modify: `src/prompts/v1/escalation_level_2.txt`
- Modify: `src/prompts/v1/escalation_level_3.txt`

- [ ] **Step 1: Read current prompts**

Read all three prompt files to find the right insertion point.

- [ ] **Step 2: Append reply analysis section to each prompt**

Add the following block to the end of each of the three prompt files (`escalation_level_1.txt`, `escalation_level_2.txt`, `escalation_level_3.txt`):

```text

## Analyzing Client Replies

When a client reply is provided in the conversation, analyze the tone and content carefully:

- If the client agrees to pay → use mark_invoice_pending with a follow-up date (typically 7 days out)
- If the client disputes the amount or terms → summarize their objection clearly and suggest response options
- If the client ignores the issue or deflects → suggest escalation to the next level
- If payment is confirmed (e.g., payment receipt or bank notification) → use mark_invoice_paid

Always explain your reasoning before suggesting an action. Present your analysis and recommendation, then use the appropriate tool.
```

- [ ] **Step 3: Commit**

```bash
git add src/prompts/v1/
git commit -m "feat: add reply analysis instructions to all escalation prompts"
```

---

### Task 7: Backend — Google OAuth Endpoints

**Files:**
- Modify: `api/index.py`

- [ ] **Step 1: Add OAuth imports and config at top of api/index.py**

Replace the Resend imports and config (lines 20-33) with:

```python
import jwt
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from src.db import init_db, upsert_user, get_user, get_user_gmail_tokens
from src.services.gmail_service import GmailService, SCOPES

# Initialize database on startup
init_db()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5173/auth/google/callback")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
```

- [ ] **Step 2: Add JWT helper functions after the config block**

```python
def create_jwt(user_id: str, email: str) -> str:
    """Create a JWT session token."""
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc).timestamp() + 86400 * 7,  # 7 days
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def get_current_user(authorization: str | None) -> dict | None:
    """Decode JWT from Authorization header. Returns user dict or None."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return get_user(payload["user_id"])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
```

- [ ] **Step 3: Add OAuth endpoints after the health check route**

```python
@app.get("/api/auth/google/url")
def google_auth_url():
    """Return the Google OAuth consent URL."""
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI,
    )
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return {"url": auth_url}


class GoogleCallbackRequest(BaseModel):
    code: str


@app.post("/api/auth/google/callback")
def google_callback(req: GoogleCallbackRequest):
    """Exchange auth code for tokens, create/update user, return JWT."""
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI,
    )
    flow.fetch_token(code=req.code)
    credentials = flow.credentials

    # Get user info from Google
    import urllib.request
    import json as json_lib
    user_info_req = urllib.request.Request(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {credentials.token}"}
    )
    with urllib.request.urlopen(user_info_req) as resp:
        user_info = json_lib.loads(resp.read())

    user_id = user_info["id"]
    email = user_info["email"]
    name = user_info.get("name", "")
    picture = user_info.get("picture", "")

    # Upsert user with Gmail tokens
    upsert_user(
        user_id=user_id,
        email=email,
        name=name,
        picture=picture,
        access_token=credentials.token,
        refresh_token=credentials.refresh_token or "",
    )

    # Create JWT session
    token = create_jwt(user_id, email)

    return {
        "token": token,
        "user": {
            "id": user_id,
            "email": email,
            "name": name,
            "picture": picture,
        },
    }


@app.get("/api/auth/me")
def get_me(authorization: str | None = None):
    """Get current user from JWT."""
    from fastapi import Header
    # This will be called with the header
    return {"error": "Not authenticated"}, 401


# Override with proper header injection
from fastapi import Header, HTTPException

@app.get("/api/auth/me", response_model=None)
def get_me_route(authorization: str | None = Header(None)):
    """Get current user from JWT."""
    user = get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user.get("name", ""),
            "picture": user.get("picture", ""),
        }
    }
```

- [ ] **Step 4: Commit**

```bash
git add api/index.py
git commit -m "feat: add Google OAuth endpoints — sign-in, callback, session"
```

---

### Task 8: Backend — Replace Resend with Gmail, Add Webhook

**Files:**
- Modify: `api/index.py`

- [ ] **Step 1: Remove Resend send_email function and replace with Gmail**

Remove the `send_email` function (lines 179-199) and the Resend imports/config (already removed in Task 7). Replace with:

```python
def send_email_via_gmail(user_id: str, to_email: str, subject: str, body: str,
                         thread_id: str | None = None) -> dict | None:
    """Send an email via Gmail API. Returns {id, threadId} or None on failure."""
    tokens = get_user_gmail_tokens(user_id)
    if not tokens:
        logger.warning(f"No Gmail tokens for user {user_id} — skipping email send")
        return None
    try:
        gmail = GmailService(user_id, tokens[0], tokens[1])
        result = gmail.send_email(to_email, subject, body, thread_id)
        logger.info(f"Email sent via Gmail: {result}")
        return result
    except Exception as e:
        logger.error(f"Failed to send email via Gmail: {e}")
        return None
```

- [ ] **Step 2: Update the resume endpoint to use Gmail instead of Resend**

In the `resume` function, replace the email sending block. Where it currently calls `send_email(client_email, approved_subject, body)`, change to:

```python
# Get user_id from the request (we'll need to pass this)
# For now, get the first user from DB
from src.db import get_db
conn = get_db()
user_row = conn.execute("SELECT id FROM users LIMIT 1").fetchone()
conn.close()
user_id = user_row["id"] if user_row else None

if user_id and draft and client_email:
    approved_subject, body = parse_draft_subject_and_body(draft)
    # Get existing gmail_thread_id for this invoice
    invoice_data = get_invoice(invoice_id)
    gmail_thread_id = invoice_data.get("gmail_thread_id") if invoice_data else None
    email_result = send_email_via_gmail(user_id, client_email, approved_subject, body, gmail_thread_id)
    # Store the gmail_thread_id if this is the first email in the thread
    if email_result and not gmail_thread_id:
        update_invoice(invoice_id, gmail_thread_id=email_result["threadId"])
```

Also add the import at the top: `from src.db import get_invoice, update_invoice`

- [ ] **Step 3: Add Gmail webhook endpoint**

Add after the resume endpoint:

```python
from src.services.telegram_service import send_telegram_notification
from src.db import (
    get_invoices_by_client_email, add_communication,
    update_user_history_id, get_user
)
import base64 as b64
import json as json_module


class PubSubMessage(BaseModel):
    message: dict
    subscription: str


@app.post("/api/gmail/webhook")
def gmail_webhook(payload: PubSubMessage):
    """Handle Gmail push notifications from Pub/Sub."""
    try:
        # Decode the Pub/Sub message
        data = json_module.loads(
            b64.b64decode(payload.message.get("data", "")).decode()
        )
        email_address = data.get("emailAddress", "")
        history_id = str(data.get("historyId", ""))

        logger.info(f"Gmail webhook: email={email_address}, historyId={history_id}")

        # Find the user by email
        conn = get_db()
        user_row = conn.execute("SELECT * FROM users WHERE email = ?", (email_address,)).fetchone()
        conn.close()

        if not user_row:
            logger.warning(f"No user found for email {email_address}")
            return {"status": "ok"}

        user = dict(user_row)
        last_history_id = user.get("gmail_history_id")

        if not last_history_id:
            # First notification — just store the history ID
            update_user_history_id(user["id"], history_id)
            return {"status": "ok"}

        # Get new messages since last history ID
        tokens = get_user_gmail_tokens(user["id"])
        if not tokens:
            return {"status": "ok"}

        gmail = GmailService(user["id"], tokens[0], tokens[1])
        new_messages = gmail.get_history(last_history_id)

        # Update history ID
        update_user_history_id(user["id"], history_id)

        # Process each new inbound message
        for msg in new_messages:
            from_addr = msg.get("from", "")
            # Skip our own sent messages
            if email_address.lower() in from_addr.lower():
                continue

            # Extract sender email from "Name <email>" format
            sender_email = from_addr
            if "<" in from_addr:
                sender_email = from_addr.split("<")[1].rstrip(">")

            # Find matching invoices for this sender
            matching_invoices = get_invoices_by_client_email(sender_email)

            for invoice in matching_invoices:
                # Log the communication
                add_communication(
                    invoice_id=invoice["id"],
                    comm_type="client_reply",
                    subject=msg.get("subject", ""),
                    content=msg.get("body", "")[:2000],
                    direction="inbound",
                )

                # Feed to agent for analysis
                config = {"configurable": {"thread_id": f"invoice-{invoice['id']}"}}
                context = get_context_for_invoice(invoice["id"])
                agent_msg = (
                    f"[INCOMING CLIENT REPLY]\n"
                    f"From: {from_addr}\n"
                    f"Subject: {msg.get('subject', 'No subject')}\n\n"
                    f"{msg.get('body', '')[:2000]}\n\n"
                    f"Please analyze this reply and suggest the appropriate next action."
                )
                try:
                    agent.invoke(
                        {"messages": [HumanMessage(content=agent_msg)]},
                        context=context,
                        config=config,
                    )
                except Exception as e:
                    logger.error(f"Agent failed to process reply for invoice {invoice['id']}: {e}")

                # Send Telegram notification
                send_telegram_notification(
                    f"📩 <b>Client Reply</b>\n"
                    f"Invoice: #{invoice['id']}\n"
                    f"From: {from_addr}\n"
                    f"Subject: {msg.get('subject', 'No subject')}\n\n"
                    f"{msg.get('body', '')[:200]}"
                )

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Gmail webhook error: {e}", exc_info=True)
        return {"status": "error"}
```

- [ ] **Step 4: Add Gmail watch setup on auth**

In the `google_callback` endpoint, after upserting the user, add:

```python
    # Register for Gmail push notifications
    try:
        gmail = GmailService(user_id, credentials.token, credentials.refresh_token)
        topic = os.getenv("GOOGLE_PUBSUB_TOPIC", "")
        if topic:
            watch_result = gmail.watch_inbox(topic)
            update_user_history_id(user_id, str(watch_result.get("historyId", "")))
    except Exception as e:
        logger.warning(f"Failed to set up Gmail watch: {e}")
```

- [ ] **Step 5: Replace in-memory INVOICES_STORE with SQLite**

Replace `INVOICES_STORE = {}` and `SENDER_OVERRIDES = {}` with SQLite calls. Update these routes:

- `list_invoices` → `get_invoices_by_user(user_id)` (need user_id from JWT)
- `create_invoice` → `db.create_invoice(...)`
- Update local store references in `resume` and other endpoints

This is a larger refactor — update each endpoint to read/write from SQLite instead of the in-memory dict. The JWT `Authorization` header should be passed to identify the user.

- [ ] **Step 6: Commit**

```bash
git add api/index.py
git commit -m "feat: replace Resend with Gmail, add Pub/Sub webhook, SQLite storage"
```

---

### Task 9: Frontend — Auth Context and Google OAuth Flow

**Files:**
- Create: `frontend/src/contexts/AuthContext.tsx`
- Create: `frontend/src/pages/GoogleCallback.tsx`
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/types.ts`

- [ ] **Step 1: Add User type to frontend/src/types.ts**

Add at the end of the file:

```typescript
export interface User {
  id: string;
  email: string;
  name: string;
  picture: string;
}
```

- [ ] **Step 2: Update frontend/src/api.ts — add auth calls and JWT header**

Replace the full contents:

```typescript
const BASE_URL = import.meta.env.VITE_API_URL || '';

function getAuthHeader(): Record<string, string> {
  const token = localStorage.getItem('invoicechaser_token');
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeader(),
    },
    ...options,
  });
  if (!res.ok) {
    if (res.status === 401) {
      localStorage.removeItem('invoicechaser_token');
      localStorage.removeItem('invoicechaser_user');
      window.location.href = '/';
    }
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json();
}

export const api = {
  // Auth
  getGoogleAuthUrl: () =>
    request<{ url: string }>('/api/auth/google/url'),

  googleCallback: (code: string) =>
    request<{ token: string; user: import('./types').User }>('/api/auth/google/callback', {
      method: 'POST',
      body: JSON.stringify({ code }),
    }),

  getMe: () =>
    request<{ user: import('./types').User }>('/api/auth/me'),

  // Invoices
  getInvoices: () => request<import('./types').Invoice[]>('/api/invoices'),

  getHistory: (invoiceId: string) =>
    request<import('./types').ChatResponse>(`/api/invoices/${invoiceId}/history`),

  updateDetails: (invoiceId: string, data: { client_name?: string; client_email?: string }) =>
    request<{ state: import('./types').AgentState }>(`/api/invoices/${invoiceId}/details`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  getSender: (invoiceId: string) =>
    request<{ freelancer_name: string; freelancer_email: string; business_name: string }>(
      `/api/invoices/${invoiceId}/sender`
    ),

  updateSender: (invoiceId: string, data: { freelancer_name?: string; freelancer_email?: string; business_name?: string }) =>
    request<{ freelancer_name: string; freelancer_email: string; business_name: string }>(
      `/api/invoices/${invoiceId}/sender`,
      { method: 'PATCH', body: JSON.stringify(data) }
    ),

  createInvoice: (data: {
    invoice_id: string;
    client_name: string;
    client_email: string;
    invoice_amount: number;
    days_overdue: number;
    jurisdiction: string;
  }) =>
    request<import('./types').InvoiceCreateResponse>('/api/invoices', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  chat: (thread_id: string, message: string) =>
    request<import('./types').ChatResponse>('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ thread_id, message }),
    }),

  resume: (
    invoice_id: string,
    decision: string,
    message?: string,
    edited_action?: Record<string, unknown>
  ) =>
    request<import('./types').ChatResponse>(
      `/api/invoices/${invoice_id}/resume`,
      {
        method: 'POST',
        body: JSON.stringify({ decision, message, edited_action }),
      }
    ),
};
```

- [ ] **Step 3: Create frontend/src/contexts/AuthContext.tsx**

```tsx
import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { api } from '../api'
import type { User } from '../types'

interface AuthContextType {
  user: User | null
  loading: boolean
  signIn: () => Promise<void>
  signOut: () => void
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('invoicechaser_token')
    const savedUser = localStorage.getItem('invoicechaser_user')
    if (token && savedUser) {
      setUser(JSON.parse(savedUser))
    }
    setLoading(false)
  }, [])

  const signIn = async () => {
    const { url } = await api.getGoogleAuthUrl()
    window.location.href = url
  }

  const signOut = () => {
    localStorage.removeItem('invoicechaser_token')
    localStorage.removeItem('invoicechaser_user')
    setUser(null)
    window.location.href = '/'
  }

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

export function handleGoogleCallback(token: string, user: User) {
  localStorage.setItem('invoicechaser_token', token)
  localStorage.setItem('invoicechaser_user', JSON.stringify(user))
}
```

- [ ] **Step 4: Create frontend/src/pages/GoogleCallback.tsx**

```tsx
import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api'
import { handleGoogleCallback } from '../contexts/AuthContext'

export default function GoogleCallback() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [error, setError] = useState('')

  useEffect(() => {
    const code = searchParams.get('code')
    if (!code) {
      setError('No authorization code received')
      return
    }

    api.googleCallback(code)
      .then(({ token, user }) => {
        handleGoogleCallback(token, user)
        navigate('/dashboard', { replace: true })
        window.location.reload()
      })
      .catch((err) => {
        setError(err.message)
      })
  }, [searchParams, navigate])

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-950 text-white">
        <div className="text-center">
          <p className="text-red-400 text-lg mb-4">Sign-in failed: {error}</p>
          <a href="/" className="text-blue-400 underline">Back to home</a>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-950 text-white">
      <p className="text-lg">Signing you in...</p>
    </div>
  )
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/contexts/ frontend/src/pages/ frontend/src/api.ts frontend/src/types.ts
git commit -m "feat: add Google OAuth frontend — auth context, callback page, JWT handling"
```

---

### Task 10: Frontend — Update App Routes and Landing Page

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/LandingPage.tsx`
- Modify: `frontend/src/components/Layout.tsx`
- Modify: `frontend/src/main.tsx`

- [ ] **Step 1: Update frontend/src/App.tsx**

Replace the full contents:

```tsx
import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './components/Dashboard'
import ChatPanel from './components/ChatPanel'
import LandingPage from './components/LandingPage'
import GoogleCallback from './pages/GoogleCallback'
import { useAuth } from './contexts/AuthContext'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return null
  if (!user) return <Navigate to="/" replace />
  return <>{children}</>
}

function App() {
  const { user, loading } = useAuth()

  if (loading) return null

  return (
    <Routes>
      {/* Landing page — public */}
      <Route path="/" element={
        user ? <Navigate to="/dashboard" replace /> : <LandingPage />
      } />

      {/* OAuth callback */}
      <Route path="/auth/google/callback" element={<GoogleCallback />} />

      {/* App routes — protected */}
      <Route path="/dashboard" element={
        <ProtectedRoute>
          <Layout>
            <Dashboard />
          </Layout>
        </ProtectedRoute>
      } />
      <Route path="/invoice/:invoiceId" element={
        <ProtectedRoute>
          <Layout>
            <ChatPanel />
          </Layout>
        </ProtectedRoute>
      } />
    </Routes>
  )
}

export default App
```

- [ ] **Step 2: Update frontend/src/main.tsx — wrap with AuthProvider**

Read the current `main.tsx` first, then wrap the `<App />` with `<AuthProvider>`:

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import App from './App'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
```

- [ ] **Step 3: Update LandingPage.tsx — replace mock sign-in with Google OAuth**

Find the current sign-in button/handler in `LandingPage.tsx`. It currently stores a mock user in localStorage. Replace that handler with:

```typescript
import { useAuth } from '../contexts/AuthContext'

// Inside the component:
const { signIn } = useAuth()

// Replace the button's onClick to call signIn():
// onClick={signIn}
```

Remove the old mock authentication logic (the `localStorage.setItem('invoicechaser_user', ...)` pattern).

The button text should change from whatever it currently says to "Sign in with Google".

- [ ] **Step 4: Update Layout.tsx — show user info and sign-out**

Read `Layout.tsx` first. Add the user's avatar, email, and sign-out button to the header:

```tsx
import { useAuth } from '../contexts/AuthContext'

// Inside Layout component:
const { user, signOut } = useAuth()

// In the header, add:
{user && (
  <div className="flex items-center gap-3">
    {user.picture && (
      <img src={user.picture} alt="" className="w-8 h-8 rounded-full" />
    )}
    <span className="text-sm text-zinc-400">{user.email}</span>
    <button
      onClick={signOut}
      className="text-sm text-zinc-500 hover:text-white transition-colors"
    >
      Sign out
    </button>
  </div>
)}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/main.tsx frontend/src/components/LandingPage.tsx frontend/src/components/Layout.tsx
git commit -m "feat: integrate Google OAuth in frontend — routes, landing page, layout"
```

---

### Task 11: Frontend — Display Inbound Emails in Chat

**Files:**
- Modify: `frontend/src/components/ChatPanel.tsx`
- Modify: `frontend/src/components/MessageBubble.tsx`

- [ ] **Step 1: Read ChatPanel.tsx and MessageBubble.tsx**

Read both files to understand the current message rendering.

- [ ] **Step 2: Update MessageBubble.tsx — add inbound email styling**

Add handling for messages that start with `[INCOMING CLIENT REPLY]`. These should render with a distinct style:

```tsx
// Inside MessageBubble, detect inbound emails:
const isInboundEmail = content.startsWith('[INCOMING CLIENT REPLY]')

// Render with different styling:
// - Left-aligned (like received messages)
// - Blue/indigo accent border
// - "Client Reply" label
// - Mail icon from lucide-react
```

- [ ] **Step 3: Update ChatPanel.tsx — handle inbound messages**

The ChatPanel should poll or refresh when new inbound messages arrive. Add a periodic refresh (every 30 seconds) to check for new messages:

```typescript
useEffect(() => {
  const interval = setInterval(() => {
    // Refresh conversation history to pick up webhook-injected messages
    loadHistory()
  }, 30000)
  return () => clearInterval(interval)
}, [invoiceId])
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ChatPanel.tsx frontend/src/components/MessageBubble.tsx
git commit -m "feat: display inbound client emails in chat with distinct styling"
```

---

### Task 12: Backend — Migrate Existing Routes to SQLite

**Files:**
- Modify: `api/index.py`

- [ ] **Step 1: Update list_invoices to use SQLite**

```python
@app.get("/api/invoices")
def list_invoices(authorization: str | None = Header(None)):
    user = get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    invoices = get_invoices_by_user(user["id"])
    # Add communication_history to each invoice
    for inv in invoices:
        inv["communication_history"] = get_communications(inv["id"])
    return invoices
```

- [ ] **Step 2: Update create_invoice to use SQLite**

```python
@app.post("/api/invoices")
def create_invoice_route(req: InvoiceCreateRequest, authorization: str | None = Header(None)):
    user = get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    invoice = db_create_invoice(
        invoice_id=req.invoice_id,
        user_id=user["id"],
        client_name=req.client_name,
        client_email=req.client_email,
        invoice_amount=req.invoice_amount,
        days_overdue=req.days_overdue,
        jurisdiction=req.jurisdiction,
    )

    # Initialize agent state
    context = get_context_for_invoice(req.invoice_id)
    config = {"configurable": {"thread_id": f"invoice-{req.invoice_id}"}}
    msg = (
        f"I have an overdue invoice. Here are the details:\n"
        f"Client: {req.client_name} ({req.client_email})\n"
        f"Invoice ID: {req.invoice_id}\n"
        f"Amount: ${req.invoice_amount:.2f}\n"
        f"Days overdue: {req.days_overdue}\n"
        f"Jurisdiction: {req.jurisdiction}\n\n"
        f"Please save these details."
    )
    response = agent.invoke(
        {"messages": [HumanMessage(content=msg)]},
        context=context,
        config=config,
    )

    invoice["communication_history"] = []
    return {
        "invoice": invoice,
        "messages": serialize_messages(response["messages"]),
        "interrupt": extract_interrupt(response, context),
        "state": extract_state(response),
    }
```

- [ ] **Step 3: Update resume endpoint to use SQLite and Gmail**

Update the resume endpoint to:
- Use `send_email_via_gmail` instead of `send_email`
- Store communication in SQLite via `add_communication`
- Update invoice escalation_level and gmail_thread_id in SQLite

- [ ] **Step 4: Remove INVOICES_STORE and SENDER_OVERRIDES**

Delete the in-memory dicts and all references to them. Replace with SQLite queries.

Import the renamed DB function:

```python
from src.db import (
    init_db, upsert_user, get_user, get_user_gmail_tokens,
    create_invoice as db_create_invoice, get_invoice, get_invoices_by_user,
    update_invoice, get_invoices_by_client_email,
    add_communication, get_communications,
    update_user_history_id,
)
```

- [ ] **Step 5: Commit**

```bash
git add api/index.py
git commit -m "feat: migrate all routes from in-memory storage to SQLite"
```

---

### Task 13: Add Telegram Notifications to Key Events

**Files:**
- Modify: `api/index.py`

- [ ] **Step 1: Add Telegram notification on escalation**

In the `chat` endpoint, after the agent responds, check if the escalation level changed and notify:

```python
# After agent.invoke in chat endpoint
new_level = response.get("escalation_level", 0)
old_state = extract_state(agent.get_state(config).values) if False else {}
# Check if level changed by comparing with invoice in DB
invoice_data = get_invoice(inv_id)
if invoice_data and new_level > invoice_data.get("escalation_level", 0):
    update_invoice(inv_id, escalation_level=new_level)
    level_names = {1: "Friendly", 2: "Formal", 3: "Legal"}
    send_telegram_notification(
        f"⚠️ <b>Escalation</b>\n"
        f"Invoice #{inv_id} escalated to Level {new_level} ({level_names.get(new_level, 'Unknown')})"
    )
```

- [ ] **Step 2: Add Telegram notification on email sent**

In the `resume` endpoint, after successfully sending an email:

```python
if email_result:
    send_telegram_notification(
        f"📤 <b>Email Sent</b>\n"
        f"Invoice: #{invoice_id}\n"
        f"To: {client_email}\n"
        f"Subject: {approved_subject}"
    )
```

- [ ] **Step 3: Commit**

```bash
git add api/index.py
git commit -m "feat: add Telegram notifications for escalation and email events"
```

---

### Task 14: End-to-End Testing

- [ ] **Step 1: Verify backend starts**

Run: `python -m uvicorn api.index:app --reload --port 8000`

Expected: Server starts without import errors.

- [ ] **Step 2: Verify frontend starts**

Run: `cd frontend && npm run dev`

Expected: Vite dev server starts.

- [ ] **Step 3: Test Google OAuth flow**

1. Open `http://localhost:5173`
2. Click "Sign in with Google"
3. Complete Google consent screen
4. Verify redirect back to `/dashboard`
5. Verify user avatar and email shown in header

- [ ] **Step 4: Test invoice creation and email sending**

1. Create a new invoice on the dashboard
2. Ask the agent to draft a polite reminder
3. Approve the draft
4. Verify email is sent via Gmail (check sent folder)
5. Verify Telegram notification received

- [ ] **Step 5: Test Gmail webhook (inbound)**

1. Reply to the email sent in step 4 from the client's email
2. Verify Pub/Sub pushes notification to webhook
3. Verify reply appears in the chat panel
4. Verify agent analyzes the reply
5. Verify Telegram notification received

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "feat: complete Gmail + Telegram integration — OAuth, send/receive, push notifications"
```
