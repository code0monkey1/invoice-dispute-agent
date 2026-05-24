import { useEffect, useRef, useState } from 'react';
import { pdf } from '@react-pdf/renderer';
import { getTemplate } from './pdf';
import type { InvoiceData } from '../../types';

interface Props {
  data: InvoiceData;
  className?: string;
}

/**
 * Flicker-free live PDF preview.
 *
 * Two iframes are stacked. One is "visible" (opacity 1) and holds the
 * current PDF; the other is "buffer" (opacity 0) and is used to preload
 * the next PDF off-screen. Once the buffer iframe fires `onLoad`, we
 * swap which one is visible and revoke the now-unused blob URL. The user
 * never sees a blank frame — the old PDF stays on screen until the new
 * one is fully painted.
 */
export function PDFPreview({ data, className }: Props) {
  // Which iframe slot ("a" or "b") is currently visible.
  const [activeSlot, setActiveSlot] = useState<'a' | 'b'>('a');
  // URLs and the data shape behind each slot.
  const [urlA, setUrlA] = useState<string | null>(null);
  const [urlB, setUrlB] = useState<string | null>(null);
  // Track in-flight renders so a slower one can't overwrite a newer one.
  const generation = useRef(0);
  // Track the next pending URL so the iframe's onLoad knows when to swap.
  const pendingSlot = useRef<'a' | 'b' | null>(null);

  useEffect(() => {
    let cancelled = false;
    const myGen = ++generation.current;
    const { Component } = getTemplate(data.template);

    pdf(<Component data={data} />).toBlob()
      .then((blob) => {
        if (cancelled || myGen !== generation.current) return;
        const next = URL.createObjectURL(blob);
        // Write the new URL into the inactive slot.
        if (activeSlot === 'a') {
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
  }, [data, activeSlot]);

  // Cleanup all URLs on unmount.
  useEffect(() => {
    return () => {
      if (urlA) URL.revokeObjectURL(urlA);
      if (urlB) URL.revokeObjectURL(urlB);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleLoaded = (slot: 'a' | 'b') => {
    // Only flip if this is the slot we were waiting on.
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
