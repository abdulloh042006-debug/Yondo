import { getUzAlphabet, LANGS, setLang, setUzAlphabet, t, UZ_ALPHABETS, useLang } from './index';

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

/** Uzbek spelling: 1995 alphabet (o‘ g‘ sh ch) or 2026 alphabet (ö ğ ş ç). Applies whenever the UI is Uzbek. */
export function AlphabetPicker() {
  useLang();
  const value = getUzAlphabet();
  return (
    <div role="group" aria-label={t('settings.alphabet')} className="theme-picker alphabet-picker">
      {UZ_ALPHABETS.map((a) => (
        <button key={a.id} type="button" className="theme-opt" lang="uz" aria-pressed={value === a.id} onClick={() => setUzAlphabet(a.id)}>
          <span className="stack" style={{ gap: 0, textAlign: 'left' }}>
            <b>{a.label} · {a.letters}</b>
            <span className="hint">{t(a.id === '1995' ? 'settings.alphabet.1995' : 'settings.alphabet.2026')}</span>
          </span>
        </button>
      ))}
    </div>
  );
}
