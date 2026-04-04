const LEVELS: Record<number, { label: string; color: string; bg: string; dot: string; border: string }> = {
  1: {
    label: 'Friendly',
    color: 'text-emerald-700',
    bg: 'bg-gradient-to-r from-emerald-50 to-green-50',
    dot: 'bg-emerald-500',
    border: 'border-emerald-200',
  },
  2: {
    label: 'Formal',
    color: 'text-amber-700',
    bg: 'bg-gradient-to-r from-amber-50 to-yellow-50',
    dot: 'bg-amber-500',
    border: 'border-amber-200',
  },
  3: {
    label: 'Legal',
    color: 'text-rose-700',
    bg: 'bg-gradient-to-r from-rose-50 to-red-50',
    dot: 'bg-rose-500',
    border: 'border-rose-200',
  },
}

export default function EscalationBadge({ level, size = 'sm' }: { level: number; size?: 'sm' | 'md' }) {
  const config = LEVELS[level] || LEVELS[1]
  const isMd = size === 'md'
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full font-semibold border font-[family-name:var(--font-heading)] ${config.bg} ${config.color} ${config.border} ${isMd ? 'px-3.5 py-1.5 text-sm' : 'px-2.5 py-1 text-xs'}`}>
      <span className={`rounded-full animate-pulse-dot ${config.dot} ${isMd ? 'w-2 h-2' : 'w-1.5 h-1.5'}`} />
      Level {level} — {config.label}
    </span>
  )
}
