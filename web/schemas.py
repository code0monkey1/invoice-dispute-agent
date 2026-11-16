"""Request bodies the API accepts. Validation here is part of the API contract."""
from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    thread_id: str
    message: str


class InvoiceCreateRequest(BaseModel):
    # Trimmed, so "INV-1 " can't become a second invoice next to "INV-1".
    model_config = {"str_strip_whitespace": True}

    invoice_id: str = Field(min_length=1, max_length=300)
    client_name: str = Field(min_length=1, max_length=200)
    client_email: str = Field(min_length=1, max_length=254)
    invoice_amount: float = Field(gt=0, allow_inf_nan=False)
    days_overdue: int = Field(ge=0)
    jurisdiction: str
    amount_paid: float = Field(default=0, ge=0, allow_inf_nan=False)


class InvoiceUploadMetadata(InvoiceCreateRequest):
    pass


class ResumeRequest(BaseModel):
    decision: str  # "approve", "reject", "edit"
    message: Optional[str] = None
    edited_action: Optional[dict] = None


class UpdateDetailsRequest(BaseModel):
    client_name: Optional[str] = None
    client_email: Optional[str] = None


class UpdateSenderRequest(BaseModel):
    freelancer_name: Optional[str] = None
    freelancer_email: Optional[str] = None
    business_name: Optional[str] = None


class GoogleCallbackRequest(BaseModel):
    code: str


class SenderProfilePayload(BaseModel):
    """Pydantic schema for the per-user sender profile used by generated invoices."""
    model_config = {"extra": "forbid"}

    business_name: Optional[str] = None
    your_name: Optional[str] = None
    your_email: Optional[str] = None
    address: Optional[str] = None
    logo_url: Optional[str] = None
    tax_id: Optional[str] = None


class SummaryRefreshRequest(BaseModel):
    model_config = {"extra": "forbid"}


class GenerateInvoicePayload(BaseModel):
    """Schema for creating a generated invoice from an already-uploaded PDF."""
    model_config = {"extra": "forbid", "str_strip_whitespace": True}

    invoice_id: str = Field(min_length=1, max_length=300)
    client_name: str = Field(min_length=1, max_length=200)
    client_email: str = Field(min_length=1, max_length=254)
    invoice_amount_cents: int = Field(gt=0)
    due_date: str  # yyyy-mm-dd
    jurisdiction: Optional[str] = None
    storage_path: str
    file_name: str
    file_size: int
