import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { ApiError } from '../api/client';

const get = vi.hoisted(() => vi.fn());
const post = vi.hoisted(() => vi.fn());
vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ user: { id: 'cust' } }) }));
vi.mock('../api/client', async (orig) => {
  const real = await orig<typeof import('../api/client')>();
  return { ...real, api: { ...real.api, get, post } };
});
import { ToastProvider } from '../ui/feedback';
import { BookingDetail } from './BookingDetail';

const booking = {
  id: 'b1', customer_id: 'cust', profile_id: 'p1', service_id: 's1', service_code: 'walking', service_description: '',
  status: 'accepted', starts_at: '2027-01-10T06:00:00Z', ends_at: '2027-01-10T07:00:00Z', timezone: 'Asia/Tashkent',
  duration_minutes: 60, meeting_place: 'Park', price_minor: 1500000, currency: 'UZS', created_at: '2026-10-23T00:00:00Z',
  customer_contract_accepted_at: null, companion_contract_accepted_at: null,
};

describe('BookingDetail', () => {
  it('payment: 503 is shown as "unavailable" (never declined), retries reuse one Idempotency-Key', async () => {
    get.mockImplementation((path: string) => Promise.resolve(path === '/bookings/b1' ? booking : []));
    post.mockRejectedValue(new ApiError(503, 'payment_provider_unavailable'));
    render(
      <MemoryRouter initialEntries={['/bookings/b1']}>
        <ToastProvider>
          <Routes>
            <Route path="/bookings/:id" element={<BookingDetail />} />
          </Routes>
        </ToastProvider>
      </MemoryRouter>,
    );
    const pay = await screen.findByRole('button', { name: 'Tölovga ötiş' });
    await userEvent.click(pay);
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Tölov xizmati hozirça ulanmagan.');
    expect(alert).toHaveClass('banner');
    await userEvent.click(pay);
    const keys = post.mock.calls.map((c) => (c[2] as { headers: Record<string, string> }).headers['Idempotency-Key']);
    expect(keys).toHaveLength(2);
    expect(keys[0]).toBe(keys[1]);
    expect(screen.getByText('Uçraşuv bosqiçi bron tasdiqlangaç (tölovdan keyin) oçiladi.')).toBeInTheDocument();
    expect(screen.getByText('Şarhni uçraşuv yakunlangaç qoldirasiz.')).toBeInTheDocument();
  });
});
