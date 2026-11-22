import { X } from 'lucide-react'
import { GoogleIcon } from './GoogleIcon'


// ─── Guest modal ─────────────────────────────────────────────────────────────

interface GuestModalProps {
  name: string
  onNameChange: (name: string) => void
  onEnter: () => void
  onGoogle: () => void
  onClose: () => void
}


export function GuestModal({ name, onNameChange, onEnter, onGoogle, onClose }: GuestModalProps) {
  return (
    <div className="fixed inset-0 bg-ink/50 z-[100] flex items-center justify-center p-4" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="guest-title"
        className="bg-white rounded-xl w-full max-w-sm border border-line shadow-pop p-6 sm:p-7"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 id="guest-title" className="text-[22px] font-bold">Try the demo</h2>
            <p className="text-[15px] text-muted mt-1">No sign-up. Guest sessions are temporary.</p>
          </div>
          <button onClick={onClose} aria-label="Close" className="p-1 -m-1 text-muted hover:text-ink">
            <X className="w-5 h-5" />
          </button>
        </div>

        <label className="block mt-6">
          <span className="block text-[15px] font-semibold mb-1.5">Your name</span>
          <input
            type="text"
            value={name}
            onChange={(e) => onNameChange(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && onEnter()}
            placeholder="e.g. Sam"
            autoFocus
            className="w-full rounded-lg border border-line bg-card px-3.5 py-2.5 text-[16px] focus:outline-2 focus:outline-ink"
          />
        </label>

        <button
          onClick={onEnter}
          disabled={!name.trim()}
          className="mt-4 w-full rounded-lg bg-ink text-white font-semibold text-[16px] py-3 hover:bg-black disabled:opacity-40"
        >
          Start the demo
        </button>

        <div className="flex items-center gap-3 my-4 text-[14px] text-muted">
          <span className="h-px flex-1 bg-line" />or<span className="h-px flex-1 bg-line" />
        </div>

        <button
          onClick={onGoogle}
          className="w-full inline-flex items-center justify-center gap-2.5 rounded-lg border border-line font-semibold text-[16px] py-3 hover:border-ink"
        >
          <GoogleIcon />
          Sign in with Google to save your data
        </button>
      </div>
    </div>
  )
}
