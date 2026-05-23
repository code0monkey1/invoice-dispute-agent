import { useCallback, useRef } from 'react';
import { TEMPLATES } from './pdf';
import type { TemplateId } from '../../types';

interface Props {
  value: TemplateId;
  onChange: (next: TemplateId) => void;
}

export function TemplatePicker({ value, onChange }: Props) {
  const refs = useRef<Record<TemplateId, HTMLButtonElement | null>>({
    modern: null, classic: null, minimal: null,
  });

  const move = useCallback((delta: number) => {
    const idx = TEMPLATES.findIndex(t => t.id === value);
    const next = TEMPLATES[(idx + delta + TEMPLATES.length) % TEMPLATES.length];
    onChange(next.id);
    refs.current[next.id]?.focus();
  }, [value, onChange]);

  return (
    <div role="radiogroup" aria-label="Invoice template" className="grid grid-cols-3 gap-3">
      {TEMPLATES.map(t => {
        const active = t.id === value;
        return (
          <button
            key={t.id}
            ref={el => { refs.current[t.id] = el; }}
            role="radio"
            aria-checked={active}
            tabIndex={active ? 0 : -1}
            onClick={() => onChange(t.id)}
            onKeyDown={(e) => {
              if (e.key === 'ArrowRight' || e.key === 'ArrowDown') { e.preventDefault(); move(1); }
              else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') { e.preventDefault(); move(-1); }
              else if (e.key === 'Home') { e.preventDefault(); onChange(TEMPLATES[0].id); refs.current[TEMPLATES[0].id]?.focus(); }
              else if (e.key === 'End') { e.preventDefault(); const last = TEMPLATES[TEMPLATES.length - 1]; onChange(last.id); refs.current[last.id]?.focus(); }
            }}
            className={`group flex flex-col items-center gap-2 p-4 rounded-lg border-2 transition-all ${
              active
                ? 'border-violet-500 bg-violet-50 shadow-md'
                : 'border-slate-200 bg-white hover:border-slate-300'
            }`}
          >
            <div className="w-full h-16 rounded" style={{ background: t.swatch }} />
            <span className={`text-sm font-medium ${active ? 'text-violet-700' : 'text-slate-700'}`}>
              {t.label}
            </span>
          </button>
        );
      })}
    </div>
  );
}
