import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

const auth = vi.hoisted(() => ({ value: {} as unknown }));
const get = vi.hoisted(() => vi.fn());
const post = vi.hoisted(() => vi.fn());
vi.mock('../auth/AuthContext', () => ({ useAuth: () => auth.value }));
vi.mock('../api/client', async (orig) => {
  const real = await orig<typeof import('../api/client')>();
  return { ...real, api: { ...real.api, get, post } };
});
import { ToastProvider } from './feedback';
import { SosButton } from './Sos';

const mount = () =>
  render(
    <MemoryRouter>
      <ToastProvider>
        <SosButton />
      </ToastProvider>
    </MemoryRouter>,
  );

describe('SOS', () => {
  it('opening does nothing by itself; offers 112 and asks for location only on tap', async () => {
    auth.value = { user: null };
    const getCurrentPosition = vi.fn((ok: PositionCallback) =>
      ok({ coords: { latitude: 41.311081, longitude: 69.240562, accuracy: 18 } } as GeolocationPosition),
    );
    Object.defineProperty(navigator, 'geolocation', { value: { getCurrentPosition }, configurable: true });
    mount();
    await userEvent.click(screen.getByRole('button', { name: /SOS: favqulodda/ }));
    expect(post).not.toHaveBeenCalled();
    expect(getCurrentPosition).not.toHaveBeenCalled();
    expect(screen.getByRole('link', { name: '112 ga qönğiroq qiliş' })).toHaveAttribute('href', 'tel:112');
    expect(screen.getByText(/heç kimni avtomatik çaqirmaydi/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Joylaşuvimni xabarga qöşiş' }));
    expect(screen.getByText('Joylaşuv qöşildi: 41.31108, 69.24056 (±18 m)')).toBeInTheDocument();
  });

  it('signed in: trusted contacts via the phone’s own SMS app; moderator signal only for an active meeting', async () => {
    auth.value = { user: { id: 'u1' } };
    get.mockImplementation((path: string) =>
      Promise.resolve(
        path === '/safety/trusted-contacts'
          ? [{ id: 'c1', name: 'Ona', phone_number: '+998901112233' }]
          : [{ id: 'b1', status: 'active', service_code: 'walking' }, { id: 'b2', status: 'pending', service_code: 'coffee' }],
      ),
    );
    post.mockResolvedValue({ id: 'a1', emergency_service_contacted: false });
    mount();
    await userEvent.click(screen.getByRole('button', { name: /SOS: favqulodda/ }));
    const sms = await screen.findByRole('link', { name: 'Ona: SMS yoziş' });
    expect(sms.getAttribute('href')).toBe(`sms:+998901112233?&body=${encodeURIComponent('Menga yordam kerak (Yondo SOS).')}`);
    expect(screen.getByRole('link', { name: 'Ona: qönğiroq qiliş' })).toHaveAttribute('href', 'tel:+998901112233');
    const signal = await screen.findByRole('button', { name: /signal yuboriş/ });
    expect(screen.getAllByRole('button', { name: /signal yuboriş/ })).toHaveLength(1); // only the active booking
    await userEvent.click(signal);
    expect(post).toHaveBeenCalledWith('/safety/bookings/b1/sos', undefined, { query: { confirmed: true } });
    expect(await screen.findByText(/heç kim avtomatik xabardor qilinmadi/)).toBeInTheDocument();
  });
});
