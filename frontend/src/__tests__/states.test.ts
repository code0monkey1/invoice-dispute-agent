/// <reference types="node" />
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const css = readFileSync(resolve(process.cwd(), 'src/index.css'), 'utf8');

describe('interaction states', () => {
  it('shows a 2px ink focus ring with a 2px offset on every focusable element', () => {
    const rule = css.match(/(?:^|\n):focus-visible\s*\{([^}]*)\}/);
    expect(rule).not.toBeNull();
    expect(rule![1]).toMatch(/outline:\s*2px solid var\(--color-ink\)/);
    expect(rule![1]).toMatch(/outline-offset:\s*2px/);
  });

  it('turns off the pulse, fade-up and middleware animations for reduced motion', () => {
    const block = css.match(/@media \(prefers-reduced-motion: reduce\)\s*\{([\s\S]*?)\n\}/);
    expect(block).not.toBeNull();
    for (const name of ['animate-pulse-dot', 'animate-middleware-pulse', 'animate-fade-up']) {
      expect(block![1]).toContain(`.${name}`);
    }
    expect(block![1]).toMatch(/animation:\s*none/);
  });

  it('no longer has an infinite button shimmer', () => {
    expect(css).not.toMatch(/shimmer/);
    expect(css).not.toMatch(/btn-gradient/);
  });
});
