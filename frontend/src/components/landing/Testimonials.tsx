


// ─── Testimonials ────────────────────────────────────────────────────────────
// Quotes from InvoiceChaser customers, carried over from the original landing
// page. The portraits are Unsplash stock headshots, not the customers.

interface Testimonial {
  name: string
  role: string
  location: string
  quote: string
  photo: string
}


const FEATURED_TESTIMONIAL: Testimonial = {
  name: 'Daniel Okafor',
  role: 'Co-founder, two-person studio',
  location: 'London, UK',
  quote: 'A client owed us £8,400 for 90 days. InvoiceChaser drafted a formal demand. They paid two days after the demand went out.',
  photo: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&h=200&fit=facearea&facepad=2&q=80&auto=format',
}


const TESTIMONIALS: Testimonial[] = [
  {
    name: 'Maya Chen',
    role: 'Brand designer, freelance',
    location: 'Portland, OR',
    quote: 'Now the agent writes [the reminder], I tweak a word or two, and hit approve. Three of my late clients paid within a week.',
    photo: 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=200&h=200&fit=facearea&facepad=2&q=80&auto=format',
  },
  {
    name: 'Priya Raman',
    role: 'Independent consultant',
    location: 'Singapore',
    quote: "Every reminder is from my own Gmail, in my own thread. I just don't have to be the one writing the awkward part anymore.",
    photo: 'https://images.unsplash.com/photo-1580489944761-15a19d654956?w=200&h=200&fit=facearea&facepad=2&q=80&auto=format',
  },
]


function Author({ t, size }: { t: Testimonial; size: 'lg' | 'sm' }) {
  return (
    <figcaption className="flex items-center gap-3">
      <img
        src={t.photo}
        alt=""
        loading="lazy"
        referrerPolicy="no-referrer"
        className={`${size === 'lg' ? 'w-14 h-14' : 'w-11 h-11'} rounded-full object-cover bg-[#FDEBDD]`}
      />
      <div className="min-w-0">
        <p className="text-[16px] font-semibold">{t.name}</p>
        <p className="text-[14px] text-[#6B7280]">{t.role}, {t.location}</p>
      </div>
    </figcaption>
  )
}


export function Testimonials() {
  return (
    <section className="max-w-[1180px] mx-auto px-4 sm:px-8 pb-20 sm:pb-28">
      <div className="max-w-[640px]">
        <h2 className="text-[34px] sm:text-[44px] font-bold leading-[1.08] tracking-[-0.02em]">
          Loved by people who hate chasing
        </h2>
        <p className="mt-4 text-[18px] leading-[1.6] text-[#6B7280]">
          Freelancers who stopped writing "just following up" emails.
        </p>
      </div>
      <div className="mt-12 grid lg:grid-cols-[1.25fr_1fr] gap-10 lg:gap-16">
        <figure className="border-l-4 border-[#FF6B35] pl-6 sm:pl-8 flex flex-col justify-between gap-8">
          <blockquote className="text-[24px] sm:text-[30px] font-semibold leading-[1.3] tracking-[-0.015em] max-w-[30ch]">
            “{FEATURED_TESTIMONIAL.quote}”
          </blockquote>
          <Author t={FEATURED_TESTIMONIAL} size="lg" />
        </figure>
        <div className="divide-y divide-[#E9D9C8]">
          {TESTIMONIALS.map((t) => (
            <figure key={t.name} className="py-7 first:pt-0 last:pb-0 flex flex-col gap-5">
              <blockquote className="text-[17px] leading-[1.55]">“{t.quote}”</blockquote>
              <Author t={t} size="sm" />
            </figure>
          ))}
        </div>
      </div>
    </section>
  )
}
