import { useEffect, useRef, useState } from 'react';
import { pdf } from '@react-pdf/renderer';
import { getTemplate } from './pdf';
import type { InvoiceData } from '../../types';

interface Props {
  data: InvoiceData;
  className?: string;
}

/**
 * Live PDF preview without the flicker of <PDFViewer>.
 *
 * <PDFViewer> from @react-pdf/renderer recreates its iframe on every prop
 * change, producing a visible blank-and-redraw flash on each keystroke.
 *
 * Instead we render a plain <iframe> whose `src` is a Blob URL we generate
 * ourselves. When `data` changes we kick off a background `pdf().toBlob()`,
 * and only update the iframe src once the new blob is ready — the iframe
 * DOM element itself stays mounted, so the browser swaps the document in
 * place. Old object URLs are revoked to keep memory bounded.
 */
export function PDFPreview({ data, className }: Props) {
  const [url, setUrl] = useState<string | null>(null);
  const generation = useRef(0);

  useEffect(() => {
    let cancelled = false;
    const myGen = ++generation.current;
    const { Component } = getTemplate(data.template);

    pdf(<Component data={data} />).toBlob()
      .then((blob) => {
        if (cancelled || myGen !== generation.current) return;
        const next = URL.createObjectURL(blob);
        setUrl((prev) => {
          if (prev) URL.revokeObjectURL(prev);
          return next;
        });
      })
      .catch((err) => {
        if (cancelled) return;
        console.error('PDF preview render failed:', err);
      });

    return () => {
      cancelled = true;
    };
  }, [data]);

  // Revoke the last URL on unmount.
  useEffect(() => {
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
    // We intentionally only run this cleanup on unmount; on each render the
    // value of `url` is captured via closure and the per-update revoke
    // happens inside the data effect above.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className={className ?? 'w-full h-full min-h-[600px]'}>
      {url ? (
        <iframe
          title="Invoice PDF preview"
          src={`${url}#toolbar=0&navpanes=0&scrollbar=1`}
          className="w-full h-full"
          style={{ border: 'none', background: '#fff' }}
        />
      ) : (
        <div className="w-full h-full flex items-center justify-center text-sm text-slate-400">
          Generating preview…
        </div>
      )}
    </div>
  );
}
