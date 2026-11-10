import { useEffect, useState } from 'react';
import { Linking, Pressable, Text, View } from 'react-native';

import { ApiError, WEB_URL, errorText } from '../api';
import { useAuth } from '../auth';
import { useNav, type Route } from '../nav';
import { dedupePhonePrefix, t } from '../shared';
import { useTheme } from '../theme';
import { Banner, Button, ErrorText, Field, H1, P, Row, Screen } from '../ui';

const PHONE = /^\+998\d{9}$/;

/** Phone + one-time code (Telegram Gateway in production). The on-screen code exists only in development. */
export function LoginScreen({ then }: { then?: Route }) {
  const { requestCode, verify } = useAuth();
  const nav = useNav();
  const [phone, setPhone] = useState('+998');
  const [code, setCode] = useState('');
  const [step, setStep] = useState<{ devOtp?: string | null; resendAt: number } | null>(null);
  const [agree, setAgree] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string>();
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  const send = async () => {
    const value = dedupePhonePrefix(phone);
    setPhone(value);
    if (!PHONE.test(value)) return setErr(t('login.phoneHint'));
    setBusy(true);
    setErr(undefined);
    try {
      const res = await requestCode(value);
      setStep({ devOtp: res.development_otp, resendAt: Date.now() + (res.resend_after_seconds ?? 60) * 1000 });
    } catch (e) {
      setErr(errorText(e));
    } finally {
      setBusy(false);
    }
  };

  const submit = async () => {
    if (!agree) return setErr(t('legal.agreeRequired'));
    setBusy(true);
    setErr(undefined);
    try {
      await verify(phone, code.trim(), true);
      nav.reset(); // nothing of a previous account stays open
      if (then) nav.push(then);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : t('common.actionFailed'));
    } finally {
      setBusy(false);
    }
  };

  const wait = step ? Math.max(0, Math.ceil((step.resendAt - now) / 1000)) : 0;
  return (
    <Screen>
      <H1>{t('login.title')}</H1>
      <P muted>{t('login.lead')}</P>
      {!step ? (
        <>
          <Field label={t('login.phone')} hint={t('login.phoneHint')} value={phone} onChangeText={setPhone} keyboardType="phone-pad" autoComplete="tel" />
          {err && <ErrorText text={err} />}
          <Button label={t('login.sendCode')} busy={busy} onPress={() => void send()} />
        </>
      ) : (
        <>
          <P>
            {t('login.codeSentBefore')}
            <Text style={{ fontWeight: '700' }}>{phone}</Text>
            {t('login.codeSentAfter')}
          </P>
          {step.devOtp && (
            <Banner text={`${t('login.devBefore')}${step.devOtp}${t('login.devAfter')}`} />
          )}
          <Field label={t('login.code')} value={code} onChangeText={setCode} keyboardType="number-pad" autoComplete="one-time-code" maxLength={8} />
          <ConsentCheck checked={agree} onChange={setAgree} />
          {err && <ErrorText text={err} />}
          <Button label={t('login.submit')} busy={busy} onPress={() => void submit()} />
          <Row>
            <Button kind="ghost" small label={t('login.changeNumber')} onPress={() => setStep(null)} />
            <Button
              kind="ghost"
              small
              disabled={wait > 0 || busy}
              label={wait > 0 ? t('login.resendIn', { n: wait }) : t('login.resend')}
              onPress={() => void send()}
            />
          </Row>
        </>
      )}
      <P muted>{t('login.disclaimer')}</P>
    </Screen>
  );
}

/** The documents live on the web app (single published text); consent is recorded with their versions. */
export function ConsentCheck({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  const { palette } = useTheme();
  return (
    <View style={{ gap: 8 }}>
      <Pressable
        role="checkbox"
        aria-checked={checked}
        aria-label={t('legal.agree')}
        onPress={() => onChange(!checked)}
        style={{ flexDirection: 'row', gap: 10, alignItems: 'flex-start', minHeight: 44 }}
      >
        <View
          style={{
            width: 24,
            height: 24,
            borderRadius: 6,
            borderWidth: 2,
            borderColor: checked ? palette.accent : palette.line,
            backgroundColor: checked ? palette.primary : 'transparent',
          }}
        />
        <Text style={{ color: palette.fg, flex: 1, fontSize: 15 }}>{t('legal.agree')}</Text>
      </Pressable>
      {WEB_URL ? (
        <Row>
          <Button kind="ghost" small label={t('legal.terms')} onPress={() => void Linking.openURL(`${WEB_URL}/terms`)} />
          <Button kind="ghost" small label={t('legal.privacy')} onPress={() => void Linking.openURL(`${WEB_URL}/privacy`)} />
        </Row>
      ) : (
        <Text style={{ color: palette.muted }}>{t('mobile.webMissing')}</Text>
      )}
    </View>
  );
}
