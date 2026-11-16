import { FileText, PenLine, Send, Inbox, Scale, ListChecks, Clock, FileDown } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'


// ─── Who does what ───────────────────────────────────────────────────────────

const AGENT_JOBS: [LucideIcon, string][] = [
  [FileText, 'Reads your PDF or DOCX invoice'],
  [Clock, 'Works out how overdue it is'],
  [PenLine, 'Drafts each follow-up in the right tone'],
  [Inbox, 'Reads replies and flags disputes'],
  [FileDown, 'Creates invoice PDFs from three templates'],
  [Scale, 'Suggests when to get firmer'],
  [ListChecks, "Finds small-claims rules for your client's location"],
  [Send, 'Sends from your Gmail, not a no-reply bot'],
]


export function WhoDoesWhat() {
  return (
    <section className="max-w-[1180px] mx-auto px-4 sm:px-8 pt-20 sm:pt-28 pb-20 sm:pb-28">
      <h2 className="text-[34px] sm:text-[44px] font-bold leading-[1.08] tracking-[-0.02em] max-w-[16ch]">
        The agent does the chasing. You keep the final say.
      </h2>
      <div className="mt-10 grid lg:grid-cols-[1.6fr_1fr] gap-4 items-start">
        <div className="rounded-[16px] bg-white border border-[#F1E4D8] p-6 sm:p-8">
          <h3 className="text-[20px] font-semibold flex items-center gap-2.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#111827]" />
            The agent
          </h3>
          <ul className="mt-5 grid sm:grid-cols-2 gap-x-8 gap-y-4 text-[16px] leading-[1.4]">
            {AGENT_JOBS.map(([Icon, text]) => (
              <li key={text} className="flex items-center gap-3">
                <span className="w-9 h-9 shrink-0 rounded-[10px] bg-[#111827] text-white flex items-center justify-center">
                  <Icon className="w-[18px] h-[18px]" />
                </span>
                {text}
              </li>
            ))}
          </ul>
        </div>
        <div className="rounded-[16px] bg-[#FF6B35] text-[#111827] p-6 sm:p-8">
          <h3 className="text-[20px] font-semibold flex items-center gap-2.5">
            <span className="w-2.5 h-2.5 rounded-[3px] bg-[#111827]" />
            You
          </h3>
          <p className="mt-5 text-[28px] sm:text-[32px] font-bold leading-[1.15] tracking-[-0.01em]">
            Add the invoice. Approve each email.
          </p>
          <p className="mt-3 text-[16px] leading-[1.5]">
            Edit or reject any draft. Nothing sends without your click.
          </p>
        </div>
      </div>
    </section>
  )
}
