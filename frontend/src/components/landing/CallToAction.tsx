import { useState, useEffect } from 'react'
import { Play } from 'lucide-react'
import { GoogleIcon } from './GoogleIcon'
import { demoButton, googleButton } from './styles'


export interface CtaProps {
  onGoogle: () => void
  onGuest: () => void
}


export function CtaButtons({ onGoogle, onGuest }: CtaProps) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-3">
      <button onClick={onGuest} className={`${demoButton} text-[16px] px-5 py-3.5`}>
        <Play className="w-4 h-4" fill="currentColor" />
        See a demo
      </button>
      <button onClick={onGoogle} className={`${googleButton} text-[16px] px-5 py-3.5`}>
        <GoogleIcon />
        Continue with Google
      </button>
    </div>
  )
}


export function StickyCta({ onGoogle, onGuest }: CtaProps) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    // Shown once the hero's buttons scroll away, hidden again when the closing
    // call to action (which has the same buttons) comes into view.
    const finalCta = document.getElementById('final-cta')
    const onScroll = () => {
      const finalInView = finalCta ? finalCta.getBoundingClientRect().top < window.innerHeight : false
      setVisible(window.scrollY > 560 && !finalInView)
    }
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
    }
  }, [])

  return (
    <div
      aria-hidden={!visible}
      className={`fixed bottom-4 inset-x-4 sm:inset-x-auto sm:left-1/2 sm:-translate-x-1/2 z-50 rounded-xl bg-white border border-line shadow-card p-2 sm:pl-5 flex items-center gap-3 sm:gap-6 transition-all duration-300 motion-reduce:transition-none ${
        visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4 pointer-events-none'
      }`}
    >
      <p className="hidden md:block text-[16px] font-semibold whitespace-nowrap">Have an overdue invoice?</p>
      <div className="flex flex-1 sm:flex-none gap-2">
        <button onClick={onGuest} tabIndex={visible ? 0 : -1} className={`${demoButton} flex-1 sm:flex-none text-[16px] px-4 py-2.5`}>
          Try the demo
        </button>
        <button onClick={onGoogle} tabIndex={visible ? 0 : -1} className={`${googleButton} flex-1 sm:flex-none text-[16px] px-4 py-2.5`}>
          <GoogleIcon />
          Sign in
        </button>
      </div>
    </div>
  )
}
