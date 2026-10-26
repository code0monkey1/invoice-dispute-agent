export function formatMoney(amount: number): string {
  return amount.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
}

export function formatOverdue(days: number): string {
  if (days <= 0) return 'Not overdue'
  return days === 1 ? '1 day' : `${days} days`
}

/** "2026-11-15" → "Nov 15, 2026". Parsed as a local date so it never shifts a day. */
export function formatPromiseDate(isoDate: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(isoDate)
  if (!match) return isoDate
  const date = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]))
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

/** True when the promised YYYY-MM-DD date is before *today* (the due day itself still counts). */
export function isPromiseMissed(isoDate: string, today: Date): boolean {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(isoDate)
  if (!match) return false
  const promised = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]))
  const startOfToday = new Date(today.getFullYear(), today.getMonth(), today.getDate())
  return promised < startOfToday
}
