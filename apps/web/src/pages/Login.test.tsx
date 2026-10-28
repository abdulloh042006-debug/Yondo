import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../api/client';
import { t } from '../i18n';

const auth = vi.hoisted(() => ({ requestCode: vi.fn(), verify: vi.fn() }));
vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({ state: { status: 'anon' }, requestCode: auth.requestCode, verify: auth.verify }),
}));
import { Login } from './Login';

const base = { message: 'x', expires_in_seconds: 300, resend_after_seconds: 3 };
const mount = () =>
  render(
    <MemoryRouter>
      <Login />
    </MemoryRouter>,
  );

/** Phone step: fill the number, tick the consent box and press "send code". */
async function sendCode() {
  fireEvent.change(screen.getByLabelText(t('login.phone')), { target: { value: '+998901234567' } });
  fireEvent.click(document.querySelector('.consent input') as HTMLInputElement);
  await act(async () => {
    fireEvent.click(screen.getByRole('button', { name: t('login.sendCode') }));
  });
}

const codeInput = () => screen.getByLabelText(t('login.code')) as HTMLInputElement;

beforeEach(() => {
  auth.requestCode.mockReset();
  auth.verify.mockReset();
});
afterEach(() => vi.useRealTimers());

describe('Login: dev / demo path (no delivery_channel)', () => {
  it('keeps the generic sentence and the on-screen development code', async () => {
    auth.requestCode.mockResolvedValue({ ...base, development_otp: '123456' });
    mount();
    await sendCode();
    const dev = document.querySelector('b.mono');
    expect(dev?.textContent).toBe('123456');
    expect(screen.getByText(/raqamiga kod yuborildi/)).toBeInTheDocument();
    expect(screen.queryByText(t('login.tg.title'))).toBeNull();
    expect(screen.queryByText(t('login.tg.noTelegram'))).toBeNull();
  });

  it('treats an unknown or sms channel like the generic layout (never invents Telegram text)', async () => {
    auth.requestCode.mockResolvedValue({ ...base, delivery_channel: 'sms' });
    mount();
    await sendCode();
    expect(screen.getByText(/raqamiga kod yuborildi/)).toBeInTheDocument();
    expect(screen.queryByText(t('login.tg.title'))).toBeNull();
  });
});

describe('Login: Telegram channel', () => {
  beforeEach(() => auth.requestCode.mockResolvedValue({ ...base, delivery_channel: 'telegram' }));

  it('shows the Telegram instructions instead of a code, with a numeric one-time-code field', async () => {
    mount();
    await sendCode();
    expect(screen.getByRole('heading', { name: 'Kod Telegramʼga yuborildi' })).toBeInTheDocument();
    expect(document.querySelector('b.mono')).toBeNull();
    expect(screen.getByText(t('login.tg.open'))).toBeInTheDocument();
    expect(screen.getByText('Kod 5 daqiqa amal qiladi.')).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/SMS/);
    const input = codeInput();
    expect(input).toHaveAttribute('autocomplete', 'one-time-code');
    expect(input).toHaveAttribute('inputmode', 'numeric');
    expect(input).toHaveFocus();
  });

  it('keeps only digits (max 6) and enables submit at exactly 6', async () => {
    mount();
    await sendCode();
    const submit = screen.getByRole('button', { name: t('login.submit') });
    fireEvent.change(codeInput(), { target: { value: '12 34a5' } });
    expect(codeInput().value).toBe('12345');
    expect(submit).toBeDisabled();
    fireEvent.change(codeInput(), { target: { value: '123 456 789' } });
    expect(codeInput().value).toBe('123456');
    expect(submit).toBeEnabled();
  });

  it('"Telegramim yöq" discloses plain words and never promises SMS', async () => {
    mount();
    await sendCode();
    const toggle = screen.getByRole('button', { name: t('login.tg.noTelegram') });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    const body = screen.getByText(t('login.tg.noTelegramBody'));
    expect(toggle.getAttribute('aria-controls')).toBe(body.id);
    expect(body.textContent).not.toMatch(/SMS/);
    fireEvent.click(toggle);
    expect(screen.queryByText(t('login.tg.noTelegramBody'))).toBeNull();
  });

  it('counts down, then resends and announces it in the status region', async () => {
    vi.useFakeTimers();
    mount();
    await sendCode();
    const resend = screen.getByRole('button', { name: t('login.resendIn', { n: 3 }) });
    expect(resend).toBeDisabled();
    for (let i = 0; i < 3; i++) {
      // One act per second: each tick re-renders and only then schedules the next timeout.
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000);
      });
    }
    const ready = screen.getByRole('button', { name: t('login.resend') });
    expect(ready).toBeEnabled();
    await act(async () => {
      fireEvent.click(ready);
    });
    expect(auth.requestCode).toHaveBeenCalledTimes(2);
    expect(screen.getByRole('status')).toHaveTextContent(t('login.resent'));
    expect(screen.getByRole('button', { name: t('login.resendIn', { n: 3 }) })).toBeDisabled();
  });

  it('otp_expired clears the code and allows an immediate resend', async () => {
    auth.verify.mockRejectedValue(new ApiError(401, 'otp_expired'));
    mount();
    await sendCode();
    fireEvent.change(codeInput(), { target: { value: '123456' } });
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: t('login.submit') }));
    });
    await waitFor(() => expect(screen.getByText(t('err.otp_expired'))).toBeInTheDocument());
    expect(codeInput().value).toBe('');
    expect(screen.getByRole('button', { name: t('login.resend') })).toBeEnabled();
  });
});

describe('Login: delivery errors are chosen by code, never by status', () => {
  it('otp_channel_unavailable is shown under the phone field and the form stays usable', async () => {
    // Deliberately a different status than the backend's 422: only the code may matter.
    auth.requestCode.mockRejectedValue(new ApiError(418, 'otp_channel_unavailable'));
    mount();
    await sendCode();
    const phone = screen.getByLabelText(t('login.phone'));
    expect(phone).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByRole('alert')).toHaveTextContent(t('err.otp_channel_unavailable'));
    expect(screen.getByText(/Telegram hisobi topilmadi/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: t('login.sendCode') })).toBeEnabled();
  });

  it.each([
    [502, 'otp_delivery_failed', 'Kodni yuborib bölmadi'],
    [503, 'otp_delivery_unavailable', 'Kod yuboriş xizmati hozirça ulanmagan'],
  ])('%s %s stays on the phone step with neutral wording', async (status, code, text) => {
    auth.requestCode.mockRejectedValue(new ApiError(status, code));
    mount();
    await sendCode();
    expect(screen.getByRole('alert')).toHaveTextContent(text);
    expect(screen.getByLabelText(t('login.phone'))).not.toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByRole('button', { name: t('login.sendCode') })).toBeEnabled();
    expect(document.body.textContent).not.toMatch(/SMS|rad etil/i);
  });
});
