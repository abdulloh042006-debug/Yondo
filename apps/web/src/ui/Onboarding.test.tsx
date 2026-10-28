import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const auth = vi.hoisted(() => ({ value: {} as unknown }));
vi.mock('../auth/AuthContext', () => ({ useAuth: () => auth.value }));
import { setLang } from '../i18n';
import { firstRun } from '../lib/firstRun';
import { Help } from '../pages/Help';
import { Settings } from '../pages/Settings';
import { GuideButton, OnboardingHost } from './Onboarding';
import { ToastProvider } from './feedback';

const anon = () => (auth.value = { state: { status: 'anon' }, user: null });
const signedIn = (...roles: string[]) => (auth.value = { state: { status: 'authed' }, user: { id: 'u1', roles } });
const host = (path: string) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <OnboardingHost />
      <main>page</main>
    </MemoryRouter>,
  );
const dialog = () => screen.queryByRole('dialog', { name: 'Yondo qanday işlaydi' });
const gone = () => waitFor(() => expect(dialog()).toBeNull(), { timeout: 3000 });
const flag = (variant: string) => localStorage.getItem(`yondo.onboarding.v1.${variant}`);

beforeEach(anon);
afterEach(async () => {
  localStorage.clear();
  firstRun.forget('onboarding.customer');
  firstRun.forget('onboarding.companion');
  await setLang('uz');
});

describe('onboarding: first visit', () => {
  it('opens on the first visit with the first customer card, dots and working buttons', async () => {
    host('/');
    expect(dialog()).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Top', level: 3 })).toBeInTheDocument();
    expect(screen.getByText(/hamrohlarni qidiring/)).toBeInTheDocument();
    const dots = screen.getByRole('list', { name: 'Qöllanma qadamlari' });
    expect(dots.querySelectorAll('li')).toHaveLength(3);
    expect(dots.querySelector('[aria-current="step"]')).toHaveTextContent('1-qadam / 3');
    expect(screen.queryByRole('button', { name: 'Orqaga' })).toBeNull(); // nothing to go back to
    expect(flag('customer')).toBeNull(); // nothing is stored just by showing it
  });

  it('Next / Back move through the 3 cards; the last card says Tayyor and carries the honest safety note', async () => {
    host('/');
    await userEvent.click(screen.getByRole('button', { name: 'Keyingi' }));
    expect(screen.getByRole('heading', { name: 'Bron qil', level: 3 })).toBeInTheDocument();
    expect(screen.getByText(/qabul qilgandan keyin/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Orqaga' }));
    expect(screen.getByRole('heading', { name: 'Top', level: 3 })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Keyingi' }));
    await userEvent.click(screen.getByRole('button', { name: 'Keyingi' }));
    expect(screen.getByRole('heading', { name: 'Xavfsiz uçraşuv', level: 3 })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Tayyor' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Keyingi' })).toBeNull();
    const text = dialog()!.textContent ?? '';
    expect(text).toContain('Yondo xavfsizlikni kafolatlamaydi va favqulodda xizmat emas');
    expect(text).toContain('112');
    expect(text).toMatch(/SOS tugmasi moderator körib çiqişi uçun signal qayd etadi/); // an alert for review, nothing more
    expect(text).not.toMatch(/himoya|100\s?%|yordam keladi/i);
  });

  it('Skip closes it and remembers that on this device', async () => {
    host('/');
    await userEvent.click(screen.getByRole('button', { name: 'Ötkazib yuboriş' }));
    await gone();
    expect(flag('customer')).toBe('1');
  });

  it('Finish closes it and remembers that', async () => {
    host('/');
    await userEvent.click(screen.getByRole('button', { name: 'Keyingi' }));
    await userEvent.click(screen.getByRole('button', { name: 'Keyingi' }));
    await userEvent.click(screen.getByRole('button', { name: 'Tayyor' }));
    await gone();
    expect(flag('customer')).toBe('1');
  });

  it('is not shown again once seen (a later visit, same device)', () => {
    localStorage.setItem('yondo.onboarding.v1.customer', '1');
    host('/');
    expect(dialog()).toBeNull();
  });

  it('shows once per page load even when the device cannot remember (no loop)', async () => {
    const setItem = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('denied', 'SecurityError');
    });
    host('/');
    await userEvent.click(screen.getByRole('button', { name: 'Ötkazib yuboriş' }));
    await gone();
    setItem.mockRestore();
  });

  it.each(['/terms', '/privacy', '/login', '/c/abc', '/help', '/settings', '/bookings'])('never opens on %s', (path) => {
    host(path);
    expect(dialog()).toBeNull();
  });

  it('waits for the session check before choosing the wording', () => {
    auth.value = { state: { status: 'loading' }, user: null };
    host('/');
    expect(dialog()).toBeNull();
  });
});

