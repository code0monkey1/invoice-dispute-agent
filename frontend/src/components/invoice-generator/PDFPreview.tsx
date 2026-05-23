import { PDFViewer } from '@react-pdf/renderer';
import { getTemplate } from './pdf';
import type { InvoiceData } from '../../types';

interface Props {
  data: InvoiceData;
  className?: string;
}

export function PDFPreview({ data, className }: Props) {
  const { Component } = getTemplate(data.template);
  return (
    <div className={className ?? 'w-full h-full min-h-[600px]'}>
      <PDFViewer width="100%" height="100%" showToolbar={false}>
        <Component data={data} />
      </PDFViewer>
    </div>
  );
}
