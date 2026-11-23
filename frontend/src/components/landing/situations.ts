import { FileText, Search, Mail, Scale, ListChecks } from 'lucide-react'

// The day ranges are guidance for the user, not thresholds in the agent:
// escalating is always the user's call.
export const SITUATIONS = [
  {
    label: 'Just overdue', pain: 'You want to stay friendly.',
    level: 1, name: 'Friendly', icon: Mail, solid: 'bg-green', tint: 'bg-green-bg', edge: 'border-l-green',
    when: 'Usually right for invoices 7–30 days late.',
    email: { subject: 'A quick reminder: invoice INV-042', body: ['Hi Sam,', 'Just checking in on invoice INV-042 for $5,000, due 2 April. When can I expect payment?', 'Thanks, Lena'] },
    does: [[Mail, 'Polite reminders'], [Search, 'Invoice status checks']],
  },
  {
    label: 'Being ignored', pain: 'You followed up. Silence.',
    level: 2, name: 'Formal', icon: FileText, solid: 'bg-amber', tint: 'bg-amber-bg', edge: 'border-l-amber',
    when: '30–60 days late, or when the client disputes it.',
    email: { subject: 'Invoice INV-042: payment overdue', body: ['Hello Sam,', 'Invoice INV-042 for $5,000 is now 45 days overdue, past our agreed terms.', 'Please pay the balance by 30 May.'] },
    does: [[FileText, 'A formal demand letter'], [Search, 'Invoice status checks']],
  },
  {
    label: 'Last chance', pain: 'Formal letters were ignored.',
    level: 3, name: 'Legal', icon: Scale, solid: 'bg-red', tint: 'bg-red-bg', edge: 'border-l-red',
    when: '60+ days late, after formal letters are ignored.',
    email: { subject: 'Final notice: invoice INV-042', body: ['Sam,', "This is formal notice. If payment of $5,000 isn't received within 10 days, I'll file a small-claims case."] },
    does: [[Mail, 'A final notice'], [Scale, "Small-claims rules for the client's location"], [ListChecks, 'A court filing guide']],
  },
] as const
