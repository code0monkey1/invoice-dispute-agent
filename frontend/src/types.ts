export interface Invoice {
  communication_count?: number;
  outbound_count?: number;
  last_communication_direction?: string | null;
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
  /** YYYY-MM-DD the client promised to pay by; set while status is "pending". */
  follow_up_date?: string | null;
  invoice_file_path?: string | null;
  invoice_file_name?: string | null;
  invoice_file_mime?: string | null;
  invoice_file_size?: number | null;
  /** Set by GET /api/invoices: a draft or action is waiting for the user's approval. */
  awaiting_approval?: boolean;
  pending_action?: string | null;
}

export interface CommunicationEntry {
  type: string;
  content: string;
  timestamp: string;
  direction?: 'inbound' | 'outbound' | string;
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
  content: unknown;
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
  follow_up_date?: string | null;
  communication_history: CommunicationEntry[];
}

export interface SummaryMetadata {
  source_version: string | null;
  generated_at: string | null;
  status: 'empty' | 'pending' | 'refreshing' | 'current' | 'failed' | 'unavailable';
  is_stale: boolean;
}

export interface ConversationSummary extends SummaryMetadata {
  state: AgentState;
  interrupt: Interrupt | null;
  has_history: boolean;
  has_outbound: boolean;
  invoice_id: string;
  summary: string | null;
}

export interface ChatResponse {
  has_history?: boolean;
  has_outbound?: boolean;
  summary?: string | null;
  summary_metadata?: SummaryMetadata;
  messages: Message[];
  interrupt: Interrupt | null;
  state: AgentState;
  email_sent?: boolean;
  email_id?: string;
  /** Why an approved email was or wasn't sent: sent, demo, gmail_not_connected or failed. */
  email_status?: 'sent' | 'demo' | 'gmail_not_connected' | 'failed';
  email_note?: string;
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
  /** True once the user has granted send-only Gmail access. */
  gmail_connected?: boolean;
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

// Agent traces (GET /api/invoices/{id}/traces). Text in payloads is redacted server-side.
export type TraceStepType =
  | 'model_call' | 'tool_call' | 'gate_blocked' | 'interrupt' | 'human_decision' | 'email_send'

export interface TraceStep {
  seq: number
  type: TraceStepType | string
  name: string | null
  payload: Record<string, unknown>
  latency_ms: number | null
  input_tokens?: number | null
  output_tokens?: number | null
}

export interface TraceRun {
  id: string
  kind: 'chat' | 'escalate' | 'resume' | 'inbound_reply' | 'cli' | string
  status: 'ok' | 'interrupted' | 'error' | string
  model: string | null
  prompt_version: string | null
  level_start: number | null
  level_end: number | null
  started_at: string
  latency_ms: number | null
  input_tokens: number | null
  output_tokens: number | null
  cost_usd: number | null
  error: string | null
  steps: TraceStep[]
}

export interface TracesResponse {
  runs: TraceRun[]
  next_before: string | null
}
