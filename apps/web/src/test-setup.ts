import '@testing-library/jest-dom/vitest';
localStorage.setItem('yondo.uzAlphabet', '2026'); // unit tests assert the 2026 spelling of uz.ts
// jsdom has no IntersectionObserver; `Reveal` (motion whileInView) needs one. Never fires: content renders as-is.
if (!('IntersectionObserver' in globalThis)) {
  class NoopObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
    takeRecords() {
      return [];
    }
  }
  Object.assign(globalThis, { IntersectionObserver: NoopObserver });
}
