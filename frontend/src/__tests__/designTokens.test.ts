/// <reference types="node" />
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

// vitest runs with `css: false`, which blanks CSS imports, so read the file directly.
const css = readFileSync(resolve(process.cwd(), 'src/index.css'), 'utf8');

function token(name: string): string {
  const match = css.match(new RegExp(`--color-${name}:\\s*(#[0-9A-Fa-f]{6})\\s*;`));
  if (!match) throw new Error(`token --color-${name} not found in index.css`);
  return match[1];
}

function luminance(hex: string): number {
  const channels = [1, 3, 5].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

describe('design tokens', () => {
  it.each(['coral', 'coral-2', 'coral-hover'])('ink on %s meets 4.5:1', (fill) => {
    expect(contrast(token('ink'), token(fill))).toBeGreaterThanOrEqual(4.5);
  });

  it.each(['page', 'card', 'tint'])('coral-text on %s meets 4.5:1', (surface) => {
    expect(contrast(token('coral-text'), token(surface))).toBeGreaterThanOrEqual(4.5);
  });

  it('matches the Paper file values', () => {
    expect(token('coral')).toBe('#FF6B35');
    expect(token('ink')).toBe('#111827');
    expect(token('line')).toBe('#F1E4D8');
    expect(token('coral-text')).toBe('#C2410C');
  });

  describe('.btn-coral', () => {
    const rule = (selector: string) => {
      const match = css.match(new RegExp(`${selector.replace(/[.:()]/g, '\\$&')}\\s*\\{([^}]*)\\}`));
      if (!match) throw new Error(`rule ${selector} not found`);
      return match[1];
    };
    const stops = (body: string) => [...body.matchAll(/var\(--color-([a-z0-9-]+)\)/g)].map((m) => m[1]);

    it('uses an ink label', () => {
      expect(rule('.btn-coral')).toMatch(/color:\s*var\(--color-ink\)/);
    });

    it.each([
      ['default', '.btn-coral'],
      ['hover', '.btn-coral:hover:not(:disabled)'],
    ])('%s gradient keeps 4.5:1 against the ink label', (_state, selector) => {
      const gradient = stops(rule(selector).match(/linear-gradient\(.*\);/)![0]);
      expect(gradient.length).toBeGreaterThanOrEqual(2);
      for (const stop of gradient) {
        expect(contrast(token('ink'), token(stop))).toBeGreaterThanOrEqual(4.5);
      }
    });

    it('is visibly different and not clickable when disabled', () => {
      expect(rule('.btn-coral:disabled')).toMatch(/opacity:\s*0?\.\d+/);
      expect(rule('.btn-coral:disabled')).toMatch(/cursor:\s*not-allowed/);
    });
  });
});
