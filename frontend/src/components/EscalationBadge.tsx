// Level colours use the status pairs and rise in intensity: neutral, amber, red.
// Green is reserved for paid.
const LEVELS: Record<number, { label: string; text: string; bg: string; dot: string }> = {
  0: { label: 'Setting up', text: 'text-body', bg: 'bg-tint', dot: 'bg-line-2' },
  1: { label: 'Friendly', text: 'text-body', bg: 'bg-tint', dot: 'bg-muted' },
  2: { label: 'Formal', text: 'text-amber', bg: 'bg-amber-bg', dot: 'bg-amber' },
  3: { label: 'Legal', text: 'text-red', bg: 'bg-red-bg', dot: 'bg-red' },
}

export default function EscalationBadge({ level, size = 'sm' }: { level: number; size?: 'sm' | 'md' }) {
  const config = LEVELS[level] ?? LEVELS[1]
  const isMd = size === 'md'
  return (
    <span
      title={level > 0 ? `Level ${level} of 3` : undefined}
      className={`inline-flex items-center gap-1.5 rounded-full font-semibold whitespace-nowrap ${config.bg} ${config.text} ${isMd ? 'px-3.5 py-1.5 text-[16px]' : 'px-2.5 py-1 text-[14px]'}`}
    >
      <span className={`rounded-full ${config.dot} ${isMd ? 'w-2 h-2' : 'w-1.5 h-1.5'}`} />
      {config.label}
    </span>
  )
}
