/**
 * First-run state: "has this device already seen the opening animation?"
 *
 * - Device-local (localStorage), works signed out, stores a completion flag only: no personal data, no account id.
 * - Every flow has a version. The key contains it (`yondo.<topic>.v<version>`), so bumping the version shows the flow
 *   again to everybody, and the old flag is simply never read again.
 * - Storage can be missing or throw (private mode, blocked site data, quota). Nothing here may throw and nothing may
 *   loop: a flow marked seen stays seen for the rest of the page's life even if it could not be persisted.
 */
export interface FlowDef {
  topic: string;
  version: number;
}

const SEEN = '1';

export function createFirstRun<N extends string>(defs: Record<N, FlowDef>, storage: () => Storage = () => window.localStorage) {
  /** Flows marked seen during this page's life, whatever the storage said. */
  const memory = new Set<string>();
  const keyOf = (name: N): string => `yondo.${defs[name].topic}.v${defs[name].version}`;
  return {
    keyOf,
    /** True when the flow has been shown before. Never throws; without storage only this page load is remembered. */
    isSeen(name: N): boolean {
      if (memory.has(keyOf(name))) return true;
      try {
        return storage().getItem(keyOf(name)) === SEEN;
      } catch {
        return false;
      }
    },
    /** Remember that the flow was shown. Returns whether it was persisted (it is remembered in memory either way). */
    markSeen(name: N): boolean {
      memory.add(keyOf(name));
      try {
        storage().setItem(keyOf(name), SEEN);
        return true;
      } catch {
        return false;
      }
    },
    /** Forget the flow (tests, and a possible "show the opening animation again" switch). */
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
  intro: { topic: 'intro', version: 1 },
} as const satisfies Record<string, FlowDef>;
export type FlowName = keyof typeof FLOWS;

export const firstRun = createFirstRun<FlowName>(FLOWS);
