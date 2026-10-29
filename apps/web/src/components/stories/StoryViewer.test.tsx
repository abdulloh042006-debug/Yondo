import { act, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const auth = vi.hoisted(() => ({ value: {} as unknown }));
const get = vi.hoisted(() => vi.fn());
vi.mock('../../auth/AuthContext', () => ({ useAuth: () => auth.value }));
vi.mock('../../api/client', async (orig) => {
  const real = await orig<typeof import('../../api/client')>();
  return { ...real, api: { ...real.api, get } };
});
import { ToastProvider } from '../../ui/feedback';
import { StoryViewer } from './StoryViewer';
import type { Ring } from './storyState';

const ring: Ring = { profile_id: 'p1', display_name: 'Test', verified: true, photo: null, count: 2, latest_at: '2026-10-29T10:00:00Z', has_availability: true };
const slides = [
  { id: 's1', kind: 'note', caption: 'Birinchi', created_at: '2026-10-29T10:00:00Z', expires_at: '2026-10-30T10:00:00Z', photo: null, service: null, windows: [] },
  { id: 's2', kind: 'note', caption: 'Ikkinchi', created_at: '2026-10-29T10:00:00Z', expires_at: '2026-10-30T10:00:00Z', photo: null, service: null, windows: [] },
];

function reduced(on: boolean) {
  window.matchMedia = ((q: string) => ({ matches: on && q.includes('reduce'), media: q, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {} })) as never;
}
async function open() {
  const onClose = vi.fn();
  render(
    <MemoryRouter>
      <ToastProvider>
        <StoryViewer ring={ring} onClose={onClose} />
      </ToastProvider>
    </MemoryRouter>,
  );
  await act(async () => {
    await vi.advanceTimersByTimeAsync(0);
  });
  return onClose;
}

beforeEach(() => {
  vi.useFakeTimers();
  auth.value = { user: null };
  get.mockResolvedValue(slides);
});
afterEach(() => {
  vi.useRealTimers();
  localStorage.clear();
  // @ts-expect-error jsdom has no matchMedia
  delete window.matchMedia;
  get.mockReset();
});

describe('StoryViewer', () => {
  it('auto-advances a note after 6 s and closes after the last card', async () => {
    reduced(false);
    const onClose = await open();
    expect(screen.getByText('Birinchi')).toBeInTheDocument();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(6100);
    });
    expect(screen.getByText('Ikkinchi')).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(6100);
    });
    expect(onClose).toHaveBeenCalled();
  });

  it('under prefers-reduced-motion there is no auto-advance and no Pause button; manual next works', async () => {
    reduced(true);
    const onClose = await open();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(60000);
    });
    expect(screen.getByText('Birinchi')).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
    expect(screen.queryByRole('button', { name: 'Töxtatiş' })).toBeNull();
    fireEvent.keyDown(document, { key: 'ArrowRight' });
    expect(screen.getByText('Ikkinchi')).toBeInTheDocument();
  });

  it('Esc closes, and viewing is stored on this device only', async () => {
    reduced(false);
    const onClose = await open();
    expect(screen.getByRole('img', { name: 'Karta 1 / 2' })).toBeInTheDocument();
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
    expect(JSON.parse(localStorage.getItem('yondo.storiesSeen') ?? '{}')).toEqual({ p1: ring.latest_at });
    expect(get).toHaveBeenCalledTimes(1);
  });
});
