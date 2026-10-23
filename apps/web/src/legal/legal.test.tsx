import { render, screen } from '@testing-library/react';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { Markdown } from './LegalPage';
import { LEGAL_VERSIONS } from './versions';

describe('legal documents', () => {
  it('client versions equal the server versions (consent is refused otherwise)', () => {
    const py = readFileSync(resolve(process.cwd(), '../api/src/yondo_api/account/legal.py'), 'utf8');
    for (const [doc, version] of Object.entries(LEGAL_VERSIONS)) expect(py).toContain(`'${doc}': '${version}'`);
  });
  it('renders headings, lists, bold and hard line breaks', () => {
    render(<Markdown source={'# Title\n\n**Holati:** loyiha  \nikkinchi qator\n\n## 1. Bo‘lim\n\n- bir\n- **ikki**'} />);
    expect(screen.getByRole('heading', { level: 1, name: 'Title' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: '1. Bo‘lim' })).toBeInTheDocument();
    expect(screen.getAllByRole('listitem')).toHaveLength(2);
    expect(screen.getByText('Holati:').tagName).toBe('B');
    expect(document.querySelector('p br')).not.toBeNull();
  });
  it('the drafts never print placeholder brackets or an e-mail address', () => {
    for (const name of ['terms.md', 'privacy.md']) {
      const text = readFileSync(resolve(process.cwd(), 'src/legal', name), 'utf8');
      expect(text).not.toMatch(/\[[^\]]*(sana|email|pochta|nomi|manzil)[^\]]*\]/i);
      expect(text).not.toMatch(/@[a-z0-9-]+\./i);
      expect(text).toContain('30 kun');
    }
  });
});
