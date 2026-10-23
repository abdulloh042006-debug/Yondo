import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

const auth = vi.hoisted(() => ({ value: {} as unknown }));
const post = vi.hoisted(() => vi.fn());
vi.mock('../auth/AuthContext', () => ({ useAuth: () => auth.value }));
vi.mock('../api/client', async (orig) => {
  const real = await orig<typeof import('../api/client')>();
  return { ...real, api: { ...real.api, post } };
});
import { ToastProvider } from '../ui/feedback';
import { ReportDialog } from '../ui/ReportDialog';
import { Help } from './Help';

describe('Help & safety', () => {
  it('signed out: emergency number, FAQ and a sign-in prompt, no private sections', () => {
    auth.value = { state: { status: 'anon' }, user: null };
    render(
      <MemoryRouter>
        <Help />
      </MemoryRouter>,
    );
    expect(screen.getByRole('link', { name: /112/ })).toHaveAttribute('href', 'tel:112');
    expect(screen.getByText(/özi çaqirmaydi/)).toBeInTheDocument(); // never claims anyone is notified
    expect(screen.getByText('Yondo nima?')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Işonçli kontaktlar' })).toBeNull();
    expect(screen.getByText(/hisobingizga kiring/)).toBeInTheDocument();
  });

  it('report dialog sends only booking_id (the server derives who is reported)', async () => {
    post.mockResolvedValue({});
    const onClose = vi.fn();
    render(
      <ToastProvider>
        <ReportDialog bookingId="b-1" aboutCompanion onClose={onClose} />
      </ToastProvider>,
    );
    await userEvent.click(screen.getByRole('button', { name: 'Şikoyatni yuboriş' }));
    expect(post).not.toHaveBeenCalled(); // description required
    await userEvent.selectOptions(screen.getByLabelText('Sabab'), 'no_show');
    await userEvent.type(screen.getByLabelText('Nima bölganini yozing'), '  Kelmadi  ');
    await userEvent.click(screen.getByRole('button', { name: 'Şikoyatni yuboriş' }));
    expect(post).toHaveBeenCalledWith('/safety/reports', { booking_id: 'b-1', category: 'no_show', description: 'Kelmadi' });
    expect(onClose).toHaveBeenCalled();
  });
});
