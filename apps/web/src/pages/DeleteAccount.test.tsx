import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

const get = vi.hoisted(() => vi.fn());
const post = vi.hoisted(() => vi.fn());
vi.mock('../api/client', async (orig) => {
  const real = await orig<typeof import('../api/client')>();
  return { ...real, api: { ...real.api, get, post } };
});
import { ToastProvider } from '../ui/feedback';
import { DeleteAccount } from './DeleteAccount';

const view = () =>
  render(
    <MemoryRouter>
      <ToastProvider>
        <DeleteAccount before={<button className="btn ghost">Çiqiş</button>} />
      </ToastProvider>
    </MemoryRouter>,
  );

describe('account deletion (owner, 2026-11-15)', () => {
  it('the delete button looks like sign out; the question opens in a modal dialog with Ha / Yöq', async () => {
    get.mockResolvedValue({ pending: false, window_days: 30, due_at: null });
    view();
    const trigger = await screen.findByRole('button', { name: 'Hisobni öçiriş' });
    expect(trigger.className).toBe(screen.getByRole('button', { name: 'Çiqiş' }).className);
    await userEvent.click(trigger);
    const dialog = screen.getByRole('dialog', { name: 'Hisobni öçirmoqçimisiz?' });
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    const yes = screen.getByRole('button', { name: 'Ha, öçiriş' });
    expect(yes).toBeDisabled(); // the "I understand" box comes first
    await userEvent.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    expect(trigger).toHaveFocus();
  });

  it('confirming sends {confirm: true}; "Yöq" sends nothing', async () => {
    get.mockResolvedValue({ pending: false, window_days: 30, due_at: null });
    post.mockResolvedValue({ pending: true, window_days: 30, due_at: '2026-12-15T00:00:00Z' });
    view();
    await userEvent.click(await screen.findByRole('button', { name: 'Hisobni öçiriş' }));
    await userEvent.click(screen.getByRole('button', { name: 'Yöq' }));
    expect(post).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole('button', { name: 'Hisobni öçiriş' }));
    await userEvent.click(screen.getByRole('checkbox'));
    await userEvent.click(screen.getByRole('button', { name: 'Ha, öçiriş' }));
    expect(post).toHaveBeenCalledWith('/account/deletion', { confirm: true });
    await screen.findByRole('button', { name: 'Sörovni bekor qiliş' }); // pending state unchanged
  });
});
