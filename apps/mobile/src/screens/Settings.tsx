import Constants from 'expo-constants';
import { View } from 'react-native';

import { WEB_URL } from '../api';
import { useNav } from '../nav';
import { LANGS, UZ_ALPHABETS, getLang, getUzAlphabet, setLang, setUzAlphabet, t, useLang } from '../shared';
import { useTheme, type ThemeChoice } from '../theme';
import { Button, Card, Chip, ChipGroup, H1, H2, MenuRow, P, Row, Screen } from '../ui';
import { openWeb } from './Account';

/** Language, Uzbek alphabet and theme live here only (owner rule). Opened from the Profil hub or from Kirish. */
export function SettingsScreen() {
  useLang();
  const nav = useNav();
  const { choice, setChoice } = useTheme();
  const themes: { id: ThemeChoice; label: string }[] = [
    { id: 'system', label: t('mobile.themeSystem') },
    { id: 'yondo', label: t('theme.yondo.label') },
    { id: 'yondo-tun', label: t('theme.yondo-tun.label') },
  ];
  return (
    <Screen>
      {nav.canGoBack && (
        <Row>
          <Button kind="ghost" small label={t('profile.back')} onPress={nav.back} />
        </Row>
      )}
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
      <Card style={{ gap: 0, paddingVertical: 8 }}>
        <View style={{ paddingHorizontal: 8, paddingBottom: 4 }}>
          <H2>{t('settings.safety')}</H2>
        </View>
        {WEB_URL ? (
          <MenuRow title={t('help.title')} hint={t('settings.safetyHint')} web onPress={() => openWeb('/help')} />
        ) : (
          <P muted style={{ paddingHorizontal: 8 }}>{t('mobile.webMissing')}</P>
        )}
      </Card>
      <P muted>{`${t('settings.version')}: ${Constants.expoConfig?.version ?? '—'}`}</P>
    </Screen>
  );
}
