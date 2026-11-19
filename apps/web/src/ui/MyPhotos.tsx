import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, ApiError, type Schemas } from '../api/client';
import { t } from '../i18n';
import { moveId, photoProblem, PHOTO_LIMIT, PHOTO_TYPES } from '../lib/photos';
import { useResource } from '../lib/useResource';
import { ConfirmDialog, useToast } from './feedback';
import { SafeImage } from './SafeImage';

type Photo = Schemas['UserPhotoResponse'];

/**
 * Profil → "Rasmlarim": up to 6 photos of the signed-in user (`/user-photos/me`). The first one is the main photo.
 * A customer's photos are private (only companions the customer sent a booking request to, and moderators; the
 * server enforces it). A companion's public card photos are a separate set, managed in the studio.
 */
export function MyPhotos({ isCompanion }: { isCompanion: boolean }) {
  const res = useResource((signal) => api.get<Photo[]>('/user-photos/me', { signal }), []);
  const toast = useToast();
  const input = useRef<HTMLInputElement>(null);
  const still = useReducedMotion();
  const [uploading, setUploading] = useState(false);
  const [ordering, setOrdering] = useState(false);
  const [error, setError] = useState<string>();
  const [removing, setRemoving] = useState<Photo | null>(null);
  const photos = res.data ?? [];
  const full = photos.length >= PHOTO_LIMIT;

  const fail = (e: unknown) => setError(e instanceof ApiError ? e.message : t('common.actionFailed'));

  const upload = async (file: File | undefined) => {
    if (input.current) input.current.value = '';
    if (!file) return;
    setError(undefined);
    const problem = photoProblem(file, photos.length);
    if (problem) return setError(t(problem));
    setUploading(true);
    try {
      await api.upload<Photo>('/user-photos/me', file);
      toast.push('ok', t('photos.uploaded'));
      res.reload();
    } catch (e) {
      fail(e);
    } finally {
      setUploading(false);
    }
  };

  const reorder = async (ids: string[], okText: string) => {
    if (ordering) return;
    setError(undefined);
    setOrdering(true);
    const before = photos;
    // Optimistic: show the new order at once; the server's answer (or the old list on failure) replaces it.
    res.setData(ids.map((id) => before.find((p) => p.id === id)!).map((p, i) => ({ ...p, position: i })));
    try {
      res.setData(await api.put<Photo[]>('/user-photos/me/order', { photo_ids: ids }));
      toast.push('ok', okText);
    } catch (e) {
      res.setData(before);
      fail(e);
    } finally {
      setOrdering(false);
    }
  };
  const ids = photos.map((p) => p.id);

  return (
    <section className="glass pad stack" aria-labelledby="my-photos-h" aria-busy={res.loading || uploading || ordering}>
      <div className="spread">
        <h2 id="my-photos-h">
          {t('photos.title')} <span className="muted" style={{ fontSize: '0.9rem' }}>{t('photos.count', { n: photos.length })}</span>
        </h2>
        <button type="button" className="btn sm" disabled={uploading || full || res.loading} onClick={() => input.current?.click()}>
          {uploading && <span className="spinner" aria-hidden="true" />}
          {t('photos.upload')}
        </button>
        <input
          ref={input}
          type="file"
          accept={PHOTO_TYPES.join(',')}
          className="sr-only"
          tabIndex={-1}
          aria-label={t('photos.choose')}
          data-testid="photo-input"
          onChange={(e) => void upload(e.target.files?.[0])}
        />
      </div>
      <p className="hint" id="photos-privacy">
        {isCompanion ? (
          <>
            {t('photos.privacyCompanion')} <Link to="/studio">{t('account.studio')}</Link>
          </>
        ) : (
          t('photos.privacyCustomer')
        )}
      </p>
      <p className="hint">{full ? t('photos.limitErr') : t('photos.rules')}</p>
      {uploading && (
        <div className="stack tight" role="status">
          <progress className="bar" aria-label={t('photos.uploading')} />
          <span className="hint">{t('photos.uploading')}</span>
        </div>
      )}
      {error && (
        <p className="err" role="alert">
          {error}
        </p>
      )}
      {res.error ? (
        <p className="err" role="alert">
          {res.error.message} <button type="button" className="btn sm ghost" onClick={res.reload}>{t('common.retry')}</button>
        </p>
      ) : res.loading && !res.data ? (
        <div className="skeleton" style={{ minHeight: 160 }} />
      ) : photos.length === 0 ? (
        <div className="stack tight">
          <b>{t('photos.empty')}</b>
          <span className="hint">{t('photos.emptyBody')}</span>
        </div>
      ) : (
        <ol className="photo-grid" aria-describedby="photos-privacy">
          <AnimatePresence initial={false}>
            {photos.map((p, i) => (
              <motion.li
                key={p.id}
                layout={!still}
                initial={still ? false : { opacity: 0, scale: 0.94 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={still ? { opacity: 0 } : { opacity: 0, scale: 0.9 }}
                className="glass tight photo-tile"
              >
                <OwnUserPhoto id={p.id} alt={t('photos.alt', { n: i + 1 })} />
                {i === 0 && <span className="tag main-tag">{t('photos.main')}</span>}
                <div className="tools">
                  <button type="button" className="btn sm ghost" disabled={i === 0 || ordering} aria-label={t('photos.moveEarlier', { n: i + 1 })} onClick={() => void reorder(moveId(ids, p.id, i - 1), t('photos.orderSaved'))}>
                    ←
                  </button>
                  <button type="button" className="btn sm ghost" disabled={i === photos.length - 1 || ordering} aria-label={t('photos.moveLater', { n: i + 1 })} onClick={() => void reorder(moveId(ids, p.id, i + 1), t('photos.orderSaved'))}>
                    →
                  </button>
                  {i > 0 && (
                    <button type="button" className="btn sm ghost" disabled={ordering} onClick={() => void reorder(moveId(ids, p.id, 0), t('photos.mainSet'))}>
                      {t('photos.makeMain')}
                    </button>
                  )}
                  <button type="button" className="btn sm ghost" onClick={() => setRemoving(p)}>
                    {t('common.delete')}
                  </button>
                </div>
              </motion.li>
            ))}
          </AnimatePresence>
        </ol>
      )}
      <ConfirmDialog
        open={!!removing}
        danger
        title={t('photos.removeTitle')}
        body={t('photos.removeBody')}
        confirmLabel={t('common.delete')}
        onClose={() => setRemoving(null)}
        onConfirm={async () => {
          await api.del(`/user-photos/me/${removing!.id}`);
          toast.push('ok', t('photos.removed'));
          setRemoving(null);
          res.reload();
        }}
      />
    </section>
  );
}

/** The owner's own photo through a short-lived signed URL. */
function OwnUserPhoto({ id, alt }: { id: string; alt: string }) {
  const res = useResource((signal) => api.get<Schemas['PhotoDownload']>(`/user-photos/me/${id}/download`, { signal }), [id]);
  return (
    <div className="media">
      <SafeImage src={res.data?.url ?? (res.error ? null : undefined)} alt={alt} loading="lazy" />
    </div>
  );
}
