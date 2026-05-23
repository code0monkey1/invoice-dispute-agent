export interface Invoice {
  id: string;
  invoice_id: string;
  client_name: string;
  client_email: string;
  invoice_amount: number;
  amount_paid: number;
  balance_due: number;
  days_overdue: number;
  jurisdiction: string;
  escalation_level: number;
  communication_history: CommunicationEntry[];
  status: string;
  invoice_file_path?: string | null;
  invoice_file_name?: string | null;
  invoice_file_mime?: string | null;
  invoice_file_size?: number | null;
}

export interface CommunicationEntry {
  type: string;
  content: string;
  timestamp: string;
}

export interface SupabaseCommEntry {
  id: number;
  invoice_id: string;
  type: string;
  subject: string | null;
  content: string | null;
  direction: string;
  timestamp: string;
}

export interface Message {
  type: string;
  content: string;
  name?: string;
  tool_calls?: { name: string; args: Record<string, unknown> }[];
}

export interface Interrupt {
  tool: string;
  args: Record<string, unknown>;
  description: string;
}

export interface AgentState {
  escalation_level: number;
  client_name: string;
  client_email: string;
  invoice_amount: number;
  amount_paid: number;
  balance_due: number;
  invoice_id: string;
  days_overdue: number;
  jurisdiction: string;
  status: string;
  communication_history: CommunicationEntry[];
}

export interface ChatResponse {
  messages: Message[];
  interrupt: Interrupt | null;
  state: AgentState;
  email_sent?: boolean;
  email_id?: string;
  communications?: SupabaseCommEntry[];
}

export interface InvoiceCreateResponse {
  invoice: Invoice;
  messages: Message[];
  interrupt: Interrupt | null;
  state: AgentState;
  initialization_error?: string;
}

export interface ParsedInvoiceResponse {
  extracted: {
    invoice_id?: string | null;
    client_name?: string | null;
    client_email?: string | null;
    invoice_amount?: number | null;
    due_date?: string | null;
    days_overdue?: number | null;
    jurisdiction?: string | null;
    confidence?: number;
    warnings?: string[];
  };
  missing_fields: string[];
  warnings: string[];
  text_length: number;
  file: {
    name: string;
    mime: string;
    size: number;
  };
}

export interface User {
  id: string;
  email: string;
  name: string;
  picture: string;
}

// ─── Invoice Generator ───────────────────────────────────────────

export type TemplateId = 'modern' | 'classic' | 'minimal';

export type Currency = 'USD' | 'EUR' | 'GBP' | 'INR' | 'CAD' | 'AUD';

export interface SenderProfile {
  business_name?: string;
  your_name?: string;
  your_email?: string;
  address?: string;
  logo_url?: string;
  tax_id?: string;
}

export interface LineItem {
  description: string;
  quantity: number;
  unit_price_cents: number;
}

export interface InvoiceData {
  sender: SenderProfile;
  client: { name: string; email: string; address?: string };
  meta: {
    invoice_number: string;
    issue_date: string;  // yyyy-mm-dd
    due_date: string;    // yyyy-mm-dd
    currency: Currency;
  };
  line_items: LineItem[];
  tax_rate_pct?: number;
  discount?: { kind: 'flat' | 'pct'; value: number };
  payment?: { url: string; label?: string };
  payment_instructions?: string;
  notes?: string;
  template: TemplateId;
  accent_color?: string;  // honored by Modern only
}

export interface GenerateInvoiceRequest {
  invoice_id: string;
  client_name: string;
  client_email: string;
  invoice_amount_cents: number;
  due_date: string;
  jurisdiction?: string;
  storage_path: string;  // path within invoice-files bucket
  file_name: string;
  file_size: number;
}
