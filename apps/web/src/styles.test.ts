import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import postcss from 'postcss';
import { describe, expect, it } from 'vitest';

// Guard (2026-11-18): a merge once dropped a closing brace in styles.css. Browsers then nest every later rule inside
// the unclosed block (here: a reduced-motion @media), so whole screens lose their styles without any build error.
describe('styles.css', () => {
  it('parses strictly (no unclosed blocks or other CSS syntax errors)', () => {
    const css = readFileSync(resolve(process.cwd(), 'src/styles.css'), 'utf8');
    expect(() => postcss.parse(css, { from: 'styles.css' })).not.toThrow();
  });

  it('no @media swallows another @media or a theme block (the symptom of a missing brace)', () => {
    const css = readFileSync(resolve(process.cwd(), 'src/styles.css'), 'utf8');
    const root = postcss.parse(css);
    // No @media may contain a nested @media or a theme block: that only happens when a brace is missing.
    root.walkAtRules('media', (media) => {
      media.walkAtRules('media', (inner) => {
        throw new Error(`@media nested in @media at line ${inner.source?.start?.line}`);
      });
      media.walkRules((rule) => {
        if (/\[data-theme=/.test(rule.selector) && !/\[data-theme=/.test(media.params)) {
          throw new Error(`theme block inside @media at line ${rule.source?.start?.line}`);
        }
      });
    });
  });
});
