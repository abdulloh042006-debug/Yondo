import Constants from 'expo-constants';
import { Linking } from 'react-native';

import { WEB_URL } from '../api';
import { useAuth } from '../auth';
import { useNav } from '../nav';
import { LANGS, UZ_ALPHABETS, getLang, getUzAlphabet, prettyPhone, setLang, setUzAlphabet, t, useLang } from '../shared';
import { useTheme, type ThemeChoice } from '../theme';
import { Button, Card, Chip, ChipGroup, H1, H2, P, Row, Screen } from '../ui';

/** Language, Uzbek alphabet and theme live here only (owner rule), plus links to what is still web-only. */
export function SettingsScreen() {
  useLang();
  const nav = useNav();
  const { user, logout } = useAuth();
  const { choice, setChoice } = useTheme();
  const themes: { id: ThemeChoice; label: string }[] = [
    { id: 'system', label: t('mobile.themeSystem') },
    { id: 'yondo', label: t('theme.yondo.label') },
    { id: 'yondo-tun', label: t('theme.yondo-tun.label') },
  ];
  const openWeb = (path: string) => void Linking.openURL(`${WEB_URL}${path}`);
  return (
    <Screen>
      <H1>{t('settings.title')}</H1>
      <Card>
        <H2>{t('settings.language')}</H2>
        <ChipGroup label={t('settings.language')}>
          {LANGS.map((l) => (
            <Chip key={l.id} label={l.label} selected={getLang() === l.id} onPress={() => void setLang(l.id).catch(() => {})} />
          ))}
        </ChipGroup>
        {getLang() === 'uz' && (
          <>
            <P>{t('settings.alphabet')}</P>
            <ChipGroup label={t('settings.alphabet')}>
              {UZ_ALPHABETS.map((a) => (
                <Chip key={a.id} label={`${a.label} (${a.letters})`} selected={getUzAlphabet() === a.id} onPress={() => setUzAlphabet(a.id)} />
              ))}
            </ChipGroup>
          </>
        )}
      </Card>
      <Card>
        <H2>{t('settings.themeGroup')}</H2>
        <ChipGroup label={t('settings.themeGroup')}>
          {themes.map((th) => (
            <Chip key={th.id} label={th.label} selected={choice === th.id} onPress={() => setChoice(th.id)} />
          ))}
        </ChipGroup>
      </Card>
      <Card>
        <H2>{t('settings.account')}</H2>
        {user ? (
          <>
            <P>{`${t('account.phone')}: ${prettyPhone(user.phone_number)}`}</P>
            <Button kind="ghost" label={t('account.logout')} onPress={() => void logout()} />
          </>
        ) : (
          <Button label={t('nav.login')} onPress={() => nav.push({ name: 'login' })} />
        )}
      </Card>
      <Card>
        <H2>{t('settings.safety')}</H2>
        <P muted>{t('mobile.webOnly')}</P>
        {WEB_URL ? (
          <Row>
            <Button small kind="ghost" label={t('help.title')} onPress={() => openWeb('/help')} />
            <Button small kind="ghost" label={t('legal.terms')} onPress={() => openWeb('/terms')} />
            <Button small kind="ghost" label={t('legal.privacy')} onPress={() => openWeb('/privacy')} />
            {user && <Button small kind="ghost" label={t('account.delete.title')} onPress={() => openWeb('/account')} />}
          </Row>
        ) : (
          <P muted>{t('mobile.webMissing')}</P>
        )}
      </Card>
      <P muted>{`${t('settings.version')}: ${Constants.expoConfig?.version ?? '—'}`}</P>
    </Screen>
  );
}
