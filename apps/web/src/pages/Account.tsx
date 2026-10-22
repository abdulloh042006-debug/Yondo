import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { api, ApiError, type Schemas } from '../api/client';
import { useAuth, type User } from '../auth/AuthContext';
import { prettyPhone } from '../lib/format';
import { useToast } from '../ui/feedback';
import { Field } from '../ui/form';
import { Reveal } from '../ui/motion';

type Role = Schemas['UserRoleType'];

export function Account() {
  const { user } = useAuth();
  if (!user) return null;
  // Remount when the server-side profile changes so the form always starts from saved values.
  return <AccountView key={`${user.age}|${user.gender}|${user.city}`} user={user} />;
}

function AccountView({ user }: { user: User }) {
  const { reload, logout } = useAuth();
  const toast = useToast();
  const [age, setAge] = useState(user.age?.toString() ?? '');
  const [gender, setGender] = useState(user.gender ?? '');
  const [city, setCity] = useState(user.city ?? '');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<ApiError>();
  const [rolesBusy, setRolesBusy] = useState(false);

  const ageNum = age.trim() === '' ? null : Number(age);
  const ageError = ageNum !== null && (!Number.isInteger(ageNum) || ageNum < 18 || ageNum > 120) ? 'Yosh 18 dan 120 gacha bo‘lishi kerak.' : err?.fields.age;

  const save = async (e: FormEvent) => {
    e.preventDefault();
    if (ageError) return;
    setBusy(true);
    setErr(undefined);
    try {
      await api.put('/auth/profile', { age: ageNum, gender: gender.trim() || null, city: city.trim() || null });
      await reload();
      toast.push('ok', 'Profil saqlandi.');
    } catch (error) {
      setErr(error instanceof ApiError ? error : new ApiError(0, 'network_error'));
    } finally {
      setBusy(false);
    }
  };

  const toggleRole = async (role: 'customer' | 'companion') => {
    // The server replaces the whole non-admin role set, so we resend every other role we know of.
    const current = user.roles.filter((r) => r !== 'admin');
    const next: Role[] = current.includes(role) ? current.filter((r) => r !== role) : [...current, role];
    if (next.length === 0) {
      toast.push('bad', 'Kamida bitta rol tanlangan bo‘lishi kerak.');
      return;
    }
    setRolesBusy(true);
    try {
      await api.put('/auth/roles', { roles: next });
      await reload();
      toast.push('ok', 'Rollar yangilandi.');
    } catch (error) {
      toast.push('bad', error instanceof ApiError ? error.message : 'Amal bajarilmadi.');
    } finally {
      setRolesBusy(false);
    }
  };

  return (
    <div className="stack" style={{ gap: 20, maxWidth: 760, margin: '0 auto', width: '100%' }}>
      <h1>Hisobim</h1>
      <Reveal>
        <div className="glass pad stack">
          <h2>Kirish ma’lumotlari</h2>
          <dl className="kv">
            <dt>Telefon</dt><dd>{prettyPhone(user.phone_number)}</dd>
            <dt>Rollar</dt><dd>{user.roles.join(', ') || '—'}</dd>
          </dl>
          {!user.roles.includes('admin') && (
            <p className="hint">
              Hisob holati (tasdiqlangan/faol) administrator tomonidan belgilanadi; hamroh profili ommaga chiqishi uchun hisob
              faol bo‘lishi shart.
            </p>
          )}
        </div>
      </Reveal>
      <Reveal delay={0.05}>
        <form className="glass pad stack" onSubmit={save} noValidate>
          <h2>Shaxsiy ma’lumotlar</h2>
          <div className="bento">
            <Field label="Yosh" inputMode="numeric" value={age} onChange={(e) => setAge(e.target.value)} error={ageError} />
            <Field label="Jins" value={gender} maxLength={64} onChange={(e) => setGender(e.target.value)} error={err?.fields.gender} />
            <Field label="Shahar" value={city} maxLength={128} onChange={(e) => setCity(e.target.value)} error={err?.fields.city} />
          </div>
          {err && !Object.keys(err.fields).length && <p className="err" role="alert">{err.message}</p>}
          <div><button className="btn" disabled={busy || !!ageError}>{busy && <span className="spinner" aria-hidden="true" />}Saqlash</button></div>
        </form>
      </Reveal>
      <Reveal delay={0.1}>
        <div className="glass pad stack">
          <h2>Men kimman</h2>
          <p className="muted">Mijoz sifatida hamroh topasiz va bron qilasiz; hamroh sifatida o‘z profilingiz va xizmatlaringizni yuritasiz.</p>
          <div className="row">
            {(['customer', 'companion'] as const).map((r) => (
              <button key={r} className="chip" aria-pressed={user.roles.includes(r)} disabled={rolesBusy} onClick={() => void toggleRole(r)}>
                {r === 'customer' ? 'Mijoz' : 'Hamroh'}
              </button>
            ))}
          </div>
          {user.roles.includes('companion') && <Link className="btn" to="/studio" style={{ width: 'fit-content' }}>Hamroh studiyasi</Link>}
        </div>
      </Reveal>
      <div><button className="btn ghost" onClick={() => void logout()}>Chiqish</button></div>
    </div>
  );
}
