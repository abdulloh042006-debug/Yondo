import { describe, expect, it } from 'vitest';
import { moveId, photoProblem, PHOTO_MAX_BYTES, toggledLike } from './photos';

describe('photo rules (mirror the API)', () => {
  it('accepts JPEG/PNG/WebP up to the size limit while under 6 photos', () => {
    for (const type of ['image/jpeg', 'image/png', 'image/webp']) expect(photoProblem({ type, size: 1000 }, 5)).toBeNull();
  });
  it('refuses a 7th photo, other types and files over 10 MB', () => {
    expect(photoProblem({ type: 'image/png', size: 10 }, 6)).toBe('photos.limitErr');
    expect(photoProblem({ type: 'image/gif', size: 10 }, 0)).toBe('photos.typeErr');
    expect(photoProblem({ type: '', size: 10 }, 0)).toBe('photos.typeErr');
    expect(photoProblem({ type: 'image/jpeg', size: PHOTO_MAX_BYTES + 1 }, 0)).toBe('photos.sizeErr');
  });
  it('moveId moves one id and keeps the others in order', () => {
    expect(moveId(['a', 'b', 'c'], 'c', 0)).toEqual(['c', 'a', 'b']);
    expect(moveId(['a', 'b', 'c'], 'a', 1)).toEqual(['b', 'a', 'c']);
    expect(moveId(['a', 'b'], 'x', 0)).toEqual(['a', 'b']);
    expect(moveId(['a', 'b'], 'a', 9)).toEqual(['b', 'a']);
  });
  it('toggledLike adds or removes exactly one like and never goes negative', () => {
    expect(toggledLike({ like_count: 2, liked_by_me: false })).toEqual({ like_count: 3, liked_by_me: true });
    expect(toggledLike({ like_count: 3, liked_by_me: true })).toEqual({ like_count: 2, liked_by_me: false });
    expect(toggledLike({ like_count: 0, liked_by_me: true })).toEqual({ like_count: 0, liked_by_me: false });
  });
});