describe('onboarding: keyboard and focus', () => {
  it('starts on the primary button, Enter advances, Tab stays inside, Escape skips', async () => {
    host('/');
    expect(screen.getByRole('button', { name: 'Keyingi' })).toHaveFocus();
    await userEvent.keyboard('{Enter}');
    expect(screen.getByRole('heading', { name: 'Bron qil', level: 3 })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Keyingi' })).toHaveFocus();
    await userEvent.tab(); // Next is the last control: wraps to the first one
    expect(screen.getByRole('button', { name: 'Ötkazib yuboriş' })).toHaveFocus();
    await userEvent.tab({ shift: true });
    expect(screen.getByRole('button', { name: 'Keyingi' })).toHaveFocus();
    await userEvent.keyboard('{Escape}');
    await gone();
    expect(flag('customer')).toBe('1');
  });

  it('going Back to the first card (the Back button vanishes) keeps focus inside the dialog', async () => {
    host('/');
    await userEvent.keyboard('{Enter}');
    await userEvent.tab({ shift: true });
    expect(screen.getByRole('button', { name: 'Orqaga' })).toHaveFocus();
    await userEvent.keyboard('{Enter}');
    expect(screen.getByRole('heading', { name: 'Top', level: 3 })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Keyingi' })).toHaveFocus();
  });

  it('is a modal dialog labelled by its title, and the card region is a polite live region', () => {
    host('/');
    const d = dialog()!;
    expect(d).toHaveAttribute('aria-modal', 'true');
    expect(d.querySelector('[aria-live="polite"]')).not.toBeNull();
  });
});

describe('onboarding: role-aware wording', () => {
  it('signed out = customer wording', () => {
    host('/');
    expect(screen.getByRole('heading', { name: 'Top', level: 3 })).toBeInTheDocument();
    expect(screen.queryByRole('group', { name: 'Qöllanma kim uçun' })).toBeNull();
  });

  it('a customer sees the customer cards', () => {
    signedIn('customer');
    host('/');
    expect(screen.getByRole('heading', { name: 'Top', level: 3 })).toBeInTheDocument();
  });

  it('a companion-only user sees companion wording (own flag), also on /studio', async () => {
    signedIn('companion');
    host('/');
    expect(screen.getByRole('heading', { name: 'Topil', level: 3 })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Keyingi' }));
    expect(screen.getByRole('heading', { name: 'Bronni qabul qil', level: 3 })).toBeInTheDocument();
    expect(screen.getByText(/mijoz tölov qiladi/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Ötkazib yuboriş' }));
    await gone();
    expect(flag('companion')).toBe('1');
    expect(flag('customer')).toBeNull();
  });

  it('both roles: customer cards first with a working switch to the companion cards; /studio opens the companion cards', async () => {
    signedIn('customer', 'companion');
    const { unmount } = host('/');
    expect(screen.getByRole('heading', { name: 'Top', level: 3 })).toBeInTheDocument();
    const asCompanion = screen.getByRole('button', { name: 'Hamroh sifatida' });
    expect(screen.getByRole('button', { name: 'Mijoz sifatida' })).toHaveAttribute('aria-pressed', 'true');
    await userEvent.click(asCompanion);
    expect(asCompanion).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('heading', { name: 'Topil', level: 3 })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Ötkazib yuboriş' }));
    await gone();
    expect(flag('customer')).toBe('1');
    expect(flag('companion')).toBe('1'); // the companion cards were shown too
    unmount();

    localStorage.clear();
    firstRun.forget('onboarding.customer');
    firstRun.forget('onboarding.companion');
    host('/studio');
    expect(screen.getByRole('heading', { name: 'Topil', level: 3 })).toBeInTheDocument();
  });

  it('is translated: Russian and English cards, same safety note', async () => {
    await setLang('ru');
    const { unmount } = host('/');
    expect(screen.getByRole('heading', { name: 'Найди', level: 3 })).toBeInTheDocument();
    unmount();
    await setLang('en');
    host('/');
    expect(screen.getByRole('heading', { name: 'Discover', level: 3 })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Next' }));
    await userEvent.click(screen.getByRole('button', { name: 'Next' }));
    expect(screen.getByText(/does not guarantee safety and is not an emergency service/)).toBeInTheDocument();
  });
});

describe('onboarding: reopen on demand', () => {
  it('GuideButton opens the guide anywhere, also after it was seen, and closing it works', async () => {
    localStorage.setItem('yondo.onboarding.v1.customer', '1');
    render(
      <MemoryRouter>
        <GuideButton />
      </MemoryRouter>,
    );
    expect(dialog()).toBeNull();
    await userEvent.click(screen.getByRole('button', { name: 'Qöllanmani körsatiş' }));
    expect(dialog()).toBeInTheDocument();
    await userEvent.keyboard('{Escape}');
    await gone();
    expect(screen.getByRole('button', { name: 'Qöllanmani körsatiş' })).toHaveFocus(); // back where the user was
  });

  it('works from Help', async () => {
    render(
      <MemoryRouter>
        <ToastProvider>
          <Help />
        </ToastProvider>
      </MemoryRouter>,
    );
    expect(screen.getByRole('heading', { name: 'Qöllanma', level: 2 })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Qöllanmani körsatiş' }));
    expect(screen.getByRole('heading', { name: 'Top', level: 3 })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Ötkazib yuboriş' }));
    await gone();
  });

  it('works from Settings', async () => {
    render(
      <MemoryRouter>
        <Settings />
      </MemoryRouter>,
    );
    expect(screen.getByRole('heading', { name: 'Qöllanma', level: 2 })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Qöllanmani körsatiş' }));
    await userEvent.click(screen.getByRole('button', { name: 'Keyingi' }));
    expect(screen.getByRole('heading', { name: 'Bron qil', level: 3 })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Ötkazib yuboriş' }));
    await gone();
  });
});
