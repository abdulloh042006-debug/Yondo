import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it } from 'vitest';
import { en } from './en';
import { LanguagePicker } from './LanguagePicker';
import { LanguageSwitch } from './LanguageSwitch';
import { defaultUzAlphabet, getLang, LANGS, setLang, setUzAlphabet, t, toUz1995, useLang, type Key } from './index';
import { ru } from './ru';
import { uz } from './uz';
import { formatInstant, formatMoney } from '../lib/format';
import { messageFor } from '../lib/messages';
import { serviceLabel, BOOKING_STATUS } from '../lib/labels';

afterEach(async () => {
  await setLang('uz');
  localStorage.clear();
});

const params = (s: string) =>
  [...new Set([...s.matchAll(/\{(\w+)\}/g), ...s.matchAll(/\{(\w+), plural,/g)].map((m) => m[1]))].sort().join(',');
const keys = Object.keys(uz) as Key[];
const MAY_BE_EMPTY = new Set<Key>(['login.codeSentBefore']);

describe('dictionaries', () => {
  it('ru and en define exactly the keys of uz', () => {
    expect(Object.keys(ru).sort()).toEqual([...keys].sort());
    expect(Object.keys(en).sort()).toEqual([...keys].sort());
  });
  it('have no empty translations (except deliberate prefixes)', () => {
    for (const [name, dict] of [['uz', uz], ['ru', ru], ['en', en]] as const) {
      for (const k of keys) {
        if (MAY_BE_EMPTY.has(k) && name === 'uz') continue;
        expect(dict[k]?.trim(), `${name}:${k}`).toBeTruthy();
      }
    }
  });
  it('use the same {placeholders} in every language', () => {
    for (const k of keys) {
      expect(params(ru[k]), `ru:${k}`).toBe(params(uz[k]));
      expect(params(en[k]), `en:${k}`).toBe(params(uz[k]));
    }
  });
  it('ru/en are really translated (not copies of the Uzbek text)', () => {
    const SAME_OK = new Set<Key>(['nav.admin', 'admin.audit.safety_sos', 'service.shopping', 'role.admin']);
    const copies = keys.filter((k) => !SAME_OK.has(k) && uz[k].length > 6 && (ru[k] === uz[k] || en[k] === uz[k]));
    expect(copies).toEqual([]);
  });
});

describe('t()', () => {
  it('interpolates params and picks plural forms per language', async () => {
    expect(t('login.resendIn', { n: 7 })).toBe('Yangi kod: 7 s');
    await setLang('ru');
    expect(t('profile.reviews', { count: 1 })).toBe('1 отзыв');
    expect(t('profile.reviews', { count: 3 })).toBe('3 отзыва');
    expect(t('profile.reviews', { count: 5 })).toBe('5 отзывов');
    expect(t('profile.reviews', { count: 21 })).toBe('21 отзыв');
    await setLang('en');
    expect(t('profile.reviews', { count: 1 })).toBe('1 review');
    expect(t('profile.reviews', { count: 2 })).toBe('2 reviews');
    await setLang('uz');
    expect(t('profile.reviews', { count: 3 })).toBe('3 ta şarh');
  });
});

describe('language switching', () => {
  it('persists, updates <html lang>/title and translates helper modules', async () => {
    await setLang('ru');
    expect(getLang()).toBe('ru');
    expect(localStorage.getItem('yondo.lang')).toBe('ru');
    expect(document.documentElement.lang).toBe('ru');
    expect(document.title).toBe(ru['app.title']);
    expect(serviceLabel('coffee')).toBe('Кофе');
    expect(BOOKING_STATUS.pending.label).toBe('Ожидает ответа');
    expect(messageFor('invalid_otp', 422)).toBe('Неверный код. Попробуйте ещё раз.');
    expect(messageFor('nope', 503)).toBe(ru['errStatus.503']);
    await setLang('en');
    expect(messageFor('invalid_otp', 422)).toBe('Incorrect code. Please try again.');
    expect(messageFor(undefined, 500)).toBe(en['errStatus.5xx']);
  });
  it('formats money and dates per language', async () => {
    expect(formatMoney(15000000, 'UZS')).toBe('150 000 söm');
    expect(formatMoney(150050, 'UZS')).toBe('1 500.50 söm');
    await setLang('ru');
    expect(formatMoney(15000000, 'UZS')).toBe('150 000 сум');
    expect(formatMoney(150050, 'UZS')).toBe('1 500,50 сум');
    await setLang('en');
    expect(formatMoney(15000000, 'UZS')).toBe('150 000 UZS');
    expect(formatInstant('2026-10-24T09:30:00Z')).toMatch(/24/);
    expect(formatInstant(null)).toBe('—');
  });
  it('LanguagePicker switches the whole tree and keeps focus on the chosen language', async () => {
    const Probe = () => {
      useLang(); // like App: re-renders in place, no remount
      return <p data-testid="probe">{t('nav.login')}</p>;
    };
    render(
      <>
        <Probe />
        <LanguagePicker />
      </>,
    );
    expect(screen.getByTestId('probe')).toHaveTextContent('Kiriş');
    await userEvent.click(screen.getByRole('button', { name: /Русский/ }));
    expect(screen.getByTestId('probe')).toHaveTextContent('Вход');
    const ruBtn = screen.getByRole('button', { name: /Русский/ });
    expect(ruBtn).toHaveAttribute('aria-pressed', 'true');
    expect(ruBtn).toHaveFocus();
    await userEvent.click(screen.getByRole('button', { name: /English/ }));
    expect(screen.getByTestId('probe')).toHaveTextContent('Sign in');
    expect(document.documentElement.lang).toBe('en');
  });
  it('header LanguageSwitch re-renders in place: typed input survives, labels follow', async () => {
    const Form = () => {
      useLang();
      return (
        <label>
          {t('nav.login')}
          <input />
        </label>
      );
    };
    render(
      <>
        <LanguageSwitch />
        <Form />
      </>,
    );
    await userEvent.type(screen.getByRole('textbox'), '+998901');
    await userEvent.click(screen.getByRole('button', { name: /^RU/ }));
    expect(screen.getByLabelText('Вход')).toHaveValue('+998901');
    expect(screen.getByRole('button', { name: /^RU/ })).toHaveAttribute('aria-pressed', 'true');
    await setLang('uz');
  });
  it('Uzbek alphabets: 1995 text is derived from the 2026 source; default follows the law date', async () => {
    expect(toUz1995('Toşkent, özgaradi, ğalaba, Çiqiş, ŞAHAR, maʼlumot')).toBe('Toshkent, o‘zgaradi, g‘alaba, Chiqish, SHAHAR, ma’lumot');
    expect(defaultUzAlphabet(Date.parse('2026-10-23T12:00:00+05:00'))).toBe('1995');
    expect(defaultUzAlphabet(Date.parse('2027-04-21T23:59:00+05:00'))).toBe('1995');
    expect(defaultUzAlphabet(Date.parse('2027-04-22T00:00:00+05:00'))).toBe('2026');
    await setLang('uz');
    setUzAlphabet('1995');
    expect(t('nav.login')).toBe('Kirish');
    expect(t('profile.reviews', { count: 3 })).toBe('3 ta sharh');
    expect(LANGS[0].label).toBe('O‘zbekcha');
    setUzAlphabet('2026');
    expect(t('nav.login')).toBe('Kiriş');
    expect(LANGS[0].label).toBe('Özbekça');
  });
});
