import { useEffect } from 'react';
import { LANGS, setLang, t, useLang } from './index';

// Switching language remounts the page (see LanguageBoundary); this remembers to put focus back on the chosen button.
let refocus = false;

/** Language choice. Lives on the Settings page next to the theme picker. */
export function LanguagePicker() {
  const lang = useLang();
  useEffect(() => {
    if (!refocus) return;
    refocus = false;
    document.querySelector<HTMLElement>('.lang-picker [aria-pressed="true"]')?.focus();
  }, []);
  return (
    <div role="group" aria-label={t('settings.languageGroup')} className="theme-picker lang-picker">
      {LANGS.map((l) => (
        <button
          key={l.id}
          type="button"
          className="theme-opt"
          lang={l.id}
          aria-pressed={lang === l.id}
          onClick={() => {
            refocus = true;
            setLang(l.id).catch(() => {
              refocus = false; // the language chunk could not be loaded: stay in the current language
            });
          }}
        >
          <span className="stack" style={{ gap: 0, textAlign: 'left' }}>
            <b>{l.label}</b>
            <span className="hint">{l.short}</span>
          </span>
        </button>
      ))}
    </div>
  );
}
