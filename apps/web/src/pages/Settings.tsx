import { Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { t } from '../i18n';
import { AlphabetPicker, LanguagePicker } from '../i18n/LanguagePicker';
import { Reveal } from '../ui/motion';
import { ThemePicker } from '../ui/theme';

/**
 * Grouped like most consumer apps: language first (most needed, and how you recover from a wrong choice),
 * then appearance, account, privacy & safety, about. Everything here works signed out too.
 */
export function Settings() {
  const { user } = useAuth();
  return (
    <div className="stack" style={{ gap: 20, maxWidth: 760, margin: '0 auto', width: '100%' }}>
      <h1>{t('settings.title')}</h1>
      <Reveal>
        <section className="glass pad stack" aria-labelledby="lang-h">
          <h2 id="lang-h">{t('settings.language')}</h2>
          <p className="muted">{t('settings.languageHint')}</p>
          <LanguagePicker />
          <p className="hint">{t('settings.languageNote')}</p>
          <h3 id="alpha-h" style={{ marginTop: 8 }}>{t('settings.alphabet')}</h3>
          <p className="muted">{t('settings.alphabetHint')}</p>
          <AlphabetPicker />
        </section>
      </Reveal>
      <Reveal delay={0.03}>
        <section className="glass pad stack" aria-labelledby="look-h">
          <h2 id="look-h">{t('settings.look')}</h2>
          <p className="muted">{t('settings.lookHint')}</p>
          <ThemePicker />
        </section>
      </Reveal>
      <Reveal delay={0.05}>
        <section className="glass pad stack" aria-labelledby="acc-h">
          <h2 id="acc-h">{t('settings.account')}</h2>
          {user ? (
            <Link className="btn" to="/account" style={{ width: 'fit-content' }}>{t('settings.accountLink')}</Link>
          ) : (
            <Link className="btn" to="/login" style={{ width: 'fit-content' }}>{t('nav.login')}</Link>
          )}
        </section>
      </Reveal>
      <Reveal delay={0.07}>
        <section className="glass pad stack" aria-labelledby="safe-h">
          <h2 id="safe-h">{t('settings.safety')}</h2>
          <p className="muted">{t('settings.safetyHint')}</p>
          <Link className="btn ghost" to="/help" style={{ width: 'fit-content' }}>{t('help.title')}</Link>
        </section>
      </Reveal>
      <Reveal delay={0.09}>
        <section className="glass pad stack" aria-labelledby="about-h">
          <h2 id="about-h">{t('settings.about')}</h2>
          <p><b>{t('app.title')}</b></p>
          <dl className="kv">
            <dt>{t('settings.version')}</dt><dd>{__APP_VERSION__}</dd>
          </dl>
          <p className="hint">{t('settings.aboutBody')}</p>
        </section>
      </Reveal>
    </div>
  );
}
