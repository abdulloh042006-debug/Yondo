import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { Pressable } from 'react-native';

import { api, errorText, type Schemas } from './api';
import { useAuth } from './auth';
import { ICONS, Icon } from './brand';
import { t } from './shared';
import { useTheme } from './theme';
import { TOUCH } from './ui';

type Card = Schemas['CompanionCard'];

/**
 * Favourites (customers only), the same endpoints as the web (GET /discovery/favorites, PUT/DELETE
 * /discovery/favorites/{profile_id}). Every change waits for the server; nothing is toggled optimistically.
 */
interface FavApi {
  canFavorite: boolean;
  ids: Set<string>;
  pending: Set<string>;
  notice?: string;
  toggle: (id: string) => Promise<void>;
  /** Bumped after every change, so the Sevimlilar list reloads. */
  version: number;
}
const Ctx = createContext<FavApi | null>(null);
const NO_IDS = new Set<string>();

export function FavoritesProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const canFavorite = !!user?.roles.includes('customer');
  const [ids, setIds] = useState<Set<string>>(new Set());
  const [pending, setPending] = useState<Set<string>>(new Set());
  const [notice, setNotice] = useState<string>();
  const [version, setVersion] = useState(0);
  useEffect(() => {
    setIds(new Set());
    if (!canFavorite) return;
    let live = true;
    api
      .get<Card[]>('/discovery/favorites')
      .then((list) => live && setIds(new Set(list.map((c) => c.id))))
      .catch(() => {});
    return () => {
      live = false;
    };
  }, [canFavorite, user?.id]);
  const toggle = useCallback(
    async (id: string) => {
      if (pending.has(id)) return;
      const had = ids.has(id);
      setPending((p) => new Set(p).add(id));
      try {
        if (had) await api.del(`/discovery/favorites/${id}`);
        else await api.put(`/discovery/favorites/${id}`);
        setIds((s) => {
          const n = new Set(s);
          if (had) n.delete(id);
          else n.add(id);
          return n;
        });
        setNotice(had ? t('card.favRemoved') : t('card.favAdded'));
        setVersion((v) => v + 1);
      } catch (e) {
        setNotice(errorText(e));
      } finally {
        setPending((p) => {
          const n = new Set(p);
          n.delete(id);
          return n;
        });
      }
    },
    [ids, pending],
  );
  useEffect(() => {
    if (!notice) return;
    const id = setTimeout(() => setNotice(undefined), 3000);
    return () => clearTimeout(id);
  }, [notice]);
  const value = useMemo<FavApi>(
    () => ({ canFavorite, ids: canFavorite ? ids : NO_IDS, pending, notice, toggle, version }),
    [canFavorite, ids, pending, notice, toggle, version],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useFavorites(): FavApi {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useFavorites must be used inside FavoritesProvider');
  return ctx;
}

/** The web's heart button: shown only to customers, pressed state from the server's list. */
export function HeartButton({ id, name }: { id: string; name: string }) {
  const fav = useFavorites();
  const { palette } = useTheme();
  if (!fav.canFavorite) return null;
  const on = fav.ids.has(id);
  return (
    <Pressable
      role="button"
      aria-pressed={on}
      aria-label={on ? t('card.favRemove', { name }) : t('card.favAdd', { name })}
      aria-disabled={fav.pending.has(id)}
      disabled={fav.pending.has(id)}
      onPress={() => void fav.toggle(id)}
      hitSlop={6}
      style={({ pressed }) => ({
        width: TOUCH,
        height: TOUCH,
        borderRadius: TOUCH / 2,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: palette.glass,
        borderWidth: 1,
        borderColor: on ? palette.accent : palette.glassLine,
        opacity: pressed ? 0.8 : 1,
      })}
    >
      <Icon d={ICONS.heart} color={palette.fg} fill={on ? palette.fg : 'none'} />
    </Pressable>
  );
}

