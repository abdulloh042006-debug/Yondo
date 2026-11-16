import { act, fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../api/client';
import type { User } from '../auth/AuthContext';
import { t } from '../i18n';

const put = vi.hoisted(() => vi.fn());
vi.mock('../api/client', async (orig) => {
  const real = await orig<typeof import('../api/client')>();
  return { ...real, api: { ...real.api, put } };
});
import { ToastProvider } from '../ui/feedback';
import { ChangePassword } from './ChangePassword';

const user = { id: 'u1', phone_number: '+998901110003', username: 'aziz.k', has_password: true } as unknown as User;
const mount = (u = user) => render(<ToastProvider><ChangePassword user={u} /></ToastProvider>);
const fill = (cur: string, next: string, rep = next) => {
  fireEvent.change(screen.getByLabelText(t('pw.current')), { target: { value: cur } });
  fireEvent.change(screen.getByLabelText(t('pw.new')), { target: { value: next } });
  fireEvent.change(screen.getByLabelText(t('pw.repeat')), { target: { value: rep } });
};
const save = () => act(async () => fireEvent.click(screen.getByRole('button', { name: t('pwchange.submit') })));

// Block body: an arrow that returns the mock would make vitest call it as a teardown.
beforeEach(() => {
  put.mockReset();
});

describe('Settings → Hisob → Parolni almaştiriş', () => {
  it('hidden without a password', () => {
    mount({ ...user, has_password: false } as User);
    expect(screen.queryByRole('button', { name: t('pwchange.title') })).toBeNull();
  });

  it('explains other devices are signed out, sends current + new, confirms', async () => {
    put.mockResolvedValue(undefined);
    mount();
    expect(screen.getByText(t('pwchange.username', { name: 'aziz.k' }))).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: t('pwchange.title') }));
    expect(screen.getByText(t('pwchange.note'))).toBeInTheDocument();
    expect(screen.getByLabelText(t('pw.current'))).toHaveAttribute('autocomplete', 'current-password');
    fill('old password', 'new password!', 'mismatch');
    await save();
    expect(put).not.toHaveBeenCalled();
    expect(screen.getByLabelText(t('pw.repeat'))).toHaveAccessibleDescription(t('pw.mismatch'));
    fill('old password', 'new password!');
    await save();
    expect(put).toHaveBeenCalledWith('/auth/password', { current_password: 'old password', new_password: 'new password!' });
    expect(await screen.findByText(t('pwchange.done'))).toBeInTheDocument();
  });

  it('a wrong current password is shown on that field', async () => {
    put.mockRejectedValue(new ApiError(401, 'invalid_credentials'));
    mount();
    fireEvent.click(screen.getByRole('button', { name: t('pwchange.title') }));
    fill('wrong', 'new password!');
    await save();
    expect(screen.getByLabelText(t('pw.current'))).toHaveAccessibleDescription(t('pw.currentWrong'));
  });
});
