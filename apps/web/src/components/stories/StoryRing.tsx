import { useState } from 'react';
import { api } from '../../api/client';
import { t } from '../../i18n';
import { useResource } from '../../lib/useResource';
import { RoundPhoto } from './RoundPhoto';
import { StoryViewer } from './StoryViewer';
import { arcPaths, isSeen, type Ring } from './storyState';

const RING = 76;

/** One ring: an arc per active card; unseen = thick carrot arcs, seen = thin ink/paper arcs (state kept on this device only). */
export function StoryRingButton({ ring, seen, onOpen }: { ring: Ring; seen: boolean; onOpen: (el: HTMLButtonElement) => void }) {
  return (
    <li className="st-item">
      <button
        type="button"
        className="st-ring"
        aria-label={t('stories.open', { name: ring.display_name, count: ring.count })}
        onClick={(e) => onOpen(e.currentTarget)}
      >
        <span className="st-ringwrap" style={{ width: RING, height: RING }}>
          <svg className={`st-arcs${seen ? ' seen' : ' unseen'}`} width={RING} height={RING} viewBox={`0 0 ${RING} ${RING}`} aria-hidden="true" focusable="false">
            {arcPaths(RING, ring.count).map((d, i) => (
              <path key={i} d={d} pathLength={1} />
            ))}
          </svg>
          <RoundPhoto profileId={ring.profile_id} photo={ring.photo} size={64} />
          {ring.has_availability && <span className="st-dot" aria-hidden="true" />}
        </span>
        <span className="st-name">
          {ring.display_name}
          {ring.verified === true && (
            <span className="st-badge">
              <svg viewBox="0 0 12 12" width="10" height="10" aria-hidden="true" focusable="false"><path d="M2.5 6.4l2.4 2.3 4.6-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
              <span className="sr-only">{t('card.verified')}</span>
            </span>
          )}
        </span>
        {ring.has_availability && <span className="st-chip">{t('stories.hasFreeTime')}</span>}
      </button>
    </li>
  );
}

/** Home strip. Renders nothing while loading, on error, or when nobody has an active card. */
export function StoryStrip() {
  const res = useResource((signal) => api.get<Ring[]>('/discovery/stories', { query: { limit: 30 }, anonymous: true, signal }), []);
  const [open, setOpen] = useState<{ index: number; opener: HTMLElement } | null>(null);
  // bumps after a viewer closes so the "seen" read below is fresh
  const [, setTick] = useState(0);
  const rings = res.data ?? [];
  if (rings.length === 0) return null;
  return (
    <section className="st-strip" aria-label={t('stories.strip')}>
      <ul className="st-list">
        {rings.map((r, i) => (
          <StoryRingButton key={r.profile_id} ring={r} seen={isSeen(r.profile_id, r.latest_at)} onOpen={(el) => setOpen({ index: i, opener: el })} />
        ))}
      </ul>
      {open && rings[open.index] && (
        <StoryViewer
          ring={rings[open.index]}
          opener={open.opener}
          onClose={() => {
            setOpen(null);
            setTick((n) => n + 1);
          }}
        />
      )}
    </section>
  );
}
