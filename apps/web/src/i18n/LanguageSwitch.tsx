import { LANGS, setLang, t, useLang } from './index';

/** Compact UZ | RU | EN switch for the top bar. No flags (they mean countries, not languages); endonym in the accessible name. */
export function LanguageSwitch() {
  const lang = useLang();
  return (
    <div role="group" aria-label={t('settings.languageGroup')} className="lang-switch">
      {LANGS.map((l) => (
        <button
          key={l.id}
          type="button"
          className="lang-opt"
          lang={l.id}
          aria-pressed={lang === l.id}
          aria-label={`${l.short} — ${l.label}`}
          title={l.label}
          onClick={() => {
            setLang(l.id).catch(() => {
              /* the language chunk could not be loaded: stay in the current language */
            });
          }}
        >
          {l.short}
        </button>
      ))}
    </div>
  );
}
