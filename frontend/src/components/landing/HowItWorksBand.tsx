


// ─── How it works (dark band) ────────────────────────────────────────────────

const BAND_STEPS = [
  { you: true, title: 'You add the invoice', text: 'Drop in the PDF, or create one here.' },
  { you: false, title: 'The agent chases', text: 'Reminders, replies and escalation advice.' },
  { you: true, title: 'You approve each email', text: 'Nothing sends from your Gmail without your click.' },
]


export function HowItWorksBand() {
  return (
    <section aria-labelledby="how-title" className="bg-ink text-white">
      <div className="max-w-[1180px] mx-auto px-4 sm:px-8 py-12 sm:py-14">
        <h2 id="how-title" className="sr-only">How it works</h2>
        <ol className="grid md:grid-cols-3 gap-8 md:gap-10">
          {BAND_STEPS.map((step, i) => (
            <li key={step.title} className="flex gap-4">
              <span
                className={`w-10 h-10 shrink-0 rounded-lg flex items-center justify-center text-[17px] font-bold ${
                  step.you ? 'bg-coral text-ink' : 'bg-white text-ink'
                }`}
              >
                {i + 1}
              </span>
              <div>
                <h3 className="text-[20px] font-semibold">{step.title}</h3>
                <p className="mt-1 text-[16px] leading-[1.5] text-[#D1D5DB]">{step.text}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}
