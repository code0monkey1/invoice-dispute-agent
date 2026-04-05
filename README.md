<div align="center">

# InvoiceChaser

### AI-Powered Invoice Dispute & Payment Recovery Agent

An intelligent agent that helps freelancers chase overdue payments through **progressive escalation** — from friendly reminders to formal demands to legal action — with human-in-the-loop approval at every step.

**Built with LangChain | Groq | React | FastAPI** *(LangGraph used for checkpointing & state Commands)*

[Live Demo](#) &nbsp;&bull;&nbsp; [Architecture](#architecture) &nbsp;&bull;&nbsp; [How It Works](#how-it-works) &nbsp;&bull;&nbsp; [Setup](#getting-started) &nbsp;&bull;&nbsp; [GenAI Deep Dive](#genai-technologies--how-they-help)

</div>

---

## Why This Exists

Freelancers lose **$825 billion annually** to late payments. Most either:
- Give up chasing (lost revenue)
- Send awkward manual follow-ups (uncomfortable + time-consuming)
- Hire collections agencies too early (expensive + damages client relationships)

**InvoiceChaser fills the gap**: an AI agent that progressively escalates from gentle nudges to legal action, drafting every communication for you, while keeping you in full control with approve/edit/reject at every step.

> **What makes this unique:** Invoice tools and payment reminders exist separately. But an AI agent that **dynamically unlocks harder tools and shifts its communication tone based on dispute state** — progressively escalating its strategy as the situation demands — doesn't exist anywhere else. This is a genuinely novel approach to payment recovery.

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Progressive Escalation** | 3-level system: Friendly → Formal → Legal. Each level unlocks new AI capabilities |
| **Dynamic Tool Gating** | Agent's available tools change based on escalation level — it literally cannot use legal tools at Level 1 |
| **Tone-Shifting AI** | System prompt dynamically changes per level — warm at Level 1, firm at Level 2, legal language at Level 3 |
| **Human-in-the-Loop** | Every outbound draft requires your explicit approval before "sending" |
| **Late Fee Calculator** | Automatically computes late fees based on your contract terms |
| **Legal Research** | At Level 3, uses Tavily web search to research small claims court procedures for the client's jurisdiction |
| **Court Filing Guide** | Generates step-by-step filing instructions based on real jurisdiction data |
| **Conversation Memory** | Full conversation history per client thread — the agent remembers everything |
| **Real-Time Dashboard** | Track all disputes, amounts owed, escalation levels at a glance |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              VERCEL (Free Tier)                                  │
│                                                                                  │
│  ┌────────────────────────────┐         ┌──────────────────────────────────────┐  │
│  │     React Frontend         │  fetch  │       FastAPI Serverless             │  │
│  │     (Vite + Tailwind v4)   │ ──────▶ │       (api/index.py)                │  │
│  │                            │         │                                      │  │
│  │  ┌──────────────────────┐  │         │  POST /api/chat ──────────────────┐  │  │
│  │  │ Dashboard            │  │         │  POST /api/invoices               │  │  │
│  │  │ - Stats Cards        │  │         │  POST /api/invoices/{id}/resume   │  │  │
│  │  │ - Invoice Table      │  │         │  GET  /api/invoices               │  │  │
│  │  │ - Create Form        │  │         │                                   │  │  │
│  │  └──────────────────────┘  │         │  ┌───────────────────────────┐    │  │  │
│  │  ┌──────────────────────┐  │         │  │   LangChain/LangGraph    │    │  │  │
│  │  │ Chat Panel           │  │ ◀────── │  │   Agent Pipeline         │    │  │  │
│  │  │ - Message Bubbles    │  │   JSON  │  │                          │    │  │  │
│  │  │ - HITL Approval Card │  │         │  │  ┌─ Dynamic Tools MW ──┐ │    │  │  │
│  │  │ - Escalation Sidebar │  │         │  │  │  @wrap_model_call   │ │    │  │  │
│  │  │ - Communication Log  │  │         │  │  │  Level-based gating │ │    │  │  │
│  │  └──────────────────────┘  │         │  │  └─────────────────────┘ │    │  │  │
│  └────────────────────────────┘         │  │  ┌─ Dynamic Prompt MW ─┐ │    │  │  │
│                                         │  │  │  @dynamic_prompt    │ │    │  │  │
│                                         │  │  │  Tone shifting      │ │    │  │  │
│                                         │  │  └─────────────────────┘ │    │  │  │
│                                         │  │  ┌─ HITL MW ───────────┐ │    │  │  │
│                                         │  │  │  Interrupt on drafts│ │    │  │  │
│                                         │  │  │  Approve/Edit/Reject│ │    │  │  │
│                                         │  │  └─────────────────────┘ │    │  │  │
│                                         │  │  ┌─ InMemorySaver ─────┐ │    │  │  │
│                                         │  │  │  Thread-based memory│ │    │  │  │
│                                         │  │  └─────────────────────┘ │    │  │  │
│                                         │  └───────────────────────────┘    │  │  │
│                                         └──────────────────────────────────────┘  │
│                                                        │                         │
│                                              ┌─────────┴──────────┐              │
│                                              │                    │              │
│                                         ┌────▼─────┐      ┌──────▼──────┐       │
│                                         │ Groq API │      │ Tavily API  │       │
│                                         │ (free)   │      │ (free)      │       │
│                                         │ LLaMA 3  │      │ Web Search  │       │
│                                         └──────────┘      └─────────────┘       │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## How It Works

### Sequence Diagram: Full Dispute Lifecycle

```
User                Frontend              Backend/Agent            Groq LLM           Tavily
 │                    │                       │                      │                  │
 │  Create Invoice    │                       │                      │                  │
 ├───────────────────▶│  POST /api/invoices   │                      │                  │
 │                    ├──────────────────────▶│                      │                  │
 │                    │                       │  invoke(HumanMsg)    │                  │
 │                    │                       ├─────────────────────▶│                  │
 │                    │                       │                      │                  │
 │                    │                       │  ◀── Tool Call: ─────┤                  │
 │                    │                       │  update_invoice_     │                  │
 │                    │                       │  details             │                  │
 │                    │                       │                      │                  │
 │                    │                       │  Command(update={    │                  │
 │                    │                       │    escalation: 1,    │                  │
 │                    │                       │    client_name: ...  │                  │
 │                    │                       │  })                  │                  │
 │                    │  ◀── state + msgs ────┤                      │                  │
 │  ◀── Dashboard ────┤                       │                      │                  │
 │                    │                       │                      │                  │
 │  "Draft a reminder"│                       │                      │                  │
 ├───────────────────▶│  POST /api/chat       │                      │                  │
 │                    ├──────────────────────▶│                      │                  │
 │                    │                       │                      │                  │
 │                    │                       │  ── Dynamic Tools MW ──────────────────────
 │                    │                       │  │ Level 1: only                        │
 │                    │                       │  │ [check_invoice_status,               │
 │                    │                       │  │  draft_polite_reminder,              │
 │                    │                       │  │  escalate_dispute,                   │
 │                    │                       │  │  update_invoice_details]             │
 │                    │                       │  └─────────────────────────────────────────
 │                    │                       │                      │                  │
 │                    │                       │  ── Dynamic Prompt MW ─────────────────────
 │                    │                       │  │ "Tone: Warm, empathetic.            │
 │                    │                       │  │  Assume best intentions."            │
 │                    │                       │  └─────────────────────────────────────────
 │                    │                       │                      │                  │
 │                    │                       │  invoke(tools=L1)    │                  │
 │                    │                       ├─────────────────────▶│                  │
 │                    │                       │                      │                  │
 │                    │                       │  ◀── Tool Call: ─────┤                  │
 │                    │                       │  draft_polite_       │                  │
 │                    │                       │  reminder            │                  │
 │                    │                       │                      │                  │
 │                    │                       │  ── HITL MW ───────────────────────────────
 │                    │                       │  │ INTERRUPT!                           │
 │                    │                       │  │ "draft_polite_reminder"              │
 │                    │                       │  │ requires human approval              │
 │                    │                       │  └─────────────────────────────────────────
 │                    │                       │                      │                  │
 │                    │  ◀── interrupt: ──────┤                      │                  │
 │                    │  {tool, args, draft}  │                      │                  │
 │                    │                       │                      │                  │
 │  ◀── HITL Card ────┤                       │                      │                  │
 │  [Approve] [Edit]  │                       │                      │                  │
 │  [Reject]          │                       │                      │                  │
 │                    │                       │                      │                  │
 │  Click "Approve"   │                       │                      │                  │
 ├───────────────────▶│ POST /resume          │                      │                  │
 │                    ├──────────────────────▶│                      │                  │
 │                    │                       │  Command(resume={    │                  │
 │                    │                       │    decisions:        │                  │
 │                    │                       │    [{type:"approve"}]│                  │
 │                    │                       │  })                  │                  │
 │                    │  ◀── response ────────┤                      │                  │
 │  ◀── "Email sent!" │                       │                      │                  │
 │                    │                       │                      │                  │
 │  Click "Escalate   │                       │                      │                  │
 │   to Level 2"      │                       │                      │                  │
 ├───────────────────▶│  POST /api/chat       │                      │                  │
 │                    ├──────────────────────▶│                      │                  │
 │                    │                       │  ◀── Tool Call: ─────┤                  │
 │                    │                       │  escalate_dispute    │                  │
 │                    │                       │                      │                  │
 │                    │                       │  Command(update={    │                  │
 │                    │                       │   escalation_level:2 │                  │
 │                    │                       │  })                  │                  │
 │                    │                       │                      │                  │
 │                    │                       │  ── Dynamic Tools ────────────────────────
 │                    │                       │  │ Level 2: UNLOCKS                    │
 │                    │                       │  │ + draft_formal_demand_letter         │
 │                    │                       │  │ + calculate_late_fees               │
 │                    │                       │  └─────────────────────────────────────────
 │                    │                       │                      │                  │
 │                    │                       │  ── Dynamic Prompt ───────────────────────
 │                    │                       │  │ "Tone: Professional, firm.          │
 │                    │                       │  │  Reference contract terms."          │
 │                    │                       │  └─────────────────────────────────────────
 │                    │                       │                      │                  │
 │  ◀── Level 2 ──────┤  Badge turns amber   │                      │                  │
 │                    │                       │                      │                  │
 │  "Draft a formal   │                       │                      │                  │
 │   demand letter"   │                       │                      │                  │
 ├───────────────────▶│ ────────────────────▶│ ────────────────────▶│                  │
 │                    │                       │  ◀── calculate_late_ │                  │
 │                    │                       │      fees + draft_   │                  │
 │                    │                       │      formal_demand   │                  │
 │                    │  ◀── HITL interrupt ──┤                      │                  │
 │  ◀── Approve Card  │                       │                      │                  │
 │                    │                       │                      │                  │
 │  Escalate to L3    │                       │                      │                  │
 ├───────────────────▶│ ────────────────────▶│ ────────────────────▶│                  │
 │                    │                       │                      │                  │
 │                    │                       │  ── Dynamic Tools ────────────────────────
 │                    │                       │  │ Level 3: UNLOCKS                    │
 │                    │                       │  │ + lookup_small_claims_procedures     │
 │                    │                       │  │ + generate_court_filing_guide        │
 │                    │                       │  │ + draft_final_notice                │
 │                    │                       │  └─────────────────────────────────────────
 │                    │                       │                      │                  │
 │  "Research court   │                       │                      │                  │
 │   procedures"      │                       │                      │                  │
 ├───────────────────▶│ ────────────────────▶│ ────────────────────▶│                  │
 │                    │                       │                      │   Tavily Search  │
 │                    │                       │                      ├─────────────────▶│
 │                    │                       │                      │  ◀── Results ────┤
 │                    │                       │  ◀── Legal research ─┤                  │
 │  ◀── Court filing  │  ◀── response ───────┤                      │                  │
 │     instructions   │                       │                      │                  │
 │                    │                       │                      │                  │
```

### Sequence Diagram: Human-in-the-Loop (HITL) Decision Flow

```
                          ┌──────────────┐
                          │  Agent calls  │
                          │  draft tool   │
                          └──────┬───────┘
                                 │
                    ┌────────────▼────────────┐
                    │   HITL Middleware        │
                    │   Checks: is this tool  │
                    │   in interrupt_on dict?  │
                    └────────────┬────────────┘
                                 │
                          ┌──────▼──────┐
                          │  INTERRUPT   │
                          │  Agent pauses│
                          │  Returns     │
                          │  draft to UI │
                          └──────┬──────┘
                                 │
               ┌─────────────────▼─────────────────┐
               │        User Reviews Draft          │
               │                                    │
               │  ┌──────────────────────────────┐  │
               │  │  "Subject: Payment Reminder  │  │
               │  │   Dear [Client Name],        │  │
               │  │   I hope this finds you..."  │  │
               │  └──────────────────────────────┘  │
               │                                    │
               │  [Approve & Send]  [Edit]  [Reject]│
               └──────┬──────────────┬──────────┬───┘
                      │              │          │
              ┌───────▼──┐    ┌──────▼───┐  ┌───▼───────┐
              │ APPROVE  │    │  EDIT    │  │  REJECT   │
              │          │    │          │  │           │
              │ Command( │    │ User     │  │ Command(  │
              │  resume: │    │ modifies │  │  resume:  │
              │  {type:  │    │ the text │  │  {type:   │
              │  approve}│    │          │  │  reject,  │
              │ )        │    │ Command( │  │  message: │
              │          │    │  resume: │  │  "reason"}│
              │ Agent    │    │  {type:  │  │ )         │
              │ continues│    │  edit,   │  │           │
              │ & "sends"│    │  edited} │  │ Agent     │
              │ the draft│    │ )        │  │ revises & │
              └──────────┘    └──────────┘  │ re-drafts │
                                            └───────────┘
```

### Sequence Diagram: Dynamic Tool Gating (State Machine)

```
                    ┌─────────────────────────┐
                    │      Level 0            │
                    │      (No Invoice)       │
                    │                         │
                    │  Tools:                 │
                    │  - update_invoice_      │
                    │    details              │
                    └───────────┬─────────────┘
                                │
                    update_invoice_details()
                    Command(update={
                      escalation_level: 1
                    })
                                │
                    ┌───────────▼─────────────┐
                    │      Level 1            │
                    │      (Friendly)         │
                    │                         │
                    │  Tone: Warm, empathetic │
                    │                         │
                    │  Tools:                 │
                    │  - check_invoice_status │
                    │  - draft_polite_        │
                    │    reminder             │──── HITL interrupt
                    │  - escalate_dispute     │
                    │  - update_invoice_      │
                    │    details              │
                    └───────────┬─────────────┘
                                │
                    escalate_dispute()
                    Command(update={
                      escalation_level: 2
                    })
                                │
                    ┌───────────▼─────────────┐
                    │      Level 2            │
                    │      (Formal)           │
                    │                         │
                    │  Tone: Firm, direct     │
                    │                         │
                    │  Tools (all L1 plus):   │
                    │  - draft_formal_demand_ │
                    │    letter               │──── HITL interrupt
                    │  - calculate_late_fees  │
                    └───────────┬─────────────┘
                                │
                    escalate_dispute()
                    Command(update={
                      escalation_level: 3
                    })
                                │
                    ┌───────────▼─────────────┐
                    │      Level 3            │
                    │      (Legal)            │
                    │                         │
                    │  Tone: Legal language   │
                    │                         │
                    │  Tools (all L2 plus):   │
                    │  - draft_final_notice   │──── HITL interrupt
                    │  - lookup_small_claims_ │
                    │    procedures           │──── Tavily web search
                    │  - generate_court_      │
                    │    filing_guide         │──── Tavily web search
                    │                         │
                    │  [MAX LEVEL - cannot    │
                    │   escalate further]     │
                    └─────────────────────────┘
```

---

## GenAI Technologies & How They Help

This project is a showcase of **production-grade GenAI patterns** — not just "chat with an LLM" but a fully orchestrated agent system with state management, middleware pipelines, and human oversight.

### 1. LangChain Agent with Custom State (`create_agent` + `AgentState`)

```python
class InvoiceDisputeState(AgentState):
    client_name: str
    client_email: str
    invoice_amount: float
    invoice_id: str
    days_overdue: int
    escalation_level: int          # 1=friendly, 2=formal, 3=legal
    communication_history: list
    jurisdiction: str
```

**Why it matters for the customer:** The agent maintains full context across the entire dispute lifecycle. It remembers every detail — the client's name, how much they owe, what communications have been sent, and the current escalation level. The customer never has to repeat themselves.

**Technical detail:** The state is not just a chat history — it's a structured schema that middleware reads to make dynamic decisions. The `escalation_level` field is the key that unlocks the entire progressive escalation system.

### 2. Dynamic Tool Gating (`@wrap_model_call` Middleware)

```python
@wrap_model_call
def dynamic_tool_middleware(request: ModelRequest, handler) -> ModelResponse:
    level = request.state.get("escalation_level", 0)

    if level <= 0:   tools = [update_invoice_details]
    elif level == 1: tools = LEVEL_1_TOOLS  # friendly tools only
    elif level == 2: tools = LEVEL_2_TOOLS  # + formal demand, late fees
    else:            tools = LEVEL_3_TOOLS  # + legal research, court filing

    return handler(request.override(tools=tools))
```

**Why it matters for the customer:** The AI literally *cannot* jump to legal threats on Day 1. Tools are physically gated — at Level 1, the model doesn't even know `draft_final_notice` exists. This prevents premature escalation that could damage client relationships, and ensures a structured, professional approach to payment recovery.

**Technical detail:** This uses LangChain's `@wrap_model_call` middleware to intercept the model request and replace the available tools based on the current state. The model's tool schema is rewritten on every call.

### 3. Dynamic Prompt Engineering (`@dynamic_prompt` Middleware)

```python
@dynamic_prompt
def escalation_prompt(request: ModelRequest) -> str:
    level = request.state.get("escalation_level", 0)
    ctx = request.runtime.context  # FreelancerContext dataclass

    if level == 1:
        return f"Tone: Warm, empathetic. Assume best intentions..."
    elif level == 2:
        return f"Tone: Professional, firm. Reference contract terms..."
    elif level == 3:
        return f"Tone: Formal legal language. Reference statutes..."
```

**Why it matters for the customer:** The AI's personality shifts with the situation. At Level 1, it's understanding and gentle ("I'm sure this was an oversight"). At Level 3, it's using legal language ("Pursuant to the terms of agreement..."). The customer doesn't need to coach the AI on tone — it adapts automatically.

**Technical detail:** The `@dynamic_prompt` middleware replaces the system prompt dynamically based on state. It also injects the freelancer's business context (name, payment terms, late fee rate) from the runtime context dataclass.

### 4. Human-in-the-Loop (`HumanInTheLoopMiddleware`)

```python
HumanInTheLoopMiddleware(
    interrupt_on={
        "draft_polite_reminder": True,      # HITL required
        "draft_formal_demand_letter": True,  # HITL required
        "draft_final_notice": True,          # HITL required
        "calculate_late_fees": False,        # Auto-execute
        "escalate_dispute": False,           # Auto-execute
    },
    description_prefix="APPROVAL REQUIRED: Review this draft before sending",
)
```

**Why it matters for the customer:** No email or letter is ever sent without explicit human approval. The customer can:
- **Approve** — send as-is
- **Edit** — modify the draft and send
- **Reject** — tell the agent to revise with specific feedback

This is crucial for legal communications where a wrong word could have consequences. The customer stays in full control while the AI does the heavy lifting of drafting.

**Technical detail:** When the agent calls a draft tool, the HITL middleware interrupts execution, serializes the pending tool call, and returns it to the frontend. The frontend displays an approval card. When the user decides, the backend resumes with `Command(resume={"decisions": [...]})`.

### 5. Command Pattern for State Updates

```python
@tool
def escalate_dispute(runtime: ToolRuntime) -> Command:
    current = runtime.state.get("escalation_level", 1)
    return Command(update={
        "escalation_level": current + 1,
        "messages": [ToolMessage(
            f"Escalated to level {current + 1}. New tools available.",
            tool_call_id=runtime.tool_call_id
        )]
    })
```

**Why it matters for the customer:** State changes (escalation, invoice details) are atomic and auditable. When you escalate, the new level takes effect immediately — the next model call sees the updated state, gets new tools, and adopts a new tone.

**Technical detail:** Tools return `Command(update={...})` from `langgraph.types` to modify the agent's state. This is one of the few places LangGraph is directly used — `Command` is LangGraph's declarative state mutation primitive, imported here into an otherwise LangChain-driven agent.

### 6. Runtime Context Injection (`@dataclass` + `context_schema`)

```python
@dataclass
class FreelancerContext:
    freelancer_name: str = "Alex Rivera"
    freelancer_email: str = "alex@riveraconsulting.com"
    business_name: str = "Rivera Consulting"
    default_payment_terms: str = "Net 30"
    default_late_fee_percent: float = 1.5  # monthly
```

**Why it matters for the customer:** Every draft is automatically personalized — your business name in the header, your payment terms referenced, your late fee rate applied. You configure once, and every communication is branded and accurate.

**Technical detail:** The context dataclass is injected at runtime via `context_schema` on `create_agent`. Every tool and middleware can access it via `runtime.context` — it's read-only and never stored in the conversation state.

### 7. Web Search Integration (Tavily)

```python
@tool
def lookup_small_claims_procedures(jurisdiction: str, runtime: ToolRuntime) -> str:
    """Search for small claims court procedures for the given jurisdiction."""
    client = TavilyClient()
    results = client.search(
        query=f"small claims court filing procedure {jurisdiction} 2024",
        max_results=3
    )
    return "\n\n".join([r["content"] for r in results["results"]])
```

**Why it matters for the customer:** At Level 3, the AI researches actual court procedures for the client's specific jurisdiction. Instead of generic legal advice, you get: "In California, small claims court limit is $12,500. File at the courthouse in the county where the defendant resides..." Real, actionable information.

**Technical detail:** Tavily is used instead of a generic web search because it returns clean, structured content optimized for LLM consumption. The search is gated behind Level 3 — it only runs when the dispute has genuinely reached the legal stage.

### 8. MCP Server (Model Context Protocol)

```python
mcp = FastMCP("invoice_server")

@mcp.tool()
def get_invoice(invoice_id: str) -> dict:
    """Retrieve invoice details from the database."""
    ...

@mcp.tool()
def log_communication(invoice_id: str, comm_type: str, content: str) -> str:
    """Log a communication sent for an invoice."""
    ...
```

**Why it matters for the customer:** The MCP server acts as a standardized bridge to your invoice system. In production, this would connect to QuickBooks, FreshBooks, or Xero. The agent can read invoice data and log every communication automatically.

**Technical detail:** Uses Anthropic's Model Context Protocol with `FastMCP` for tool definition. The server runs as a subprocess with stdio transport, making it easily swappable with any invoice management system that implements the same tool interface.

### 9. Conversation Memory (`InMemorySaver`)

**Why it matters for the customer:** Every conversation is preserved per client thread. You can pick up a dispute weeks later and the agent remembers everything — what was sent, what level you're at, what the client responded.

**Technical detail:** This is where LangGraph contributes directly — `SqliteSaver` and `PostgresSaver` are LangGraph's checkpointing backends. Each thread has a unique ID (`invoice-{invoice_id}`), and every state mutation is persisted. The code tries `PostgresSaver` first (via `DATABASE_URL`), falling back to `SqliteSaver` locally.

---

## Escalation Levels — Detailed Breakdown

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   LEVEL 1: FRIENDLY                                                        │
│   ══════════════════                                                        │
│                                                                             │
│   Tone:   "Hi [Client], just a gentle reminder about invoice #[ID]..."     │
│   Tools:  check_invoice_status, draft_polite_reminder, escalate_dispute    │
│   Badge:  🟢 Green                                                          │
│   Goal:   Resolve with goodwill — assume oversight, not malice             │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   LEVEL 2: FORMAL                                                          │
│   ════════════════                                                          │
│                                                                             │
│   Tone:   "Per our agreement dated [date], payment of $[amount]            │
│            was due [X] days ago. A late fee of $[fee] has accrued..."       │
│   Tools:  + draft_formal_demand_letter, calculate_late_fees                │
│   Badge:  🟡 Amber                                                          │
│   Goal:   Create urgency — reference contract, apply financial pressure    │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   LEVEL 3: LEGAL                                                           │
│   ═══════════════                                                           │
│                                                                             │
│   Tone:   "This constitutes formal notice pursuant to [statute].           │
│            Failure to remit payment within 10 business days will            │
│            result in filing in [jurisdiction] Small Claims Court..."        │
│   Tools:  + draft_final_notice, lookup_small_claims, court_filing_guide    │
│   Badge:  🔴 Red                                                            │
│   Goal:   Final warning before court — legally sound, evidentially useful  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **LLM** | Groq (LLaMA 3.3 70B) | Free tier, fast inference, strong reasoning |
| **Agent Framework** | LangChain (primary) | Agent runtime, middleware pipeline (`@wrap_model_call`, `@dynamic_prompt`, HITL), tool orchestration |
| **Checkpointing / State** | LangGraph (secondary) | `SqliteSaver`/`PostgresSaver` for thread memory; `Command` type for tool state mutations |
| **Web Search** | Tavily | Clean content optimized for LLM consumption |
| **Backend** | FastAPI (Python) | Async, Pydantic validation, Vercel serverless compatible |
| **Frontend** | React 19 + Vite + Tailwind v4 | Fast builds, modern CSS, type-safe |
| **Hosting** | Vercel (free tier) | Zero-config deployment, serverless Python functions |
| **Icons** | Lucide React | Consistent, lightweight icon set |

---

## Project Structure

```
invoice-dispute-agent/
├── api/
│   └── index.py                    # FastAPI routes (Vercel serverless)
├── src/
│   ├── agent.py                    # Agent assembly with all middleware
│   ├── state.py                    # InvoiceDisputeState + FreelancerContext
│   ├── tools/
│   │   ├── drafting.py             # draft_polite_reminder, draft_formal_demand, draft_final_notice
│   │   ├── invoice.py              # check_invoice_status, calculate_late_fees
│   │   ├── legal.py                # lookup_small_claims, court_filing_guide (Tavily)
│   │   └── escalation.py           # escalate_dispute, update_invoice_details (Command pattern)
│   ├── middleware/
│   │   ├── dynamic_tools.py        # @wrap_model_call — level-based tool gating
│   │   └── dynamic_prompts.py      # @dynamic_prompt — tone shifting per level
│   └── mcp_server/
│       └── invoice_server.py       # FastMCP mock invoice API
├── frontend/
│   ├── src/
│   │   ├── App.tsx                 # React Router (Dashboard + Chat)
│   │   ├── components/
│   │   │   ├── Dashboard.tsx       # Stats + invoice table + create form
│   │   │   ├── ChatPanel.tsx       # Chat + HITL + sidebar + escalation control
│   │   │   ├── MessageBubble.tsx   # Agent/user/tool message rendering
│   │   │   ├── DraftApproval.tsx   # HITL approve/edit/reject card
│   │   │   ├── EscalationBadge.tsx # Color-coded level indicator
│   │   │   ├── StatsCards.tsx      # Dashboard summary cards
│   │   │   ├── InvoiceTable.tsx    # Clickable invoice table
│   │   │   ├── InvoiceForm.tsx     # New invoice modal form
│   │   │   └── Layout.tsx          # App shell with nav
│   │   ├── hooks/
│   │   │   ├── useChat.ts          # Chat state + API calls + HITL handling
│   │   │   └── useInvoices.ts      # Invoice CRUD + polling
│   │   ├── api.ts                  # Fetch wrapper
│   │   └── types.ts                # TypeScript interfaces
│   └── index.html
├── main.py                         # CLI entry point (no frontend needed)
├── requirements.txt
├── vercel.json                     # Vercel deployment config
└── .env.example
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Free API keys:
  - [Groq](https://console.groq.com) — LLM inference (free tier: 30 req/min)
  - [Tavily](https://app.tavily.com) — Web search (free tier: 1000 searches/month)

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/invoice-dispute-agent.git
cd invoice-dispute-agent

# Set up Python virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend && npm install && cd ..

# Configure environment variables
cp .env.example .env
```

Edit `.env` with your API keys:

```env
GROQ_API_KEY=gsk_your_key_here
TAVILY_API_KEY=tvly-your_key_here
```

### Run Locally

```bash
# Terminal 1: Start the backend
uvicorn api.index:app --reload --port 8000

# Terminal 2: Start the frontend
cd frontend && npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

### CLI Mode (No Frontend)

```bash
python main.py
```

Interactive terminal mode — type messages, handle HITL with `approve`/`reject`/`edit:...` commands.

---

## Deploy to Vercel (Free)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel --prod
```

Set environment variables in the Vercel dashboard:
- `GROQ_API_KEY`
- `TAVILY_API_KEY`

The `vercel.json` handles everything:
- Frontend builds from `frontend/dist`
- API routes served by `api/index.py` as a Python serverless function
- All other routes serve the React SPA

---

## Demo Flow

1. **Create Invoice** — Click "+ New Invoice", enter client details (name, email, amount, days overdue, jurisdiction)
2. **Level 1** — The agent starts at Friendly. Ask it to "draft a reminder email"
3. **HITL Review** — A styled approval card appears with the draft. Approve, edit, or reject
4. **Escalate** — Click "Escalate to Level 2" in the sidebar. The badge turns amber, new tools unlock
5. **Level 2** — Request a "formal demand letter with late fees". The AI calculates fees and drafts a firm letter
6. **Escalate Again** — Move to Level 3. The badge turns red
7. **Legal Research** — Ask "What are the small claims court procedures in California?" — the agent uses Tavily to research real legal procedures
8. **Final Notice** — Request a final notice. The AI drafts a legally-structured document referencing jurisdiction-specific statutes

---

## LangChain Concepts Demonstrated

| Concept | Module | Implementation |
|---------|--------|---------------|
| Custom State (`AgentState` subclass) | `src/state.py` | `InvoiceDisputeState` with 8 typed fields |
| Runtime Context (`@dataclass`) | `src/state.py` | `FreelancerContext` injected per request |
| Tools (`@tool` + `ToolRuntime`) | `src/tools/` | 9 specialized tools across 4 modules |
| Dynamic Tools (`@wrap_model_call`) | `src/middleware/dynamic_tools.py` | Level-based progressive tool unlocking |
| Dynamic Prompts (`@dynamic_prompt`) | `src/middleware/dynamic_prompts.py` | Tone shifting across 4 escalation levels |
| Human-in-the-Loop (`HumanInTheLoopMiddleware`) | `src/agent.py` | Interrupt on all 3 draft tools |
| Command Pattern (`Command(update={...})`) | `src/tools/escalation.py` | Atomic state updates from tools |
| Web Search (Tavily) | `src/tools/legal.py` | Small claims + court filing research |
| MCP Server (`FastMCP`) | `src/mcp_server/` | Mock invoice API with 5 tools |
| Memory (`InMemorySaver`) | `src/agent.py` | Thread-based conversation persistence |

---

## Contributing

Contributions are welcome! Here's how to get started:

1. **Fork** the repository
2. **Create a branch**: `git checkout -b feature/your-feature`
3. **Make your changes** and test locally (both backend and frontend)
4. **Commit**: `git commit -m "Add your feature"`
5. **Push**: `git push origin feature/your-feature`
6. **Open a Pull Request**

### Areas for Contribution

- **Real invoice integrations** — Connect to QuickBooks, FreshBooks, or Xero via MCP
- **Email sending** — Integrate SendGrid/Resend to actually deliver drafted communications
- **Persistent storage** — Replace `InMemorySaver` with PostgreSQL for production
- **Multi-language** — Generate drafts in the client's preferred language
- **PDF generation** — Export formal demand letters and final notices as styled PDFs
- **Analytics** — Track recovery rates, average time to payment, escalation patterns

---

## License

MIT

---

<div align="center">

**Built as a portfolio project demonstrating production-grade GenAI agent development.**

*Every LangChain concept — state management, middleware pipelines, tool orchestration, human oversight — working together in a system that solves a real $825B problem.*

</div>
