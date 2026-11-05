import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ApiError } from '../api/client';
import { ConfirmDialog, ErrorState } from './feedback';

describe('ConfirmDialog', () => {
  it('blocks the action until a long-enough reason is typed and surfaces server refusals', async () => {
    const onConfirm = vi.fn().mockRejectedValue(new ApiError(409, 'stale_companion_revision'));
    render(
      <ConfirmDialog open title="Rad etiş" body="matn" confirmLabel="Tasdiqlaş" reason={{ label: 'Sabab', min: 8, max: 100 }} onConfirm={onConfirm} onClose={() => {}} />,
    );
    const confirm = screen.getByRole('button', { name: 'Tasdiqlaş' });
    expect(confirm).toBeDisabled();
    await userEvent.type(screen.getByLabelText('Sabab'), 'qisqa');
    expect(confirm).toBeDisabled();
    await userEvent.type(screen.getByLabelText('Sabab'), ' va yetarli');
    expect(confirm).toBeEnabled();
    await userEvent.click(confirm);
    expect(onConfirm).toHaveBeenCalledWith('qisqa va yetarli');
    expect(await screen.findByRole('alert')).toHaveTextContent('özgargan');
  });

  it('moves focus into the dialog, closes on Escape', async () => {
    const onClose = vi.fn();
    render(<ConfirmDialog open title="T" body="b" confirmLabel="OK" onConfirm={async () => {}} onClose={onClose} />);
    await waitFor(() => expect(screen.getByRole('dialog')).toContainElement(document.activeElement as HTMLElement));
    await userEvent.keyboard('{Escape}');
    expect(onClose).toHaveBeenCalled();
  });
});

describe('ErrorState', () => {
  it('describes 503 as unavailability, not refusal, and offers retry', async () => {
    const retry = vi.fn();
    render(<ErrorState error={new ApiError(503, 'payment_provider_unavailable', 'req-9')} onRetry={retry} />);
    expect(screen.getByText('Xizmat hozirça mavjud emas')).toBeInTheDocument();
    expect(screen.getByText(/req-9/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Qayta uriniş' }));
    expect(retry).toHaveBeenCalled();
  });
});
