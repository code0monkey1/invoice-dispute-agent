import { Check, X } from 'lucide-react'


// ─── With and without ────────────────────────────────────────────────────────

const COMPARISON: [string, string, string][] = [
  ['Writing the email', 'Start from a blank page, every time', 'A draft from your invoice, in the right tone'],
  ['Getting firmer', 'Decide alone how blunt to be', 'The agent suggests the level. You decide.'],
  ['Client replies', 'Search your inbox, update a spreadsheet', 'Saved on the invoice'],
  ['Small claims', 'Research the rules yourself', "Rules for your client's location, plus a filing guide"],
]


export function WithWithout() {
  return (
    <section className="max-w-[1180px] mx-auto px-4 sm:px-8 pb-20 sm:pb-28">
      <h2 className="text-[34px] sm:text-[44px] font-bold leading-[1.08] tracking-[-0.02em] max-w-[18ch]">
        Chasing an invoice, with and without InvoiceChaser
      </h2>
      <div className="mt-10 rounded-xl bg-white border border-line overflow-hidden">
        <table className="w-full text-left text-[16px]">
          <thead>
            <tr className="border-b border-line text-[15px]">
              <th scope="col" className="px-5 py-3.5 font-medium text-muted hidden md:table-cell w-[22%]">Task</th>
              <th scope="col" className="px-5 py-3.5 font-medium text-muted">On your own</th>
              <th scope="col" className="px-5 py-3.5 font-semibold bg-ink text-white">With InvoiceChaser</th>
            </tr>
          </thead>
          <tbody>
            {COMPARISON.map(([task, without, withIt]) => (
              <tr key={task} className="border-b last:border-b-0 border-[#F6EDE3] align-top">
                <th scope="row" className="px-5 py-4 font-semibold hidden md:table-cell">{task}</th>
                <td className="px-5 py-4 text-muted">
                  <span className="md:hidden block text-[14px] font-semibold text-ink mb-0.5">{task}</span>
                  <span className="flex gap-2"><X className="w-4 h-4 mt-1 shrink-0 text-red" />{without}</span>
                </td>
                <td className="px-5 py-4 bg-card">
                  <span className="md:hidden block text-[14px] mb-0.5">&nbsp;</span>
                  <span className="flex gap-2 font-medium"><Check className="w-4 h-4 mt-1 shrink-0 text-green" strokeWidth={2.5} />{withIt}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
