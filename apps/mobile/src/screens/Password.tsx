import { useEffect, useState } from 'react';

import { ApiError, api, errorText, type Schemas } from '../api';
import { useAuth, type User } from '../auth';
import { AUTOFILL } from '../autofill';
import { setLoginIntent } from '../loginIntent';
import { dobProblem, normalizeUsername, passwordProblem, t, usernameValid, type Key } from '../shared';
import { Button, Card, ErrorText, Field, H1, H2, P, Row, Screen } from '../ui';
import { ConsentCheck } from './Login';
import { DeleteAccount } from './Settings';

const CHECK_DELAY_MS = 400;
type CheckState = 'checking' | 'available' | 'taken' | 'reserved' | 'invalid' | 'unknown';
const CHECK_TEXT: Record<Exclude<CheckState, 'unknown'>, Key> = {
  checking: 'setup.checking',
  available: 'setup.available',
  taken: 'setup.taken',
  reserved: 'setup.reserved',
  invalid: 'setup.invalid',
};

/**
 * The web's PasswordSetupGate (apps/web/src/auth/PasswordSetup.tsx): right after a code sign-in an account
 * without a username/password sets both before anything else. `reauth_required` (the code sign-in is older
 * than 15 minutes) signs out and opens the code sign-in with an explanation.
 */
