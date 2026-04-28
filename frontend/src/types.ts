export interface Invoice {
  id: string;
  invoice_id: string;
  client_name: string;
  client_email: string;
  invoice_amount: number;
  days_overdue: number;
  jurisdiction: string;
  escalation_level: number;
  communication_history: CommunicationEntry[];
  status: string;
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
  invoice_id: string;
  days_overdue: number;
  jurisdiction: string;
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

export interface User {
  id: string;
  email: string;
  name: string;
  picture: string;
}
