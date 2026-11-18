/**
 * Profile photo rules shared by the web and the mobile app (apps/mobile imports this file).
 * They mirror the API's checks (apps/api/src/yondo_api/userphotos/router.py) so a user hears about a wrong file
 * before it is sent; the server still decides, and its error `code` is what the UI shows on failure.
 */
export const PHOTO_LIMIT = 6;
/** The API's default `companion_photo_max_bytes` (10 MiB). A host can lower it; the server's 413 then explains. */
export const PHOTO_MAX_BYTES = 10 * 1024 * 1024;
export const PHOTO_TYPES = ['image/jpeg', 'image/png', 'image/webp'] as const;

export type PhotoProblem = 'photos.typeErr' | 'photos.sizeErr' | 'photos.limitErr';

/** First reason the file would be refused, or null. `type` may be empty when the platform does not know it. */
export function photoProblem(file: { type?: string | null; size?: number | null }, count: number): PhotoProblem | null {
  if (count >= PHOTO_LIMIT) return 'photos.limitErr';
  if (!file.type || !(PHOTO_TYPES as readonly string[]).includes(file.type)) return 'photos.typeErr';
  if (file.size != null && file.size > PHOTO_MAX_BYTES) return 'photos.sizeErr';
  return null;
}

/** New order with `id` moved to `to` (0 = main photo). Unknown id or same place: the list unchanged. */
export function moveId(ids: readonly string[], id: string, to: number): string[] {
  const from = ids.indexOf(id);
  if (from < 0) return [...ids];
  const next = ids.filter((x) => x !== id);
  next.splice(Math.max(0, Math.min(to, next.length)), 0, id);
  return next;
}

/** Optimistic like toggle: the state shown immediately, before the server answers. */
export function toggledLike(state: { like_count: number; liked_by_me: boolean }): { like_count: number; liked_by_me: boolean } {
  return state.liked_by_me
    ? { like_count: Math.max(0, state.like_count - 1), liked_by_me: false }
    : { like_count: state.like_count + 1, liked_by_me: true };
}
