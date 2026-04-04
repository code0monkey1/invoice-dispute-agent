from mcp.server.fastmcp import FastMCP
from datetime import datetime

mcp = FastMCP("invoice_server")

# Mock database
INVOICES = {
    "INV-001": {
        "id": "INV-001",
        "client_name": "Acme Corp",
        "client_email": "billing@acme.com",
        "amount": 5000.00,
        "due_date": "2025-12-01",
        "status": "overdue",
        "days_overdue": 120,
        "jurisdiction": "California",
    },
    "INV-002": {
        "id": "INV-002",
        "client_name": "Beta LLC",
        "client_email": "accounts@beta.com",
        "amount": 2500.00,
        "due_date": "2026-02-15",
        "status": "overdue",
        "days_overdue": 45,
        "jurisdiction": "New York",
    },
    "INV-003": {
        "id": "INV-003",
        "client_name": "Gamma Industries",
        "client_email": "finance@gamma.io",
        "amount": 8750.00,
        "due_date": "2026-03-01",
        "status": "overdue",
        "days_overdue": 30,
        "jurisdiction": "Texas",
    },
}

COMMUNICATION_LOG = []


@mcp.tool()
def get_invoice(invoice_id: str) -> dict:
    """Get details for a specific invoice by its ID."""
    if invoice_id in INVOICES:
        return INVOICES[invoice_id]
    return {"error": f"Invoice {invoice_id} not found"}


@mcp.tool()
def list_overdue_invoices() -> list:
    """List all overdue invoices."""
    return [inv for inv in INVOICES.values() if inv["status"] == "overdue"]


@mcp.tool()
def mark_invoice_paid(invoice_id: str) -> str:
    """Mark an invoice as paid."""
    if invoice_id in INVOICES:
        INVOICES[invoice_id]["status"] = "paid"
        INVOICES[invoice_id]["days_overdue"] = 0
        return f"Invoice {invoice_id} marked as paid"
    return f"Invoice {invoice_id} not found"


@mcp.tool()
def log_communication(invoice_id: str, comm_type: str, content: str) -> str:
    """Log a communication sent for an invoice. comm_type: polite_reminder, formal_demand, final_notice."""
    entry = {
        "invoice_id": invoice_id,
        "type": comm_type,
        "content": content,
        "timestamp": datetime.now().isoformat(),
    }
    COMMUNICATION_LOG.append(entry)
    return f"Communication logged for invoice {invoice_id}"


@mcp.tool()
def get_communication_log(invoice_id: str) -> list:
    """Get all logged communications for a specific invoice."""
    return [c for c in COMMUNICATION_LOG if c["invoice_id"] == invoice_id]


if __name__ == "__main__":
    mcp.run(transport="stdio")
