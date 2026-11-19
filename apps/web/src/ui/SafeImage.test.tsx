import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { IMAGE_TIMEOUT_MS, SafeImage } from './SafeImage';

const logo = () => screen.queryByTestId('image-fallback');

describe('SafeImage (owner, 2026-11-19: the Yondo logo when a photo does not load)', () => {
  afterEach(() => vi.useRealTimers());

  it('shows the logo while loading, then the photo (alt kept)', () => {
    render(<SafeImage src="https://img.test/a.jpg" alt="DEMO Madina rasmi" />);
    expect(logo()).toBeInTheDocument();
    const img = screen.getByAltText('DEMO Madina rasmi');
    fireEvent.load(img);
    expect(logo()).toBeNull();
    expect(img.closest('.safe-img')).toHaveAttribute('data-status', 'loaded');
  });

  it('swaps to the logo for good when the photo fails (no broken image, no alt text spilling)', () => {
    render(<SafeImage src="https://img.test/404.jpg" alt="DEMO Jasur rasmi" />);
    fireEvent.error(screen.getByAltText('DEMO Jasur rasmi'));
    expect(logo()).toBeInTheDocument();
    expect(screen.queryByRole('img', { name: 'DEMO Jasur rasmi' })).toBeNull();
  });

  it('gives up after the timeout and when no URL could be obtained', () => {
    vi.useFakeTimers();
    const { rerender } = render(<SafeImage src="https://img.test/slow.jpg" alt="sekin" />);
    act(() => vi.advanceTimersByTime(IMAGE_TIMEOUT_MS + 1));
    expect(logo()).toBeInTheDocument();
    expect(screen.queryByAltText('sekin')).toBeNull();
    rerender(<SafeImage src={null} alt="yo'q" />);
    expect(logo()).toBeInTheDocument();
    expect(screen.queryByAltText("yo'q")).toBeNull();
  });
});
