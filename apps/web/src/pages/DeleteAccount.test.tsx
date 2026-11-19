import { act, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

const get = vi.hoisted(() => vi.fn());
const post = vi.hoisted(() => vi.fn());
vi.mock('../api/client', async (orig) => {
  const real = await orig<typeof import('../api/client')>();
  return { ...real, api: { ...real.api, get, post } };
});
import { ToastProvider } from '../ui/feedback';
import { HOLD_MS } from '../ui/HoldToConfirm';
import { DeleteAccount } from './DeleteAccount';

const view = () =>
  render(
    <MemoryRouter>
      <ToastProvider>
        <DeleteAccount before={<button className="btn ghost">Çiqiş</button>} />
      </ToastProvider>
    </MemoryRouter>,
  );

describe('account deletion (owner, 2026-11-18: hold-to-confirm replaces the dialog)', () => {
  it('no dialog: sign-out stays plain, deletion is a red hold button with the consequences next to it', async () => {
    get.mockResolvedValue({ pending: false, window_days: 30, due_at: null });
    view();
    const hold = await screen.findByRole('button', { name: 'Hisobni öçiriş' });
    expect(hold).toHaveClass('hold');
    expect(screen.getByRole('button', { name: 'Çiqiş' })).not.toHaveClass('hold');
    expect(hold.closest('.danger-zone')).toHaveTextContent('30 kun');
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('a 1.5 s hold sends {confirm: true}; an early release sends nothing', async () => {
    get.mockResolvedValue({ pending: false, window_days: 30, due_at: null });
    post.mockResolvedValue({ pending: true, window_days: 30, due_at: '2026-12-15T00:00:00Z' });
    view();
    const hold = await screen.findByRole('button', { name: 'Hisobni öçiriş' });
    vi.useFakeTimers();
    try {
      fireEvent.pointerDown(hold);
      act(() => vi.advanceTimersByTime(800));
      fireEvent.pointerUp(hold);
      expect(post).not.toHaveBeenCalled();
      act(() => vi.advanceTimersByTime(100));
      fireEvent.pointerDown(hold);
      await act(async () => vi.advanceTimersByTime(HOLD_MS));
    } finally {
      vi.useRealTimers();
    }
    expect(post).toHaveBeenCalledWith('/account/deletion', { confirm: true });
    await screen.findByRole('button', { name: 'Sörovni bekor qiliş' }); // pending state unchanged
  });
});
