import { useState, type FormEvent } from 'react';
import { api, ApiError, type Schemas } from '../../api/client';
import { t, type Key } from '../../i18n';
import { formatInstant } from '../../lib/format';
import { serviceLabel } from '../../lib/labels';
import { useResource } from '../../lib/useResource';
import { ConfirmDialog, Empty, ErrorState, Loading, useToast } from '../../ui/feedback';
import { Select, TextArea } from '../../ui/form';
import { Reveal } from '../../ui/motion';
import { CAPTION_MAX, MAX_ACTIVE, type OwnStory } from './storyState';

type Photo = Schemas['PhotoResponse'];
type Service = Schemas['ServiceResponse'];
type Kind = OwnStory['kind'];

const STATE_KEY = { active: 'stories.state.active', expired: 'stories.state.expired', removed: 'stories.state.removed' } as const satisfies Record<OwnStory['state'], Key>;
const CAPTION_CODES = new Set(['story_caption_required', 'story_caption_contact_info']);

function OwnThumb({ id, selected, label, onPick }: { id: string; selected: boolean; label: string; onPick: () => void }) {
  const res = useResource((signal) => api.get<Schemas['PhotoDownload']>(`/companions/me/photos/${id}/download`, { signal }), [id]);
  return (
    <button type="button" className="st-thumb" role="radio" aria-checked={selected} aria-label={label} onClick={onPick}>
      {res.data ? <img src={res.data.url} alt="" loading="lazy" /> : <span aria-hidden="true">…</span>}
    </button>
  );
}

