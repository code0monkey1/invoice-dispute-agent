from dotenv import load_dotenv

load_dotenv()

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
import os
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

def _make_checkpointer():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if DATABASE_URL:
        try:
            import psycopg
            from langgraph.checkpoint.postgres import PostgresSaver
            # Supabase requires SSL
            url = DATABASE_URL if "sslmode" in DATABASE_URL else DATABASE_URL + "?sslmode=require"
            conn = psycopg.connect(url)
            cp = PostgresSaver(conn)
            cp.setup()
            print("[agent] PostgresSaver initialized successfully")
            return cp
        except Exception as e:
            import traceback
            print(f"[agent] PostgresSaver failed: {e}\n{traceback.format_exc()}")
    import sqlite3
    from langgraph.checkpoint.sqlite import SqliteSaver
    # Use local file in dev, /tmp on Vercel (read-only filesystem outside /tmp)
    db_path = ".checkpoints.db" if os.access(".", os.W_OK) else "/tmp/.checkpoints.db"
    return SqliteSaver(sqlite3.connect(db_path, check_same_thread=False))

checkpointer = _make_checkpointer()

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
                "update_invoice_details": False,
                "check_invoice_status": False,
                "calculate_late_fees": False,
                "escalate_dispute": False,
                "lookup_small_claims_procedures": False,
                "generate_court_filing_guide": False,
                "mark_invoice_pending": True,
                "mark_invoice_paid": True,
            },
            description_prefix="APPROVAL REQUIRED: Review this draft before sending",
        ),
    ],
)
