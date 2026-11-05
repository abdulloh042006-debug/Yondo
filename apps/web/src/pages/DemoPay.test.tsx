import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

const get = vi.hoisted(() => vi.fn());
const post = vi.hoisted(() => vi.fn());
vi.mock('../api/client', async (orig) => {
  const real = await orig<typeof import('../api/client')>();
  return { ...real, api: { ...real.api, get, post } };
});
import { ApiError } from '../api/client';
import { ToastProvider } from '../ui/feedback';
import { DemoPay } from './DemoPay';

const mount = () =>
  render(
    <MemoryRouter initialEntries={['/demo-pay/demo-abc']}>
      <ToastProvider>
        <Routes>
          <Route path="/demo-pay/:reference" element={<DemoPay />} />
          <Route path="/bookings/:id" element={<p>booking page</p>} />
        </Routes>
      </ToastProvider>
    </MemoryRouter>,
  );

describe('DEMO payment page', () => {
  it('says no money moves; confirming calls the demo provider and returns to the booking', async () => {
    get.mockResolvedValue({ booking_id: 'b1', amount_minor: 15000000, currency: 'UZS', status: 'pending' });
    post.mockResolvedValue({ booking_id: 'b1', amount_minor: 15000000, currency: 'UZS', status: 'succeeded' });
    mount();
    expect(await screen.findByRole('heading', { name: 'Sinov tölov sahifasi' })).toBeInTheDocument();
    expect(screen.getByText(/Hech qanday pul yeçilmaydi/)).toBeInTheDocument();
    expect(screen.getByText('Summa: 150 000 söm')).toBeInTheDocument();
    expect(get).toHaveBeenCalledWith('/demo-pay/demo-abc', expect.anything());
    await userEvent.click(screen.getByRole('button', { name: 'Tölovni tasdiqlaş (DEMO)' }));
    expect(post).toHaveBeenCalledWith('/demo-pay/demo-abc/succeed');
    expect(await screen.findByText('booking page')).toBeInTheDocument();
  });

  it('rejecting sends the fail outcome', async () => {
    get.mockResolvedValue({ booking_id: 'b1', amount_minor: 100, currency: 'UZS', status: 'pending' });
    post.mockResolvedValue({ booking_id: 'b1', amount_minor: 100, currency: 'UZS', status: 'failed' });
    mount();
    await userEvent.click(await screen.findByRole('button', { name: 'Rad etiş (DEMO)' }));
    expect(post).toHaveBeenCalledWith('/demo-pay/demo-abc/fail');
  });

  it('a server without the demo provider (or someone else’s payment) answers 404: explained, no buttons', async () => {
    get.mockRejectedValue(new ApiError(404, 'http_404'));
    mount();
    expect(await screen.findByText(/yoqilmagan yoki sizga tegişli emas/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /DEMO/ })).toBeNull();
  });
});
