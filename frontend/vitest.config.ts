/// <reference types="vitest" />
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      include: [
        'src/components/invoice-generator/**',
        'src/hooks/useInvoiceGeneratorForm.ts',
        'src/hooks/useSenderProfile.ts',
      ],
      thresholds: {
        lines: 90,
        statements: 90,
        branches: 85,
        functions: 90,
      },
    },
  },
});
