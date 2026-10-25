// Same level colours as the landing page: green, amber, red.
const LEVELS: Record<number, { label: string; text: string; bg: string; dot: string }> = {
  0: { label: 'Setting up', text: 'text-[#6B7280]', bg: 'bg-[#F6EDE3]', dot: 'bg-[#C9B8A6]' },
  1: { label: 'Friendly', text: 'text-[#1F7A55]', bg: 'bg-[#E7F4EC]', dot: 'bg-[#1F7A55]' },
  2: { label: 'Formal', text: 'text-[#8A4F00]', bg: 'bg-[#FDF1DE]', dot: 'bg-[#A35E00]' },
  3: { label: 'Legal', text: 'text-[#B3261E]', bg: 'bg-[#FBE8E6]', dot: 'bg-[#B3261E]' },
}

export default function EscalationBadge({ level, size = 'sm' }: { level: number; size?: 'sm' | 'md' }) {
  const config = LEVELS[level] ?? LEVELS[1]
  const isMd = size === 'md'
  return (
    <span
      title={level > 0 ? `Level ${level} of 3` : undefined}
      className={`inline-flex items-center gap-1.5 rounded-full font-semibold whitespace-nowrap ${config.bg} ${config.text} ${isMd ? 'px-3.5 py-1.5 text-[15px]' : 'px-2.5 py-1 text-[13px]'}`}
    >
      <span className={`rounded-full ${config.dot} ${isMd ? 'w-2 h-2' : 'w-1.5 h-1.5'}`} />
      {config.label}
    </span>
  )
}
