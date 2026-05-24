import { useEffect, useRef, useState } from 'react';
import { pdf } from '@react-pdf/renderer';
import { getTemplate } from './pdf';
import type { InvoiceData } from '../../types';

interface Props {
  data: InvoiceData;
  className?: string;
}

/**
 * Flicker-free live PDF preview using two stacked iframes (A / B).
 *
 * One iframe is visible; the other preloads the next PDF off-screen.
 * On `onLoad` of the off-screen iframe we flip which one is visible —
 * the user never sees a blank frame.
 *
 * Critical: this effect must only re-fire when `data` changes. We read
 * which slot is currently active via a ref, not via state, so that a
 * swap (which mutates state) doesn't re-trigger the effect.
 */
export function PDFPreview({ data, className }: Props) {
  const [activeSlot, setActiveSlot] = useState<'a' | 'b'>('a');
  const activeSlotRef = useRef<'a' | 'b'>('a');
  useEffect(() => { activeSlotRef.current = activeSlot; }, [activeSlot]);

  const [urlA, setUrlA] = useState<string | null>(null);
  const [urlB, setUrlB] = useState<string | null>(null);
  const generation = useRef(0);
  const pendingSlot = useRef<'a' | 'b' | null>(null);

  useEffect(() => {
    let cancelled = false;
    const myGen = ++generation.current;
    const { Component } = getTemplate(data.template);

    pdf(<Component data={data} />).toBlob()
      .then((blob) => {
        if (cancelled || myGen !== generation.current) return;
        const next = URL.createObjectURL(blob);
        // Write into the slot that is NOT currently visible.
        if (activeSlotRef.current === 'a') {
          setUrlB((old) => { if (old) URL.revokeObjectURL(old); return next; });
          pendingSlot.current = 'b';
        } else {
          setUrlA((old) => { if (old) URL.revokeObjectURL(old); return next; });
          pendingSlot.current = 'a';
        }
      })
      .catch((err) => {
        if (cancelled) return;
        console.error('PDF preview render failed:', err);
      });

    return () => { cancelled = true; };
  }, [data]);

  // Revoke remaining URLs on unmount.
  useEffect(() => {
    return () => {
      if (urlA) URL.revokeObjectURL(urlA);
      if (urlB) URL.revokeObjectURL(urlB);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleLoaded = (slot: 'a' | 'b') => {
    if (pendingSlot.current === slot) {
      pendingSlot.current = null;
      setActiveSlot(slot);
    }
  };

  return (
    <div className={`${className ?? 'w-full h-full min-h-[600px]'} relative`}>
      {urlA && (
        <iframe
          title="Invoice PDF preview A"
          src={`${urlA}#toolbar=0&navpanes=0&scrollbar=1`}
          onLoad={() => handleLoaded('a')}
          className="absolute inset-0 w-full h-full transition-opacity duration-150"
          style={{
            border: 'none',
            background: '#fff',
            opacity: activeSlot === 'a' ? 1 : 0,
            pointerEvents: activeSlot === 'a' ? 'auto' : 'none',
          }}
        />
      )}
      {urlB && (
        <iframe
          title="Invoice PDF preview B"
          src={`${urlB}#toolbar=0&navpanes=0&scrollbar=1`}
          onLoad={() => handleLoaded('b')}
          className="absolute inset-0 w-full h-full transition-opacity duration-150"
          style={{
            border: 'none',
            background: '#fff',
            opacity: activeSlot === 'b' ? 1 : 0,
            pointerEvents: activeSlot === 'b' ? 'auto' : 'none',
          }}
        />
      )}
      {!urlA && !urlB && (
        <div className="absolute inset-0 flex items-center justify-center text-sm text-slate-400">
          Generating preview…
        </div>
      )}
    </div>
  );
}
