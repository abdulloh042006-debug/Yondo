import { type KeyboardEvent, type ReactNode, useRef, useState } from 'react';
import { t } from '../i18n';
import { APP_ICONS, effectiveAppIcon, setAppIcon } from './appIcon';
import { BrandMark } from './Brand';
import { Icon, type IconName } from './Icon';
import { type AppIconId, type SkinId, SKINS, useSkin } from './skin';
import { setSkin } from './theme';

interface Tile<Id extends string> {
  id: Id;
  label: string;
  hint?: string;
  badge?: string;
  preview: ReactNode;
}

/** Radio group of tiles: roving tabindex, arrow keys move + select, Space/Enter select (native button). */
function RadioTiles<Id extends string>({ label, tiles, value, onSelect, className }: { label: string; tiles: Tile<Id>[]; value: Id; onSelect: (id: Id) => void; className: string }) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const onKey = (e: KeyboardEvent, index: number) => {
    const step = e.key === 'ArrowRight' || e.key === 'ArrowDown' ? 1 : e.key === 'ArrowLeft' || e.key === 'ArrowUp' ? -1 : 0;
    if (!step) return;
    e.preventDefault();
    const next = (index + step + tiles.length) % tiles.length;
    refs.current[next]?.focus();
    onSelect(tiles[next].id);
  };
  return (
    <div role="radiogroup" aria-label={label} className={`tile-grid ${className}`}>
      {tiles.map((tile, i) => {
        const on = tile.id === value;
        return (
          <button
            key={tile.id}
            ref={(el) => { refs.current[i] = el; }}
            type="button"
            role="radio"
            aria-checked={on}
            data-tile={tile.id}
            tabIndex={on ? 0 : -1}
            className="tile-opt"
            onClick={() => onSelect(tile.id)}
            onKeyDown={(e) => onKey(e, i)}
          >
            <span className="tile-preview" aria-hidden="true">{tile.preview}</span>
            <span className="stack" style={{ gap: 0, textAlign: 'left' }}>
              <b>{tile.label}</b>
              {tile.hint && <span className="hint">{tile.hint}</span>}
              {tile.badge && <span className="hint">{tile.badge}</span>}
            </span>
            {on && <span className="tile-check" aria-hidden="true"><Icon name="check" size={18} /></span>}
          </button>
        );
      })}
    </div>
  );
}

const PREVIEW_ICONS: IconName[] = ['home', 'heart', 'cal', 'user'];

/** Mini login: lockup, 4 icons and a button, drawn in the skin it represents. */
function SkinPreview({ skin }: { skin: SkinId }) {
  return (
    <span className={`skin-preview skin-preview-${skin}`}>
      <BrandMark skin={skin} />
      <span className="skin-preview-icons">
        {PREVIEW_ICONS.map((n) => <Icon key={n} name={n} size={18} set={skin} />)}
      </span>
      <span className="skin-preview-btn">{t('nav.login')}</span>
    </span>
  );
}

/** Settings: appearance style (skin). Day/night and the colour themes stay in ThemePicker. */
export function SkinPicker() {
  const skin = useSkin();
  const tiles: Tile<SkinId>[] = (['classic', 'warm'] as const).map((id) => ({
    id,
    label: t(`skin.${id}.label`),
    hint: t(`skin.${id}.hint`),
    preview: <SkinPreview skin={id} />,
  }));
  return <RadioTiles label={t('skin.title')} tiles={tiles} value={skin} onSelect={(id) => setSkin(id)} className="skin-tiles" />;
}

/** Settings: optional app icon. Follows the skin's default until the user picks one. */
export function AppIconPicker() {
  const skin = useSkin(); // the default icon follows the skin
  const [picked, setPicked] = useState(0);
  void picked;
  const value = effectiveAppIcon();
  const tiles: Tile<AppIconId>[] = APP_ICONS.map((def) => ({
    id: def.id,
    label: t(`appicon.${def.id}`),
    badge: def.id === SKINS[skin].appIconDefault ? t('appicon.default') : undefined,
    preview: <img src={def.svg} alt="" width="48" height="48" />,
  }));
  return (
    <RadioTiles
      label={t('appicon.title')}
      tiles={tiles}
      value={value}
      onSelect={(id) => {
        setAppIcon(id);
        setPicked((n) => n + 1);
      }}
      className="appicon-tiles"
    />
  );
}