/** "My cards": the companion's own list plus the composer. Needs an active public profile. */
export function OwnStories() {
  const res = useResource((signal) => api.get<OwnStory[]>('/companions/me/stories', { signal }), []);
  const toast = useToast();
  const [removing, setRemoving] = useState<OwnStory | null>(null);
  const [inactive, setInactive] = useState(false);

  if (res.loading && !res.data) return <Loading rows={2} />;
  if (res.error && res.error.code !== 'story_profile_not_active') return <ErrorState error={res.error} onRetry={res.reload} />;
  const notActive = inactive || res.error?.code === 'story_profile_not_active';
  const list = res.data ?? [];
  const active = list.filter((s) => s.state === 'active').length;

  return (
    <Reveal>
      <div className="stack" style={{ gap: 18 }}>
        <div className="spread">
          <h2>{t('stories.mine')}</h2>
          {!notActive && <span className="tag" aria-live="polite">{t('stories.quota', { n: active, max: MAX_ACTIVE })}</span>}
        </div>
        <p className="hint">{t('stories.mineLead')}</p>

        {notActive ? (
          <Empty title={t('stories.notActive.title')}>{t('stories.notActive.body')}</Empty>
        ) : (
          <Composer full={active >= MAX_ACTIVE} onPosted={res.reload} onInactive={() => setInactive(true)} />
        )}

        {list.length === 0 ? (
          !notActive && <Empty title={t('stories.none')}>{t('stories.noneBody')}</Empty>
        ) : (
          <ul className="st-own" aria-label={t('stories.mine')}>
            {list.map((s) => (
              <li key={s.id}>
                <div className="st-ownrow">
                  <span className={`st-statechip ${s.state}`}>{t(STATE_KEY[s.state])}</span>
                  <span className="hint">{t(s.kind === 'note' ? 'stories.kind.note' : 'stories.kind.availability')}</span>
                  {s.service && <span className="tag">{serviceLabel(s.service.service_code)}</span>}
                </div>
                <p>{s.caption || '—'}</p>
                <p className="hint">
                  {s.state === 'active' ? t('stories.until', { time: formatInstant(s.expires_at) }) : formatInstant(s.created_at)}
                  {s.state === 'removed' && s.removal_note ? ` · ${t('stories.reason', { note: s.removal_note })}` : ''}
                </p>
                {s.state === 'active' && (
                  <div className="row">
                    <button type="button" className="btn ghost sm" onClick={() => setRemoving(s)}>{t('stories.delete')}</button>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}

        <ConfirmDialog
          open={!!removing}
          title={t('stories.deleteTitle')}
          body={t('stories.deleteBody')}
          confirmLabel={t('stories.delete')}
          danger
          onClose={() => setRemoving(null)}
          onConfirm={async () => {
            await api.del(`/companions/me/stories/${removing!.id}`);
            toast.push('ok', t('stories.deleted'));
            setRemoving(null);
            res.reload();
          }}
        />
      </div>
    </Reveal>
  );
}

function Composer({ full, onPosted, onInactive }: { full: boolean; onPosted: () => void; onInactive: () => void }) {
  const toast = useToast();
  const photos = useResource((signal) => api.get<Photo[]>('/companions/me/photos', { signal }), []);
  const services = useResource((signal) => api.get<Service[]>('/companions/me/services', { signal }), []);
  const [kind, setKind] = useState<Kind>('availability');
  const [caption, setCaption] = useState('');
  const [photoId, setPhotoId] = useState('');
  const [serviceId, setServiceId] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<ApiError>();

  const service = (services.data ?? []).find((s) => s.id === serviceId);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (full) return;
    setBusy(true);
    setErr(undefined);
    try {
      await api.post('/companions/me/stories', {
        kind,
        caption: caption.trim(),
        photo_id: photoId || null,
        service_id: kind === 'availability' && serviceId ? serviceId : null,
      });
      toast.push('ok', t('stories.posted'));
      setCaption('');
      setPhotoId('');
      setServiceId('');
      onPosted();
    } catch (error) {
      const apiError = error instanceof ApiError ? error : new ApiError(0, 'network_error');
      if (apiError.code === 'story_profile_not_active') onInactive();
      else setErr(apiError);
    } finally {
      setBusy(false);
    }
  };

  const captionError = err && CAPTION_CODES.has(err.code) ? err.message : undefined;
  const formError = err && !CAPTION_CODES.has(err.code) ? err.message : undefined;

  return (
    <form className="glass pad stack" onSubmit={(e) => void submit(e)} noValidate aria-label={t('stories.new')}>
      <h3>{t('stories.new')}</h3>
      <div role="group" aria-label={t('stories.kind')} className="row" style={{ gap: 6 }}>
        {(['availability', 'note'] as const).map((k) => (
          <button key={k} type="button" className="chip" aria-pressed={kind === k} onClick={() => setKind(k)}>
            {t(k === 'note' ? 'stories.kind.note' : 'stories.kind.availability')}
          </button>
        ))}
      </div>
      <TextArea
        label={t('stories.caption')}
        rows={2}
        maxLength={CAPTION_MAX}
        value={caption}
        onChange={(e) => setCaption(e.target.value)}
        error={captionError}
        hint={<>{t('stories.captionHint')} <span aria-live="polite">{caption.length}/{CAPTION_MAX}</span></>}
      />
      <div className="field" role="radiogroup" aria-label={t('stories.photo')}>
        <span>{t('stories.photo')}</span>
        <div className="row" style={{ gap: 8 }}>
          <button type="button" className="chip" role="radio" aria-checked={photoId === ''} onClick={() => setPhotoId('')}>{t('stories.noPhoto')}</button>
          {(photos.data ?? []).map((p, idx) => (
            <OwnThumb key={p.id} id={p.id} selected={photoId === p.id} label={t('stories.photoN', { n: idx + 1 })} onPick={() => setPhotoId(p.id)} />
          ))}
        </div>
      </div>
      {kind === 'availability' && (
        <>
          <Select label={t('stories.service')} value={serviceId} onChange={(e) => setServiceId(e.target.value)}>
            <option value="">{t('stories.noService')}</option>
            {(services.data ?? []).map((s) => <option key={s.id} value={s.id}>{serviceLabel(s.service_code)}</option>)}
          </Select>
          <p className="hint">{t('stories.windowsHint')}</p>
        </>
      )}
      <div className={`st-preview${kind === 'note' && !photoId ? ' nt' : ''}`} aria-label={t('stories.preview')} role="group">
        <span className="st-kind">{t(kind === 'note' ? 'stories.kind.note' : 'stories.kind.availability')}</span>
        {kind === 'availability' && service && <b>{serviceLabel(service.service_code)}</b>}
        <span>{caption.trim() || t('stories.previewEmpty')}</span>
        {photoId && <span className="hint st-prevhint">{t('stories.photoChosen')}</span>}
      </div>
      {full && <p className="err" role="alert">{t('stories.full')}</p>}
      {formError && <p className="err" role="alert">{formError}</p>}
      <div className="row">
        <button className="btn" disabled={busy || full}>{busy && <span className="spinner" aria-hidden="true" />}{t('stories.post')}</button>
      </div>
    </form>
  );
}
