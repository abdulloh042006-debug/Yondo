import { LANGS, setLang, t, useLang } from './index';

/** Language choice with full names. Lives on the Settings page next to the theme picker. */
export function LanguagePicker() {
  const lang = useLang();
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
            setLang(l.id).catch(() => {
              /* the language chunk could not be loaded: stay in the current language */
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
