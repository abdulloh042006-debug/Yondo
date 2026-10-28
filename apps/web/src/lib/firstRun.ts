/**
 * First-run state: "has this device already seen the intro / the onboarding?"
 *
 * - Device-local (localStorage), works signed out, stores a completion flag only: no personal data, no account id.
 * - Every flow has a version. The key contains it (`yondo.<topic>.v<version>[.<variant>]`), so bumping the version of
 *   a flow shows it again to everybody, and the old flag is simply never read again.
 * - Storage can be missing or throw (private mode, blocked site data, quota). Nothing here may throw, and nothing
 *   may loop: a flow marked seen stays seen for the rest of the page's life even if it could not be persisted, and a
 *   flow whose `whenUnavailable` is `'skip'` is simply not shown when the device cannot remember it.
 *
 * Adding a flow is one line in `FLOWS`; no other file needs to change. The opening animation (`intro`) uses `'show'`:
 * without storage it still plays at most once per page load (the in-memory flag), never on every navigation.
 */
export interface FlowDef {
  topic: string;
  version: number;
  variant?: string;
  /**
   * What to do when the device cannot remember the answer: `'show'` = show it (once per page load, thanks to the
   * in-memory fallback); `'skip'` = do not show it (animations must never repeat on every load).
   */
  whenUnavailable: 'show' | 'skip';
}

const SEEN = '1';

export function createFirstRun<N extends string>(defs: Record<N, FlowDef>, storage: () => Storage = () => window.localStorage) {
  /** Flows marked seen during this page's life, whatever the storage said. */
  const memory = new Set<string>();

  const keyOf = (name: N): string => {
    const def = defs[name];
    return `yondo.${def.topic}.v${def.version}${def.variant ? `.${def.variant}` : ''}`;
  };

  return {
    keyOf,
    /** True when the flow must not be shown (again). Never throws. */
    isSeen(name: N): boolean {
      if (memory.has(keyOf(name))) return true;
      try {
        return storage().getItem(keyOf(name)) === SEEN;
      } catch {
        return defs[name].whenUnavailable === 'skip';
      }
    },
    /** Remember that the flow was shown and dismissed. Returns whether it was persisted (it is remembered in memory either way). */
    markSeen(name: N): boolean {
      memory.add(keyOf(name));
      try {
        storage().setItem(keyOf(name), SEEN);
        return true;
      } catch {
        return false;
      }
    },
    /** Forget the flow (tests, and a possible "show the intro again" switch). */
    forget(name: N): void {
      memory.delete(keyOf(name));
      try {
        storage().removeItem(keyOf(name));
      } catch {
        /* nothing to forget */
      }
    },
  };
}

export const FLOWS = {
  intro: { topic: 'intro', version: 1, whenUnavailable: 'show' },
  'onboarding.customer': { topic: 'onboarding', variant: 'customer', version: 1, whenUnavailable: 'show' },
  'onboarding.companion': { topic: 'onboarding', variant: 'companion', version: 1, whenUnavailable: 'show' },
} as const satisfies Record<string, FlowDef>;
export type FlowName = keyof typeof FLOWS;

export const firstRun = createFirstRun<FlowName>(FLOWS);