export function PasswordSetupScreen({ user }: { user: User }) {
  const { reload, logout } = useAuth();
  const fixed = user.username ?? null;
  const [username, setUsername] = useState(fixed ?? '');
  const [password, setPassword] = useState('');
  const [password2, setPassword2] = useState('');
  const [show, setShow] = useState(false);
  const [remote, setRemote] = useState<{ name: string; state: CheckState } | null>(null);
  const [errs, setErrs] = useState<{ username?: string; password?: string; repeat?: string; dob?: string; form?: string }>({});
  const [busy, setBusy] = useState(false);
  const askDob = !user.date_of_birth; // 18+ (owner, 2026-11-19)
  const [dob, setDob] = useState('');
  const name = normalizeUsername(username);
  const needsRemote = !fixed && !!name && usernameValid(name);

  useEffect(() => {
    if (!needsRemote) return;
    let live = true;
    const timer = setTimeout(() => {
      api
        .get<Schemas['UsernameAvailability']>(`/auth/username/available?username=${encodeURIComponent(name)}`)
        .then((r) => live && setRemote({ name, state: r.available ? 'available' : (r.reason ?? 'taken') }))
        .catch(() => live && setRemote({ name, state: 'unknown' })); // the server decides on submit
    }, CHECK_DELAY_MS);
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [name, needsRemote]);
  const check: CheckState | null = fixed || !name ? null : !needsRemote ? 'invalid' : remote?.name === name ? remote.state : 'checking';

  const submit = async () => {
    const next: typeof errs = {};
    if (!fixed && !usernameValid(name)) next.username = t('setup.invalid');
    else if (!fixed && (check === 'taken' || check === 'reserved')) next.username = t(CHECK_TEXT[check]);
    const problem = passwordProblem(password, user.phone_number);
    if (problem) next.password = t(problem);
    else if (password !== password2) next.repeat = t('pw.mismatch');
    // Under 18 still goes to the server, which refuses it and keeps a 30-day cooldown for the number.
    if (askDob && dobProblem(dob) === 'age.invalid') next.dob = t('age.invalid');
    setErrs(next);
    if (Object.keys(next).length) return;
    setBusy(true);
    try {
      await api.post('/auth/registration', { username: fixed ?? name, password, ...(askDob ? { date_of_birth: dob } : {}) });
      await reload();
    } catch (e) {
      const code = e instanceof ApiError ? e.code : '';
      if (code === 'reauth_required') {
        setLoginIntent({ mode: 'code', notice: t('setup.reauth') });
        await logout(); // the shell's sign-out reset then opens Kirish with this intent
        return;
      }
      if (code === 'registration_complete') return void reload();
      if (code === 'age_restricted') {
        setLoginIntent({ mode: 'password', notice: t('age.restrictedNew') });
        await logout(); // the account was erased by the server
        return;
      }
      if (code === 'date_of_birth_required' || code === 'invalid_date_of_birth') return void setErrs({ dob: errorText(e) });
      if (['invalid_username', 'username_unavailable', 'username_already_set'].includes(code)) setErrs({ username: errorText(e) });
      else if (code === 'weak_password') setErrs({ password: errorText(e) });
      else setErrs({ form: errorText(e) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Screen>
      <H1>{t('setup.title')}</H1>
      <P muted>{t('setup.lead')}</P>
      <Card style={{ gap: 12 }}>
        <Field
          label={t('setup.username')}
          hint={`${t('setup.usernameRules')} ${t('setup.usernamePrivate')}`}
          value={username}
          onChangeText={setUsername}
          editable={!fixed}
          maxLength={30}
          {...AUTOFILL.username}
          error={errs.username}
          live={check && check !== 'unknown' && !errs.username ? t(CHECK_TEXT[check]) : undefined}
        />
        <Field
          label={t('pw.new')}
          hint={t('pw.rules')}
          value={password}
          onChangeText={setPassword}
          secureTextEntry={!show}
          {...AUTOFILL.newPassword}
          error={errs.password}
        />
        <Field
          label={t('pw.repeat')}
          value={password2}
          onChangeText={setPassword2}
          secureTextEntry={!show}
          {...AUTOFILL.newPassword}
          error={errs.repeat}
        />
        <ConsentCheck checked={show} onChange={setShow} label={t('login.pw.show')} />
        {askDob && <DobField value={dob} onChange={setDob} error={errs.dob} />}
        {errs.form && <ErrorText text={errs.form} />}
        <Row>
          <Button label={t('setup.submit')} busy={busy} onPress={() => void submit()} />
          <Button kind="ghost" label={t('account.logout')} onPress={() => void logout()} />
        </Row>
      </Card>
    </Screen>
  );
}

/** 18+: YYYY-MM-DD typed with the number keyboard (no extra date-picker dependency). */
function DobField({ value, onChange, error }: { value: string; onChange: (v: string) => void; error?: string }) {
  return (
    <Field
      label={t('age.dob')}
      hint={`${t('age.dobHint')} (YYYY-MM-DD)`}
      value={value}
      onChangeText={onChange}
      placeholder="1995-05-15"
      keyboardType="numbers-and-punctuation"
      autoComplete="birthdate-full"
      maxLength={10}
      error={error}
    />
  );
}

/** Accounts from before the age limit give their date of birth once (PUT /auth/date-of-birth). */
export function DobStepScreen() {
  const { reload, logout } = useAuth();
  const [dob, setDob] = useState('');
  const [err, setErr] = useState<string>();
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    if (dobProblem(dob) === 'age.invalid') return setErr(t('age.invalid'));
    setBusy(true);
    setErr(undefined);
    try {
      await api.put('/auth/date-of-birth', { date_of_birth: dob });
    } catch (e) {
      if (!(e instanceof ApiError && e.code === 'age_restricted')) setErr(errorText(e));
    } finally {
      setBusy(false);
    }
    await reload();
  };
  return (
    <Screen>
      <H1>{t('age.stepTitle')}</H1>
      <P muted>{t('age.stepLead')}</P>
      <Card style={{ gap: 12 }}>
        <DobField value={dob} onChange={setDob} error={err} />
        <Row>
          <Button label={t('setup.submit')} busy={busy} onPress={() => void submit()} />
          <Button kind="ghost" label={t('account.logout')} onPress={() => void logout()} />
        </Row>
      </Card>
    </Screen>
  );
}

/** Declared under 18: locked until an admin checks the ID; Help (support) and deletion stay open. */
export function AgeRestrictedScreen({ onHelp }: { onHelp: () => void }) {
  const { logout } = useAuth();
  return (
    <Screen>
      <H1>{t('age.restrictedTitle')}</H1>
      <P>{t('age.restrictedBody')}</P>
      <Row>
        <Button label={t('age.contactSupport')} onPress={onHelp} />
        <Button kind="ghost" label={t('account.logout')} onPress={() => void logout()} />
      </Row>
      <DeleteAccount before={null} />
    </Screen>
  );
}

/** Settings → Hisob: "Parolni almaştiriş" (PUT /auth/password); other devices are signed out, this one stays. */
export function ChangePassword({ user, onDone }: { user: User; onDone: (text: string) => void }) {
  const [open, setOpen] = useState(false);
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [repeat, setRepeat] = useState('');
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [errs, setErrs] = useState<{ current?: string; next?: string; repeat?: string; form?: string }>({});
  if (!user.has_password) return null;
  const close = () => {
    setOpen(false);
    setCurrent('');
    setNext('');
    setRepeat('');
    setErrs({});
  };
  const submit = async () => {
    const found: typeof errs = {};
    const problem = passwordProblem(next, user.phone_number);
    if (!current) found.current = t('pw.currentWrong');
    if (problem) found.next = t(problem);
    else if (next !== repeat) found.repeat = t('pw.mismatch');
    setErrs(found);
    if (Object.keys(found).length) return;
    setBusy(true);
    try {
      await api.put('/auth/password', { current_password: current, new_password: next });
      close();
      onDone(t('pwchange.done'));
    } catch (e) {
      const code = e instanceof ApiError ? e.code : '';
      if (code === 'invalid_credentials') setErrs({ current: t('pw.currentWrong') });
      else if (code === 'weak_password') setErrs({ next: errorText(e) });
      else setErrs({ form: errorText(e) });
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      {user.username ? <P muted>{t('pwchange.username', { name: user.username })}</P> : null}
      {!open ? (
        <Row>
          <Button kind="ghost" label={t('pwchange.title')} onPress={() => setOpen(true)} />
        </Row>
      ) : (
        <>
          <H2>{t('pwchange.title')}</H2>
          <P muted>{t('pwchange.note')}</P>
          <Field label={t('pw.current')} value={current} onChangeText={setCurrent} secureTextEntry={!show} {...AUTOFILL.currentPassword} error={errs.current} />
          <Field label={t('pw.new')} hint={t('pw.rules')} value={next} onChangeText={setNext} secureTextEntry={!show} {...AUTOFILL.newPassword} error={errs.next} />
          <Field label={t('pw.repeat')} value={repeat} onChangeText={setRepeat} secureTextEntry={!show} {...AUTOFILL.newPassword} error={errs.repeat} />
          <ConsentCheck checked={show} onChange={setShow} label={t('login.pw.show')} />
          {errs.form && <ErrorText text={errs.form} />}
          <Row>
            <Button label={t('pwchange.submit')} busy={busy} onPress={() => void submit()} />
            <Button kind="ghost" label={t('common.cancel')} disabled={busy} onPress={close} />
          </Row>
        </>
      )}
    </>
  );
}
