import { Fragment, useEffect, useState, type ReactNode } from 'react';
import { t, useLang } from '../i18n';
import { Loading } from '../ui/feedback';
import { LEGAL_VERSIONS, type LegalDoc } from './versions';

// Each document is its own lazy chunk; the text is the owner's Uzbek draft (1995 spelling, as authored).
const SOURCES: Record<LegalDoc, () => Promise<string>> = {
  terms: () => import('./terms.md?raw').then((m) => m.default),
  privacy: () => import('./privacy.md?raw').then((m) => m.default),
};

function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith('**') && part.endsWith('**') ? <b key={i}>{part.slice(2, -2)}</b> : <Fragment key={i}>{part}</Fragment>,
  );
}

/** Minimal Markdown (headings, lists, paragraphs, bold, hard breaks): enough for these documents, no dependency. */
export function Markdown({ source }: { source: string }) {
  return (
    <>
      {source
        .trim()
        .split(/\n{2,}/)
        .map((block, i) => {
          if (block.startsWith('# ')) return <h1 key={i}>{inline(block.slice(2))}</h1>;
          if (block.startsWith('## ')) return <h2 key={i}>{inline(block.slice(3))}</h2>;
          const lines = block.split('\n');
          if (lines.every((l) => l.startsWith('- '))) {
            return <ul key={i}>{lines.map((l, j) => <li key={j}>{inline(l.slice(2))}</li>)}</ul>;
          }
          return (
            <p key={i}>
              {lines.map((l, j) => (
                <Fragment key={j}>
                  {inline(l.replace(/ {2}$/, ''))}
                  {j < lines.length - 1 && (l.endsWith('  ') ? <br /> : ' ')}
                </Fragment>
              ))}
            </p>
          );
        })}
    </>
  );
}

export function LegalPage({ doc }: { doc: LegalDoc }) {
  const lang = useLang();
  const [text, setText] = useState<string>();
  useEffect(() => {
    let live = true;
    void SOURCES[doc]().then((value) => live && setText(value));
    return () => {
      live = false;
    };
  }, [doc]);
  return (
    <div className="stack" style={{ gap: 16, maxWidth: 760, margin: '0 auto', width: '100%' }}>
      <p className="banner">{t('legal.draftBanner')}</p>
      {lang !== 'uz' && <p className="hint">{t('legal.onlyUz')}</p>}
      <p className="hint mono">{t('legal.version', { version: LEGAL_VERSIONS[doc] })}</p>
      {text === undefined ? (
        <Loading rows={4} />
      ) : (
        <article className="glass pad legal-doc" lang="uz">
          <Markdown source={text} />
        </article>
      )}
    </div>
  );
}
