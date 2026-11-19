import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { HOLD_MS, HoldToConfirm } from './HoldToConfirm';

const setup = (onConfirm = vi.fn()) => {
  render(<HoldToConfirm label="Hisobni öçiriş" yesLabel="Ha, öçiriş" doneLabel="Bajarildi" onConfirm={onConfirm} />);
  return { onConfirm, btn: screen.getByRole('button', { name: /Hisobni öçiriş/ }) };
};
const live = () => document.querySelector('[aria-live="polite"]')!.textContent;

describe('HoldToConfirm (owner, 2026-11-18: 1.5 s hold replaces the dialog)', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('early release cancels: nothing runs, the label returns, the release is announced', () => {
    const { btn, onConfirm } = setup();
    fireEvent.pointerDown(btn);
    expect(btn).toHaveClass('holding');
    expect(btn).toHaveTextContent('Tasdiqlanmoqda…');
    act(() => vi.advanceTimersByTime(HOLD_MS - 100));
    fireEvent.pointerUp(btn);
    act(() => vi.advanceTimersByTime(1000));
    expect(onConfirm).not.toHaveBeenCalled();
    expect(btn).not.toHaveClass('holding');
    expect(btn).toHaveClass('retract');
    expect(live()).toBe('Bekor qilindi. Amal bajarilmadi.');
  });

  it('a full 1.5 s hold runs the action exactly once', async () => {
    const { btn, onConfirm } = setup();
    fireEvent.pointerDown(btn);
    await act(async () => vi.advanceTimersByTime(HOLD_MS));
    fireEvent.pointerUp(btn);
    fireEvent.click(btn);
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole('group')).toBeNull(); // the click after our own press does not open step two
  });

  it('keyboard: holding Space works, auto-repeat is ignored, early key-up cancels', async () => {
    const { btn, onConfirm } = setup();
    fireEvent.keyDown(btn, { key: ' ' });
    act(() => vi.advanceTimersByTime(500));
    fireEvent.keyUp(btn, { key: ' ' });
    expect(onConfirm).not.toHaveBeenCalled();
    act(() => vi.advanceTimersByTime(100));
    fireEvent.keyDown(btn, { key: 'Enter' });
    fireEvent.keyDown(btn, { key: 'Enter', repeat: true });
    await act(async () => vi.advanceTimersByTime(HOLD_MS));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it('activation without a hold (screen reader) opens an explicit two-step confirmation', async () => {
    const { btn, onConfirm } = setup();
    fireEvent.click(btn);
    expect(onConfirm).not.toHaveBeenCalled();
    const yes = screen.getByRole('button', { name: 'Ha, öçiriş' });
    expect(yes).toHaveFocus();
    expect(live()).toContain('tasdiqlaysizmi');
    fireEvent.click(screen.getByRole('button', { name: 'Yöq' }));
    expect(onConfirm).not.toHaveBeenCalled();
    expect(btn).toHaveFocus();
    fireEvent.click(btn);
    await act(async () => fireEvent.click(screen.getByRole('button', { name: 'Ha, öçiriş' })));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it('a failed action returns to idle and shows the error', async () => {
    const { btn } = setup(vi.fn().mockRejectedValue(new Error('x')));
    fireEvent.pointerDown(btn);
    await act(async () => vi.advanceTimersByTime(HOLD_MS));
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(btn).not.toHaveClass('done');
  });
});
