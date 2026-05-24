import type { ComponentType } from 'react';
import type { InvoiceData, TemplateId } from '../../../types';
import { ModernTemplate } from './ModernTemplate';
import { ClassicTemplate } from './ClassicTemplate';
import { MinimalTemplate } from './MinimalTemplate';

export interface TemplateDescriptor {
  id: TemplateId;
  label: string;
  Component: ComponentType<{ data: InvoiceData }>;
  swatch: string;
}

export const TEMPLATES: TemplateDescriptor[] = [
  { id: 'modern',  label: 'Modern',  Component: ModernTemplate,  swatch: '#FF6B35' },
  { id: 'classic', label: 'Classic', Component: ClassicTemplate, swatch: '#1F2937' },
  { id: 'minimal', label: 'Minimal', Component: MinimalTemplate, swatch: '#000000' },
];

export function getTemplate(id: TemplateId): TemplateDescriptor {
  const t = TEMPLATES.find(t => t.id === id);
  if (!t) throw new Error(`Unknown template id: ${id}`);
  return t;
}
