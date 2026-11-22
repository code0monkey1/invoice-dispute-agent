/// <reference types="node" />
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const html = readFileSync(resolve(process.cwd(), 'index.html'), 'utf8');
const css = readFileSync(resolve(process.cwd(), 'src/index.css'), 'utf8');

describe('typefaces', () => {
  it('loads only Schibsted Grotesk and Source Serif 4', () => {
    const link = html.match(/<link href="(https:\/\/fonts\.googleapis\.com\/css2[^"]+)"/);
    expect(link).not.toBeNull();
    const families = [...link![1].matchAll(/family=([^:&]+)/g)].map((m) => decodeURIComponent(m[1]).replace(/\+/g, ' '));
    expect(families).toEqual(['Schibsted Grotesk', 'Source Serif 4']);
  });

  it('sets Schibsted Grotesk as the theme sans and Source Serif 4 as the serif', () => {
    expect(css).toMatch(/--font-sans:\s*"Schibsted Grotesk"/);
    expect(css).toMatch(/--font-serif:\s*"Source Serif 4"/);
  });

  it('does not override the font on every element or heading', () => {
    expect(css).not.toMatch(/^\*\s*\{[^}]*font-family/m);
    expect(css).not.toMatch(/h1,\s*h2[^{]*\{[^}]*font-family/);
  });
});
