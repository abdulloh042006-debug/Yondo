import { act, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../api/client';
import { t } from '../i18n';

const get = vi.hoisted(() => vi.fn());
const put = vi.hoisted(() => vi.fn());
const upload = vi.hoisted(() => vi.fn());
vi.mock('../api/client', async (orig) => {
  const real = await orig<typeof import('../api/client')>();
  return { ...real, api: { ...real.api, get, put, upload } };
});
import { ToastProvider } from './feedback';
import { MyPhotos } from './MyPhotos';

const photo = (id: string, position: number) => ({ id, position, content_type: 'image/jpeg', width: 10, height: 10, size_bytes: 10, created_at: '2026-11-18T00:00:00Z' });
let list = [photo('p1', 0), photo('p2', 1)];
beforeEach(() => {
  list = [photo('p1', 0), photo('p2', 1)];
  get.mockReset();
  put.mockReset();
  upload.mockReset();
  get.mockImplementation((path: string) => Promise.resolve(path === '/user-photos/me' ? list : { url: 'data:image/png;base64,AA' }));
});
const mount = (isCompanion = false) => render(<MemoryRouter><ToastProvider><MyPhotos isCompanion={isCompanion} /></ToastProvider></MemoryRouter>);
const pick = (file: File) => act(async () => fireEvent.change(screen.getByTestId('photo-input'), { target: { files: [file] } }));

describe('Profil → Rasmlarim', () => {
  it('explains who sees a customer’s photos; the first photo is the main one', async () => {
    mount();
    expect(screen.getByText(t('photos.privacyCustomer'))).toBeInTheDocument();
    expect(await screen.findByAltText(t('photos.alt', { n: 1 }))).toBeInTheDocument();
    expect(screen.getByText(t('photos.main'))).toBeInTheDocument();
  });
  it('companions are told their public photos live in the studio', () => {
    mount(true);
    expect(screen.getByText(t('photos.privacyCompanion'), { exact: false })).toBeInTheDocument();
  });
  it('refuses a wrong type before sending; uploads a PNG', async () => {
    mount();
    await screen.findByAltText(t('photos.alt', { n: 2 }));
    await pick(new File(['x'], 'a.gif', { type: 'image/gif' }));
    expect(screen.getByRole('alert')).toHaveTextContent(t('photos.typeErr'));
    expect(upload).not.toHaveBeenCalled();
    upload.mockResolvedValue(photo('p3', 2));
    await pick(new File(['x'], 'a.png', { type: 'image/png' }));
    expect(upload).toHaveBeenCalledWith('/user-photos/me', expect.any(File));
  });
  it('shows the server error by code', async () => {
    mount();
    await screen.findByAltText(t('photos.alt', { n: 2 }));
    upload.mockRejectedValue(new ApiError(413, 'photo_too_large'));
    await pick(new File(['x'], 'a.png', { type: 'image/png' }));
    expect(await screen.findByText(t('err.photo_too_large'))).toBeInTheDocument();
  });
  it('"Asosiy qiliş" sends the new order; a failure restores the old one', async () => {
    mount();
    await screen.findByAltText(t('photos.alt', { n: 2 }));
    put.mockResolvedValue([photo('p2', 0), photo('p1', 1)]);
    await act(async () => fireEvent.click(screen.getByRole('button', { name: t('photos.makeMain') })));
    expect(put).toHaveBeenCalledWith('/user-photos/me/order', { photo_ids: ['p2', 'p1'] });
    put.mockRejectedValue(new ApiError(422, 'invalid_photo_order'));
    await act(async () => fireEvent.click(screen.getByRole('button', { name: t('photos.makeMain') })));
    expect(await screen.findByText(t('err.invalid_photo_order'))).toBeInTheDocument();
    expect(put).toHaveBeenLastCalledWith('/user-photos/me/order', { photo_ids: ['p1', 'p2'] });
  });
  it('no upload button action at 6 photos', async () => {
    list = [0, 1, 2, 3, 4, 5].map((i) => photo(`p${i}`, i));
    mount();
    await screen.findByAltText(t('photos.alt', { n: 6 }));
    expect(screen.getByRole('button', { name: t('photos.upload') })).toBeDisabled();
    expect(screen.getByText(t('photos.limitErr'))).toBeInTheDocument();
  });
});
