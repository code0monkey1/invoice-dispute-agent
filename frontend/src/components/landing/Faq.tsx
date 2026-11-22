import { Plus } from 'lucide-react'


// ─── FAQ ─────────────────────────────────────────────────────────────────────

const FAQS = [
  {
    question: 'Will InvoiceChaser send emails without my approval?',
    answer: 'No. Every draft waits for you to approve, edit or reject it.',
  },
  {
    question: "Do clients know I'm using an AI tool?",
    answer: 'Emails come from your own Gmail, in the same thread. Clients see a normal email from you.',
  },
  {
    question: 'What if a client replies with a dispute?',
    answer: 'The agent summarizes their objection and suggests how to respond. Anything it drafts still needs your approval.',
  },
  {
    question: 'Is this a replacement for a lawyer?',
    answer: "No. It drafts emails and explains small-claims steps, but it isn't legal advice.",
  },
  {
    question: 'What do I need to get started?',
    answer: 'Your invoice as a PDF or DOCX, or type the details in. Sign in with Google, then connect Gmail to send. Or try the demo first.',
  },
  {
    question: 'Can InvoiceChaser read my inbox?',
    answer: 'No. It can only send the emails you approve. Replies reach your inbox as usual, and a copy lands on the invoice.',
  },
  {
    question: 'Which invoice files work?',
    answer: "PDF or DOCX up to 10 MB. Scans and photos aren't supported yet, so type those in.",
  },
]


// FAQ structured data comes from the same FAQS array, so it can't drift from the page.
const FAQ_JSON_LD = JSON.stringify({
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: FAQS.map(({ question, answer }) => ({
    '@type': 'Question',
    name: question,
    acceptedAnswer: { '@type': 'Answer', text: answer },
  })),
}).replace(/</g, '\\u003c')
 // static copy only; escaping keeps "</script>" impossible

export function Faq() {
  return (
    <section id="faq" className="max-w-[1180px] mx-auto px-4 sm:px-8 pb-20 sm:pb-28 grid lg:grid-cols-[1fr_1.6fr] gap-8 lg:gap-16 scroll-mt-4">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: FAQ_JSON_LD }} />
      <h2 className="text-[34px] sm:text-[44px] font-bold leading-[1.08] tracking-[-0.02em] max-w-[14ch]">
        Questions before you connect Gmail
      </h2>
      <div className="border-y border-line-2 divide-y divide-line-2">
        {FAQS.map(({ question, answer }) => (
          <details key={question} className="group">
            <summary className="flex items-center justify-between gap-4 py-5 cursor-pointer list-none [&::-webkit-details-marker]:hidden text-[17px] font-semibold">
              {question}
              <Plus className="w-5 h-5 shrink-0 text-muted transition-transform group-open:rotate-45 motion-reduce:transition-none" />
            </summary>
            <p className="pb-5 -mt-1 text-[16px] leading-[1.6] text-muted max-w-[62ch]">{answer}</p>
          </details>
        ))}
      </div>
    </section>
  )
}
