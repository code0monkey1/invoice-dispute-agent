// The hero's product glance, from the "Page sample" in the Paper design
// system: an overdue invoice, an automatic step, and the one step that needs
// the user (approving the email). Illustration only, so it is hidden from
// assistive tech; the animated run below is the interactive demo.
export function HeroCards() {
  return (
    <div aria-hidden="true" className="flex flex-col gap-4">
      <div className="flex items-center gap-4 rounded-xl bg-card border border-line px-5 py-4">
        <img
          src="/presenter/woman-happy.jpg"
          alt=""
          width={64}
          height={64}
          className="w-16 h-16 shrink-0 rounded-full object-cover"
        />
        <div className="grow min-w-0">
          <p className="text-[16px] font-semibold leading-5">Northwind Studio · $2,400.00</p>
          <p className="text-[14px] leading-[18px] text-muted">Invoice #1042 · due 3 Nov</p>
        </div>
        <span className="rounded-full bg-red-bg px-3 py-1 text-[14px] font-semibold text-red">Overdue</span>
      </div>

      <div className="flex items-center gap-4 rounded-xl bg-card border border-line px-5 py-4">
        <span className="w-8 h-8 shrink-0 rounded-full bg-line flex items-center justify-center text-[14px] font-bold text-muted">1</span>
        <div className="grow min-w-0">
          <p className="text-[16px] font-medium leading-5 text-muted">Checked the invoice and found no payment</p>
          <p className="text-[14px] leading-[18px] text-muted">Automatic</p>
        </div>
        <span className="text-[14px] font-medium text-muted">Done</span>
      </div>

      <div className="flex items-center gap-4 rounded-xl bg-tint border-2 border-coral px-5 py-4">
        <span className="w-8 h-8 shrink-0 rounded-full bg-coral flex items-center justify-center text-[14px] font-bold text-ink">2</span>
        <div className="grow min-w-0">
          <p className="text-[16px] font-bold leading-5">Friendly reminder drafted</p>
          <p className="text-[14px] font-semibold leading-[18px] text-coral-text">Needs your approval</p>
        </div>
        <span className="btn-coral shrink-0 rounded-lg px-4 py-2 text-[14px] font-semibold">Approve and send</span>
      </div>
    </div>
  )
}
