import { useEffect, useState } from 'react';
import { Linking, Pressable, Text, View } from 'react-native';

import { ApiError, WEB_URL, errorText } from '../api';
import { useAuth } from '../auth';
import { takeLoginIntent } from '../loginIntent';
import { useNav, type Route } from '../nav';
import { dedupePhonePrefix, passwordProblem, t } from '../shared';
import { FONT, useTheme } from '../theme';
import { Banner, Button, Card, Field, H1, LangSwitch, MenuRow, P, Row, Screen } from '../ui';

const PHONE = /^\+998\d{9}$/;
export type LoginMode = 'password' | 'code' | 'reset';

/**
 * Kirish, as on the web (apps/web/src/pages/Login.tsx, owner 2026-11-15): username or phone + password first;
 * a one-time code via Telegram second (the sign-up path); "Parolni unutdingizmi?" = phone → code → new password.
 * The on-screen code exists only in development.
 */
export function LoginScreen({ then, mode: initialMode, notice: initialNotice }: { then?: Route; mode?: LoginMode; notice?: string }) {
  const { requestCode, verify, passwordLogin, resetPassword } = useAuth();
  const nav = useNav();
  const [intent] = useState(takeLoginIntent);
  const [mode, setMode] = useState<LoginMode>(intent?.mode ?? initialMode ?? 'password');
  const [notice, setNotice] = useState(intent?.notice ?? initialNotice);
  const [login, setLogin] = useState('');
  const [password, setPassword] = useState('');
  const [password2, setPassword2] = useState('');
  const [show, setShow] = useState(false);
  const [pwErr, setPwErr] = useState<string>();
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

  const done = () => {
    nav.reset(); // nothing of a previous account stays open
    if (then) nav.push(then);
  };
  const switchMode = (next: LoginMode) => {
    setMode(next);
    setStep(null);
    setErr(undefined);
    setPwErr(undefined);
    setNotice(undefined);
    setPassword('');
    setPassword2('');
  };

  const signIn = async () => {
    if (!login.trim() || !password) return setErr(t('err.invalid_credentials'));
    setBusy(true);
    setErr(undefined);
    try {
      await passwordLogin(login.trim(), password);
      done();
    } catch (e) {
      setErr(errorText(e)); // invalid_credentials / password_login_blocked / rate_limited, chosen by code
      setPassword('');
    } finally {
      setBusy(false);
    }
  };

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
    if (mode === 'reset') {
      const problem = passwordProblem(password, phone);
      if (problem || password !== password2) return setPwErr(t(problem ?? 'pw.mismatch'));
    } else if (!agree) return setErr(t('legal.agreeRequired'));
    setPwErr(undefined);
    setBusy(true);
    setErr(undefined);
    try {
      if (mode === 'reset') await resetPassword(phone, code.trim(), password);
      else await verify(phone, code.trim(), true);
      done();
    } catch (e) {
      if (e instanceof ApiError && e.code === 'weak_password') setPwErr(e.message);
      else setErr(e instanceof ApiError ? e.message : t('common.actionFailed'));
    } finally {
      setBusy(false);
    }
  };

  const wait = step ? Math.max(0, Math.ceil((step.resendAt - now) / 1000)) : 0;
  return (
    <Screen>
      {nav.canGoBack && (
        <Row>
          <Button kind="ghost" small label={t('profile.back')} onPress={nav.back} />
        </Row>
      )}
      <LangSwitch />
      <H1>{mode === 'reset' ? t('login.reset.title') : t('login.title')}</H1>
      <P muted>{t(mode === 'password' ? 'login.pw.lead' : mode === 'reset' ? 'login.reset.lead' : 'login.pw.codeLead')}</P>
      {notice && <Banner text={notice} />}
      {mode === 'password' ? (
        <>
          <Field
            label={t('login.pw.login')}
            hint={t('login.pw.loginHint')}
            value={login}
            onChangeText={setLogin}
            autoComplete="username"
            textContentType="username"
            autoCapitalize="none"
            autoCorrect={false}
          />
          <Field
            label={t('login.pw.password')}
            value={password}
            onChangeText={setPassword}
            secureTextEntry={!show}
            autoComplete="current-password"
            textContentType="password"
            autoCapitalize="none"
            error={err}
            onSubmitEditing={() => void signIn()}
          />
          <ConsentCheck checked={show} onChange={setShow} label={t('login.pw.show')} />
          <Button label={t('login.submit')} busy={busy} onPress={() => void signIn()} />
          <Row>
            <Button kind="ghost" small label={t('login.pw.useCode')} onPress={() => switchMode('code')} />
            <Button kind="ghost" small label={t('login.pw.forgot')} onPress={() => switchMode('reset')} />
          </Row>
          <P muted>{t('login.pw.firstTime')}</P>
        </>
      ) : !step ? (
        <>
          <Field label={t('login.phone')} hint={t('login.phoneHint')} value={phone} onChangeText={setPhone} keyboardType="phone-pad" autoComplete="tel" error={err} />
          <Button label={t('login.sendCode')} busy={busy} onPress={() => void send()} />
        </>
      ) : (
        <>
          <P>
            {t('login.codeSentBefore')}
            <Text style={{ fontFamily: FONT.bold }}>{phone}</Text>
            {t('login.codeSentAfter')}
          </P>
          {step.devOtp && (
            <Banner text={`${t('login.devBefore')}${step.devOtp}${t('login.devAfter')}`} />
          )}
          <Field label={t('login.code')} value={code} onChangeText={setCode} keyboardType="number-pad" autoComplete="one-time-code" maxLength={8} error={err} />
          {mode === 'reset' ? (
            <>
              <Field
                label={t('pw.new')}
                hint={t('pw.rules')}
                value={password}
                onChangeText={setPassword}
                secureTextEntry={!show}
                autoComplete="new-password"
                textContentType="newPassword"
                autoCapitalize="none"
                error={pwErr}
              />
              <Field
                label={t('pw.repeat')}
                value={password2}
                onChangeText={setPassword2}
                secureTextEntry={!show}
                autoComplete="new-password"
                textContentType="newPassword"
                autoCapitalize="none"
              />
              <ConsentCheck checked={show} onChange={setShow} label={t('login.pw.show')} />
              <P muted>{t('login.reset.note')}</P>
            </>
          ) : (
            <ConsentCheck checked={agree} onChange={setAgree} />
          )}
          <Button label={mode === 'reset' ? t('login.reset.submit') : t('login.submit')} busy={busy} onPress={() => void submit()} />
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
      {mode !== 'password' && <Button kind="ghost" label={t('login.pw.usePassword')} onPress={() => switchMode('password')} />}
      <P muted>{t('login.disclaimer')}</P>
      {/* As on the web login page: Settings is reachable before signing in (language, alphabet, theme). */}
      <Card style={{ gap: 0, paddingVertical: 8 }}>
        <MenuRow title={t('settings.link')} hint={t('settings.linkHint')} onPress={() => nav.push({ name: 'settings' })} />
      </Card>
    </Screen>
  );
}

/** The documents live on the web app (single published text); consent is recorded with their versions. */
/** `label` reuses the same checkbox for another confirmation (account deletion); the document links then stay out. */
export function ConsentCheck({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label?: string }) {
  const { palette } = useTheme();
  return (
    <View style={{ gap: 8 }}>
      <Pressable
        role="checkbox"
        aria-checked={checked}
        aria-label={label ?? t('legal.agree')}
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
        <Text style={{ fontFamily: FONT.body, color: palette.fg, flex: 1, fontSize: 15 }}>{label ?? t('legal.agree')}</Text>
      </Pressable>
      {label ? null : WEB_URL ? (
        <Row>
          <Button kind="ghost" small label={t('legal.terms')} onPress={() => void Linking.openURL(`${WEB_URL}/terms`)} />
          <Button kind="ghost" small label={t('legal.privacy')} onPress={() => void Linking.openURL(`${WEB_URL}/privacy`)} />
        </Row>
      ) : (
        <Text style={{ fontFamily: FONT.body, color: palette.muted }}>{t('mobile.webMissing')}</Text>
      )}
    </View>
  );
}
