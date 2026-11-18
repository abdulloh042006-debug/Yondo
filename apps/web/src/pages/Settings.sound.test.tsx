import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ user: null, state: { status: 'anon' }, reload: vi.fn(), logout: vi.fn() }) }));
const play = vi.hoisted(() => vi.fn());
vi.mock('../lib/notifySound', async (orig) => ({ ...(await orig<typeof import('../lib/notifySound')>()), playNotifySound: play }));
import { ToastProvider } from '../ui/feedback';
import { Settings } from './Settings';

beforeEach(() => {
  localStorage.removeItem('yondo.notifySound');
  play.mockReset();
});

const renderIt = () =>
  render(
    <MemoryRouter>
      <ToastProvider>
        <Settings />
      </ToastProvider>
    </MemoryRouter>,
  );

describe('Settings: notification sound', () => {
  it('switch is ON by default, toggles and persists on this device', async () => {
    renderIt();
    const sw = screen.getByRole('switch', { name: 'Bildiriş ovozi' });
    expect(sw).toHaveAttribute('aria-checked', 'true');
    await userEvent.click(sw);
    expect(sw).toHaveAttribute('aria-checked', 'false');
    expect(localStorage.getItem('yondo.notifySound')).toBe('off');
    await userEvent.click(sw);
    expect(sw).toHaveAttribute('aria-checked', 'true');
  });

  it('test button plays with force, even when the switch is off', async () => {
    localStorage.setItem('yondo.notifySound', 'off');
    renderIt();
    await userEvent.click(screen.getByRole('button', { name: 'Ovozni sinab köriş' }));
    expect(play).toHaveBeenCalledWith({ force: true });
  });
});
