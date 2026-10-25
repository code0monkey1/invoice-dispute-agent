export function formatMoney(amount: number): string {
  return amount.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
}

export function formatOverdue(days: number): string {
  if (days <= 0) return 'Not overdue'
  return days === 1 ? '1 day' : `${days} days`
}
